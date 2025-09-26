from httpx import AsyncClient
import re

class BaseProvedor:
    nome = str
    url = str
    session: AsyncClient | None = None
        
    async def criar_sessao(self):
        """
        cria um sessão HTTP por padrão
        Pode ser sobrescrito por provedores que necessitam passar por cloudflare, login, etc.
        """
        self.session = AsyncClient(follow_redirects=True, timeout=30)
        return self.session
    
    async def buscar_mangas(self, query: str) -> list:
        """
        Recebe lista de busca e retorna uma lista de dicionarios:
        
        [{'titulo': 'Blue Lock', 'alter_title': 'ブルーロック', 'autor': '...', 'url': '...'}]
        
        Cada provedor vai ter seu proprio formato
        """
        raise NotImplementedError
    
    async def get_all_mangas(self) -> list:
        """
        Retorna uma lista de dicionarios com todos os mangas existentes:
        
        [{'titulo': 'Blue Lock', 'alter_title': 'ブルーロック', 'autor': '...', 'url': '...'}]
        """
        raise NotImplementedError
    
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
    
    async def parse_chapter(self, text: str) -> str:
        """
        Retorna (numero, titulo)
        """
        # tenta extrair número inteiro ou decimal após "capitulo" (case insensitive)
        m = re.search(r'[Cc]ap[ií]tulo\s+(\d+(?:\.\d+)?)', text)
        if m:
            numero = float(m.group(1)) if '.' in m.group(1) else int(m.group(1))
        else:
            numero = None  # não achou número
        
        titulo = text.strip()
        return numero, titulo