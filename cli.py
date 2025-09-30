import os
import typer
import asyncio
from pathlib import Path
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

@app.command()
def listar():
    """Listar mangas no banco"""
    resultados = asyncio.run(buscar_mangas_no_banco(""))
    for r in resultados:
        print(f"[{r['id']}] {r['titulo']} ({r.get('autor')})")
        
@app.command()
def novo_provedor(nome: str):
    """
    Criar um novo provedor baseado no template.
    Exemplo: novo_provedor MangaLivre
    """
    # Caminhos
    base_dir = os.path.dirname(__file__)
    template_path = os.path.join(base_dir, "app/core", "provider_template.py")
    providers_dir = os.path.join(base_dir, "app/providers")
    os.makedirs(providers_dir, exist_ok=True)

    # Nome da classe e nome do arquivo
    class_name = nome
    file_name = nome.lower() + ".py"
    dest_file = os.path.join(providers_dir, file_name)

    if os.path.exists(dest_file):
        typer.echo(f"⚠️ Provedor {nome} já existe!")
        raise typer.Exit(1)

    # Pergunta a URL
    url = typer.prompt("Digite a URL base do provedor")

    # Lê template e substitui variáveis
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    content = content.replace("{class_name}", class_name).replace("{url}", url)

    # Cria novo arquivo
    with open(dest_file, "w", encoding="utf-8") as f:
        f.write(content)

    typer.echo(f"✅ Provedor {nome} criado em {dest_file}")
    typer.echo("⚠️ Registrando ele no banco...")
    registrar()
    typer.echo("✅ Registrado com sucesso!")
    
if __name__ == "__main__":
    app()