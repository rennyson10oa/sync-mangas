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
        async with self.semaphore:
            async with self.session.get(url_pesquisa) as response:
                if response.status == 200:
                    # get the text of the response
                    text = await response.text()
                    
                    # descapes Unicode and HTML 
                    decoded_unicode = text.encode('utf-8').decode('unicode_escape')
                    final_html = html.unescape(decoded_unicode)
                    return final_html
                else:
                    self.logger.warning(f"Falha ao buscar '{query}' ({response.status})")
                    return None
    
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
            self.logger.info(f"[*] Buscando página {page}: {url_pesquisa}")

            try:
                async with self.semaphore:
                    response = await self.session.get(url_pesquisa)
            except Exception as e:
                self.logger.error(f"[!] Erro ao acessar {url_pesquisa}: {e}")
                break
            
            html_text = await response.text()
            html_text.strip()

            if response.status != 200 or not html_text:
                self.logger.info(f"[!] Página {page} não encontrada ou vazia. Encerrando.")
                break

            soup = BeautifulSoup(html_text, "html.parser")

            # Corrigido: seletor CSS precisa do ponto
            links = soup.select(".series .justify-content-center .link-series")

            if not links:
                self.logger.info(f"[!] Nenhum mangá encontrado na página {page}. Encerrando.")
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
        
        self.logger.info(f"[*] Buscando capítulos pela URL: {url}")
        
        try:
            async with self.semaphore:
                response = await self.session.get(url, headers={
                    "User-Agent": "Mozilla/5.0",
                    "X-Requested-With": "XMLHttpRequest"
                })
        except Exception as e:
            self.logger.error(f"[!] Erro ao acessar {url}: {e}")
            return chapters
        
        html_text = await response.text()
        html_text.strip()
        
        if response.status != 200 or not html_text:
            self.logger.error(f"[!] Resposta vazia ou erro {response.status} em {url}")
            return chapters
        
        soup = BeautifulSoup(html_text, "html.parser")
        links = soup.select(".col-chapter a")
        
        self.logger.info(f"[*] Links de capítulos encontrados: {len(links)}")
        
        for link in links:
            href = self.url.rstrip("/") + link.get("href")

            # pega só o <h5> dentro do <a>
            h5 = link.find("h5")
            if not h5:
                continue
            
            text_parts = [t.strip() for t in h5.find_all(string=True, recursive=False) if t.strip()]
            text = " ".join(text_parts)  # ex: "Capítulo 281"
            
            if not href or not text:
                continue
            
            numero, titulo = await self.parse_chapter(text)
            
            if numero is None:
                self.logger.error(f"[!] Capítulo sem número detectado: '{text}'")
                continue  # ou numero = 0 se quiser inserir mesmo assim

            chapters.append({
                "numero": numero,
                "titulo": titulo,  # usa só o título parseado
                "url": href if href.startswith("http") else urljoin(self.url, href)
            })

        # ordena capítulos por número
        chapters = sorted(chapters, key=lambda x: x["numero"] if x["numero"] else 0)

        self.logger.info(f"[*] Total de capítulos extraídos: {len(chapters)}")
        return chapters

    async def parse_chapter(self, text: str) -> tuple[int | float | None, str]:
        """
        Retorna (numero, titulo limpo)
        """
        # remove quebras de linha e espaços extras
        cleaned = " ".join(text.split())

        # tenta extrair número
        m = re.search(r'[Cc]ap[ií]tulo\s+(\d+(?:\.\d+)?)', cleaned)
        if m:
            numero_str = m.group(1)
            numero = float(numero_str) if '.' in numero_str else int(numero_str)
            titulo = f"Capítulo {numero_str}"
        else:
            numero = None
            titulo = cleaned  # se não achar número, devolve o texto limpo

        return numero, titulo
    
    async def sincronizar_mangas(self):
        return await super().sincronizar_mangas()

    async def baixar_mangas(self, manga_id):
        """
        Baixa os capítulos do manga informado.
        Deve ser sobrescrito por cada provedor.
        """
        raise NotImplementedError