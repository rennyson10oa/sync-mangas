import asyncio
import html
from urllib.parse import quote
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
        raise NotImplementedError

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
    resultado = await mangabr.get_all_mangas()
    print(resultado)

if __name__ == "__main__":
    asyncio.run(test())