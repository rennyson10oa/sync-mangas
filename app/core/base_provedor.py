import logging
import os
import re
import random
import time
import asyncio
import aiohttp
from sqlalchemy.future import select
from concurrent.futures import ProcessPoolExecutor
from typing import Optional, List, Tuple, Dict, Any

from app.db import async_session
from app.models import Manga, Capitulo, CapituloProvedor, Provedor
from app.core.config_manager import ConfigManager

# --- função de logging basico (cria um loggin por provider)---
async def get_provider_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"prov:{name}")
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
    
    log_dir = await ConfigManager.get("log_dir")
    if not log_dir:
        print("[!] log_dir não encontrado nas configs, usando ./logs")
        log_dir = "./logs" # default fallback if config is not set
        
    # guarrante that the log dir exists
    os.makedirs(log_dir, exist_ok=True)
    print(f"[*] Log dir: {log_dir}")
    
    fh = logging.FileHandler(f"{log_dir}/{name}.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    
    return logger

class BaseProvedor:
    nome: str = ""
    url: str = ""
    session: aiohttp.ClientSession | None = None
    logger: logging.Logger = None
    semaphore: asyncio.Semaphore
    _initialized: bool = False
    
    def __init__(self, concurrency: int = 5):
        if not getattr(self, "nome", None) or not getattr(self, "url", None):
            raise ValueError(f"{self.__class__.__name__} precisa definir nome e url")
        
        self._initialized = False
        self.logger = None
        self.session: aiohttp.ClientSession | None = None
        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(concurrency)

    async def init(self):
        if self._initialized:
            return
        self.logger = await get_provider_logger(self.nome)
        self._initialized = True
        
    async def ensure_init(self):
        if not self._initialized:
            await self.init()
        
    async def criar_sessao(self):
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(limit=20)  # limite de conexões abertas por provider
            self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
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
        # guarranted that the provider is initialized
        await self.ensure_init()
        """Busca mangas novos e capítulos novos, e atualiza o banco."""
        print(f"[*] Sincronizando mangás do provedor {self.nome}")
        self.logger.info(f"[*] Sincronizando mangás do provedor {self.nome}")
        
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
                    self.logger.info(f"[*] Mangá '{titulo}' já sincronizado.")
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
                        self.logger.info(f"[!] Capítulo {cap['numero']} já existente em '{titulo}', ignorado.")

                if novos > 0:
                    self.logger.info(f"[+] Mangá '{titulo}': {novos} capítulos adicionados.")
                    
            await session.commit()
            
        self.logger.info(f"[*] Sincronização de {self.nome} concluída!")
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