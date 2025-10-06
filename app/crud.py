import importlib
import pkgutil
import inspect
import asyncio
from typing import Optional, List, Tuple

from sqlalchemy import select, func
from app.db import async_session
from app.models import Provedor, Manga, Capitulo
from app.core.base_provedor import BaseProvedor
from app.core.config_manager import ConfigManager

async def registrar_provedores():
    import app.providers
    package = app.providers
    
    async with async_session() as session:
        async with session.begin():
            for _, modname, _ in pkgutil.iter_modules(package.__path__):
                modulo = f"app.providers.{modname}"
                mod = importlib.import_module(modulo)
                
                for attr in dir(mod):
                    obj = getattr(mod, attr)

                    # Apenas subclasses concretas de BaseProvedor
                    if isinstance(obj, type) and issubclass(obj, BaseProvedor) and obj is not BaseProvedor:
                        with session.no_autoflush:
                            # Verifica se já existe no banco
                            result = await session.execute(
                                select(Provedor).where(Provedor.modulo == modulo)
                            )
                            existing = result.scalar_one_or_none()
                            if existing:
                                continue

                            # Adiciona o provedor
                            provedor = Provedor(
                                nome=obj.nome,  # já é string correta
                                url=getattr(obj, "url", None),
                                modulo=modulo
                            )
                            session.add(provedor)
                        
async def buscar_mangas_no_banco(query: str):
    """
    Busca mangas pelo título ou título alternativo.
    Retorna lista de dicionários.
    """
    async with async_session() as session:
        result = await session.execute(
            select(Manga).where(
                (Manga.titulo.ilike(f"%{query}%")) |
                (Manga.alter_title.ilike(f"%{query}%"))
            )
        )
        mangas = result.scalars().all()
        # Converter para lista de dicts
        return [
            {
                "id": m.id,
                "titulo": m.titulo,
                "alter_title": m.alter_title,
                "autor": m.autor,
                "descricao": m.descricao
            } for m in mangas
        ]

async def sincronizar_provedores(provedores: Optional[List[str]] = None):
    """
    Importa provedores do package app.providers, filtra pelos nomes passados (se houver)
    e chama instance.sincronizar_mangas() para cada um.
    Suporta métodos async e sync (faz await se for coroutine).
    """
    # importa o pacote de provedores só aqui (evita execução no import do módulo)
    import app.providers as providers_package

    # pegar lista de provedores do banco
    async with async_session() as session:
        result = await session.execute(select(Provedor))
        db_provedores = result.scalars().all()

    # filtrar se o usuário passou uma lista de nomes
    if provedores:
        db_provedores = [p for p in db_provedores if p.nome in provedores]

    concurrency_limit = await int(ConfigManager.get("concurrency", 3))
    semaphore = asyncio.Semaphore(concurrency_limit)
    
    async def run_provedor(p: Provedor):
        async with semaphore:
            try:
                mod = importlib.import_module(p.modulo)
                
                cls = None
                for attr in dir(mod):
                    obj = getattr(mod, attr)
                    if isinstance(obj, type) and getattr(obj, "nome", None) == p.nome:
                        cls = obj
                        break
                    
                if cls in None:
                    print(f"[warn] classe do provedor {p.nome} não encontrada em {p.modulo}")
                    return
                
                instance = cls()
                
                sync_fn = getattr(instance, "sincronizar_mangas", None)
                if sync_fn is None:
                    print(f"[warn] provedor {p.nome} não implementa sincronizar_mangas()")
                    return
                
                print(f"[*] Iniciando provedor: {p.nome}")
                
                if inspect.iscoroutinefunction(sync_fn):
                    await sync_fn()
                else:
                    maybe = sync_fn()
                    if asyncio.iscoroutine(maybe):
                        await maybe
                        
                print(f"[✓] Finalizado provedor: {p.nome}")
                
            except Exception as e:
                print(f"[error] erro sincronizando {p.nome}: {e}")
    
    # cria tasks para todos os provedores        
    tasks = [asyncio.create_task(run_provedor(p)) for p in db_provedores]

    # aguarda todos terminarem
    await asyncio.gather(*tasks, return_exceptions=True)
    
    print("[✓] Sincronização concluída!")
    
async def obter_estatisticas() -> Tuple[int, int, int]:
    """
    Retorna (n_provedores, n_mangas, n_capitulos) como ints.
    Usa func.count() corretamente.
    """
    async with async_session() as session:
        provs = await session.scalar(select(func.count(Provedor.id)))
        mangas = await session.scalar(select(func.count(Manga.id)))
        caps = await session.scalar(select(func.count(Capitulo.id)))
        return int(provs or 0), int(mangas or 0), int(caps or 0)
    
async def set_config_in_db(Key: str, Value: str):
    async with async_session() as session:
        await ConfigManager.set(session, Key, Value)