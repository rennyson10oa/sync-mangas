import re, html, asyncio
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup

from app.core.base_provedor import BaseProvedor

class MangaBR(BaseProvedor):
    nome = "MangaBR"
    url = "https://mangabr.org/"
    
    async def buscar_mangas(self, query: str) -> list:
        if self.session is None:
            await self.criar_sessao()

        url_pesquisa = self.url + "search?q=" + quote(query)
        response = await self.session.get(url_pesquisa)

        if response.status_code == 200:
            # Pega o texto da resposta
            text = response.text

            # Desescapa Unicode e HTML
            decoded_unicode = text.encode('utf-8').decode('unicode_escape')
            final_html = html.unescape(decoded_unicode)
            return final_html

        return ""
    
    async def get_all_mangas(self) -> list:
        if self.session is None:
            await self.criar_sessao()

        mangas = []
        page = 1
        while True:
            # Corrigido: usar rstrip() para remover barra final
            if page == 1:
                url_pesquisa = self.url.rstrip("/") + "/manga"
            else:
                url_pesquisa = self.url.rstrip("/") + f"/manga?page={page}"

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
            links = soup.select(".series .justify-content-center .link-series")

            if not links:
                print(f"[✓] Nenhum mangá encontrado na página {page}. Encerrando.")
                break

            for link in links:
                mangas.append({
                    "titulo": link.get_text(strip=True),
                    "url": self.url.rstrip("/") + link.get("href")
                })

            page += 1

        return mangas
    
    async def get_manga_details(self, url: str) -> dict:
        raise NotImplementedError
    
    async def get_chapters(self, url: str) -> list:
        if self.session is None:
            await self.criar_sessao()
            
        chapters = []
        
        print(f"[*] Carregando capítulos pela URL: {url}")
        
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
        links = soup.select(".col-chapter a")
        
        print(f"[*] Links de capítulos encontrados: {len(links)}")
        
        for link in links:
            href = self.url + link.get("href")

            # pega só o <h5> dentro do <a>
            h5 = link.find("h5")
            if not h5:
                continue
            
            text = h5.get_text(strip=True)  # agora só o título/num do capítulo
            
            if not href or not text:
                continue
            
            numero, titulo = await self.parse_chapter(text)
            
            if numero is None:
                print(f"[!] Capítulo sem número detectado: '{titulo}' — pulando...")
                continue  # ou numero = 0 se quiser inserir mesmo assim

            chapters.append({
                "numero": numero,
                "titulo": titulo,  # usa só o título parseado
                "url": href if href.startswith("http") else urljoin(self.url, href)
            })

        # ordena capítulos por número
        chapters = sorted(chapters, key=lambda x: x["numero"] if x["numero"] else 0)

        print(f"[*] Total de capítulos extraídos: {len(chapters)}")
        return chapters


    async def sincronizar_mangas(self):
        """Busca mangas novos e capítulos novos, e atualiza o banco."""
        raise NotImplementedError

    async def baixar_mangas(self, manga_id):
        """
        Baixa os capítulos do manga informado.
        Deve ser sobrescrito por cada provedor.
        """
        raise NotImplementedError

async def test():
    mangabr = MangaBR()
    resultado = await mangabr.get_chapters('https://mangabr.org/manga/unordinary')
    print(resultado)

if __name__ == "__main__":
    asyncio.run(test())