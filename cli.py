import typer
import asyncio
from app.crud import registrar_provedores, sincronizar_provedores, obter_estatisticas, buscar_mangas_no_banco
app = typer.Typer()

@app.command()
def registrar():
    """Registrar provedores disponíveis no banco"""
    asyncio.run(registrar_provedores())
    print("Provedores registrados com sucesso!")

@app.command()
def sync():
    """Sincronizar mangas de todos os provedores"""
    asyncio.run(sincronizar_provedores())
    print("Sincronização concluída!")

@app.command()
def stats():
    """Exibir estatísticas do banco"""
    provs, mangas, caps = asyncio.run(obter_estatisticas())
    print(f"Provedores: {provs}, Mangas: {mangas}, Capitulos: {caps}")

@app.command()
def buscar(query: str):
    """Buscar mangas no banco"""
    resultados = asyncio.run(buscar_mangas_no_banco(query))
    for r in resultados:
        print(f"[{r['id']}] {r['titulo']} ({r.get('autor')})")

    
if __name__ == "__main__":
    app()