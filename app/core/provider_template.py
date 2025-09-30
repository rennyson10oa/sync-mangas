from app.core.base_provedor import BaseProvedor

class {class_name}(BaseProvedor):
    nome = "{class_name}"
    url = "{url}"
    
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