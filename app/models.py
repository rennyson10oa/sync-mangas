from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Float, Boolean

Base = declarative_base()

class Provedor(Base):
    __tablename__ = "provedores"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, nullable=False)
    url = Column(String, unique=True, nullable=False)
    modulo = Column(String, unique=True, nullable=False)
    
    capitulos = relationship("CapituloProvedor", back_populates="provedor") 
    
class Manga(Base):
    __tablename__ = "mangas"
    
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, unique=True, nullable=False)
    alter_title = Column(String, nullable=True)
    autor = Column(String, nullable=True)
    descricao = Column(String, nullable=True)
    
    capitulos = relationship("Capitulo", back_populates="manga")
    
class Capitulo(Base):
    __tablename__ = "capitulos"
    
    id = Column(Integer, primary_key=True, index=True)
    numero = Column(Float, nullable=False)
    titulo = Column(String, nullable=True)
    baixado = Column(Boolean, nullable=False, default=False)
    
    manga_id = Column(Integer, ForeignKey("mangas.id"), nullable=False)
    
    manga = relationship("Manga", back_populates="capitulos")
    provedores = relationship("CapituloProvedor", back_populates="capitulo")
    
    __table_args__ = (
        UniqueConstraint("numero", "manga_id", name="uq_capitulo_manga"),
    )

    
class CapituloProvedor(Base):
    """
    Tabela de ligação que diz qual provedor o cap veio
    Ex: Capitulo 60 existe tanto no mangadex, quanto no MangaSee
    """
    __tablename__ = "capitulos_provedores"
    
    id = Column(Integer, primary_key=True)
    capitulo_id = Column(Integer, ForeignKey("capitulos.id"), nullable=False)
    provedor_id = Column(Integer, ForeignKey("provedores.id"), nullable=False)
    url = Column(String, nullable=False)
    
    capitulo = relationship("Capitulo", back_populates="provedores")
    provedor = relationship("Provedor", back_populates="capitulos")
    
    __table_args__ = (
        UniqueConstraint("capitulo_id", "provedor_id", name="uq_capitulo_por_provedor"),
    )
    
class Config(Base):
    __tablename__ = "config"
    
    id = Column(Integer, primary_key=True)
    chave = Column(String, unique=True)
    valor = Column(String)