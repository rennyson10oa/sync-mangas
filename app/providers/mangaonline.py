import re
import asyncio
from sqlalchemy.future import select
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from app.db import async_session
from app.models import Manga, Capitulo, CapituloProvedor, Provedor
from app.core.base_provedor import BaseProvedor

class MangaOnline(BaseProvedor):
    nome = "MangaOnline"
    url = "https://mangaonline.blog/"

    async def buscar_mangas(self, termo=""):
        if self.session is None:
            await self.criar_sessao()

        url_pesquisa = self.url + "?s=" + urlparse.quote(termo)
        response = await self.session.get(url_pesquisa)

        if response.status_code == 200:
            return response.text
        return ""

    async def get_all_mangas(self):
        if self.session is None:
            await self.criar_sessao()

        mangas = []
        page = 1
        while True:
            # Corrigido: usar rstrip() para remover barra final
            if page == 1:
                url_pesquisa = self.url.rstrip("/") + "/manga/"
            else:
                url_pesquisa = self.url.rstrip("/") + f"/manga/page/{page}/"

            print(f"[*] Buscando página {page}: {url_pesquisa}")

            try:
                response = await self.session.get(url_pesquisa)
            except Exception as e:
                print(f"[!] Erro ao acessar {url_pesquisa}: {e}")
                break

            if response.status_code != 200 or not response.text.strip():
                print(f"[!] Página {page} não encontrada ou vazia. Encerrando.")
                break

            soup = BeautifulSoup(response.text, "html.parser")

            # Corrigido: seletor CSS precisa do ponto
            links = soup.select(".post-title a")

            if not links:
                print(f"[✓] Nenhum mangá encontrado na página {page}. Encerrando.")
                break

            for link in links:
                mangas.append({
                    "titulo": link.get_text(strip=True),
                    "url": link.get("href")
                })

            page += 1

        return mangas

    async def baixar_mangas(self, manga_id):
        raise NotImplementedError
    
    async def get_chapters(self, url: str) -> list:
        if self.session is None:
            await self.criar_sessao()

        chapters = []
        infos = []

        print(f"[*] Carregando capítulos pela url: {url}")

        try:
            response = await self.session.get(url, headers={
                "User-Agent": "Mozilla/5.0",
                "X-Requested-With": "XMLHttpRequest"
            })
        except Exception as e:
            print(f"[!] Erro ao acessar {url}: {e}")
            return chapters

        if response.status_code != 200 or not response.text.strip():
            print(f"[!] Resposta vazia ou erro {response.status_code} em {url}")
            return chapters

        soup = BeautifulSoup(response.text, "html.parser")
        
        # --- infos do manga ---
        post_infos = soup.select(".post-content_item")
        post_rating, post_alternative, post_type, post_status = "", "", "", ""
        
        for info in post_infos:
            heading = info.select_one(".summary-heading")
            if not heading:
                continue  # se não encontrar, pula

            tipo = heading.get_text(strip=True)

            match tipo:
                case "Rating":
                    post_rating = info.select_one(".summary-content.vote-details").get_text(strip=True)
                    match = re.search(r"([\d.]+)\s*/\s*5", post_rating)
                    if match:
                        post_rating = match.group(1)  # só o número (ex.: "4.3")
                    else:
                        post_rating = post_rating
                case "Alternative":
                    post_alternative = info.select_one(".summary-content").get_text(strip=True)
                case "Type":
                    post_type = info.select_one(".summary-content").get_text(strip=True)
                case "Status":
                    post_status = info.select_one(".summary-content").get_text(strip=True)
    
        infos.append({
            "avaliacao": post_rating,
            "alter_name": post_alternative,
            "tipo": post_type,
            "status": post_status,
        })
        
        # --- capítulos ---
        caps = soup.select(".main.version-chap.no-volumn li")

        print(f"[*] Links de capítulos encontrados: {len(caps)}")

        for cap in caps:
            
            infos_cap = cap.select_one("a")
            href = infos_cap.get("href")
            text = infos_cap.get_text(strip=True)
            
            if not href or not text:
                continue
            
            numero, titulo = await self.parse_chapter(text)
            
            if numero is None:
                print(f"[!] Capítulo sem número detectado: '{titulo}' — pulando...")
                continue  # ou numero = 0 se quiser inserir mesmo assim

            chapters.append({
                "numero": numero,
                "titulo": text,
                "url": href if href.startswith("http") else urljoin(self.url, href)
            })

        # ordena capítulos por número
        chapters = sorted(chapters, key=lambda x: x["numero"] if x["numero"] else 0)

        print(f"[*] Total de capítulos extraídos: {len(chapters)}")
        return {
            "infos": infos[0] if infos else {},
            "chapters": chapters
        }


    async def sincronizar_mangas(self):
        print(f"[*] Sincronizando mangás do provedor {self.nome}")
        
        # pega a lista de todos os mangas do server
        mangas = await self.get_all_mangas()
        
        async with async_session() as session:
            result = await session.execute(select(Provedor).where(Provedor.nome == self.nome))
            db_prov = result.scalars().first()
            self.db_provedor_id = db_prov.id

            for m in mangas:
                titulo = m["titulo"].strip()
                
                # checa se já existe no banco
                result = await session.execute(
                    select(Manga).where(Manga.titulo == titulo)
                )
                manga_db = result.scalars().first()
                
                if not manga_db:
                    # se não existir, cria um novo manga
                    manga_db = Manga(titulo=titulo)
                    session.add(manga_db)
                    await session.flush() # gera o id
                    
                # pega os caps existentes no banco
                result = await session.execute(
                    select(Capitulo).where(Capitulo.manga_id == manga_db.id)
                )
                
                caps_existentes = result.scalars().all()
                caps_existentes_dict = {float(c.numero): c for c in caps_existentes}
                
                # pega capitulos novos do provedor
                capitulos = await self.get_chapters(m["url"])
                
                if len(capitulos) == len(caps_existentes):
                    print(f"[-] Mangá '{titulo}' já sincronizado.")
                    continue
                
                #adiciona caps que não existem
                novos = 0
                for cap in capitulos:
                    if cap["numero"] not in caps_existentes_dict:
                        novo_cap = Capitulo(
                            manga_id=manga_db.id,
                            numero=cap["numero"],
                            titulo=cap.get("titulo"),
                        )
                        session.add(novo_cap)
                        await session.flush()  # garante que novo_cap.id é gerado

                        # 👉 Atualiza o dict para evitar inserir duplicados
                        caps_existentes_dict[cap["numero"]] = novo_cap

                        cap_prov = CapituloProvedor(
                            capitulo_id=novo_cap.id,
                            provedor_id=self.db_provedor_id,
                            url=cap["url"]
                        )
                        session.add(cap_prov)
                        novos += 1
                    else:
                        print(f"[!] Capítulo {cap['numero']} já existente em '{titulo}', ignorado.")

                        
                if novos > 0:
                    print(f"[+] Mangá '{titulo}': {novos} capítulos adicionados.")
                    
            await session.commit()
            
        print(f"[✓] Sincronização de {self.nome} concluída!")

    async def baixar_mangas(self, manga_id):
        """
        Baixa os capítulos do manga informado.
        Deve ser sobrescrito por cada provedor.
        """
        raise NotImplementedError
    
async def main():
    teste = await MangaOnline().get_chapters('https://mangaonline.blog/manga/demon-slayer-kimetsu-no-yaiba-manga-pt-br/')
    print(teste)
    
if __name__ == "__main__":
    asyncio.run(main())