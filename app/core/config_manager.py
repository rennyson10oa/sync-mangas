from sqlalchemy import select
from app.models import Config
from app.db import async_session
import asyncio

class ConfigManager():
    _cache: dict[str, str] = {}
    _loaded: bool = False
    _loading_lock = asyncio.Lock() # avoid multiples loads at the same time
    
    @classmethod
    async def _ensure_loaded(cls):
        """guarantee that the cache is loaded"""
        if cls._loaded:
            return

        async with cls._loading_lock:
            # verify if it was loaded while we were waiting
            if cls._loaded:
                return

            async with async_session() as session:
                result = await session.execute(select(Config))
                configs = result.scalars().all()
                cls._cache = {c.chave: c.valor for c in configs}
                cls._loaded = True
                print(f"[*] Configurações carregadas: {len(cls._cache)}")
        
    @classmethod
    async def get(cls, key: str, default=None):
        if not cls._loaded:
            await cls._ensure_loaded()
        return cls._cache.get(key, default)
    
    @classmethod
    async def set(cls, session, key: str, value: str):
        config = await session.execute(select(Config).where(Config.chave == key))
        config = config.scalars().first()
        if config:
            config.valor = value
        else:
            config = Config(chave=key, valor=value)
            session.add(config)
        await session.commit()
        
        # atualiza no cache também
        cls._cache[key] = value
    
    @classmethod
    async def reload(cls):
        cls._loaded = False
        await cls._ensure_loaded()