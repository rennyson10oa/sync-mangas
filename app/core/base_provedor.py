from sqlalchemy.future import select
from httpx import AsyncClient
import re

from app.db import async_session
from app.models import Manga, Capitulo, CapituloProvedor, Provedor

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

    async def baixar_mangas(self, manga_id: int):
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