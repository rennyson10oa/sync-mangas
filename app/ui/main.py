from textual.app import App, ComposeResult
from textual.widgets import Button, Input, Static, Checkbox
from app.crud import buscar_mangas_no_banco, sincronizar_provedores, obter_estatisticas

class MangaApp(App):
    CSS_PATH = "styles.css"
    
    def compose(self) -> ComposeResult:
        yield Static("Provedores: 0 | Mangas: 0 | Capitulos: 0", id="stats")
        
        #campo de busca
        yield Input(placeholder="Pesquisar manga...", id="search_input")
        yield Button("Buscar", id="search_button")
        
        yield Button("Listar mangas", id="listar_button")
        
        # Botão de sincronização
        yield Button("Sincronizar provedores", id="sync_button")

        # Lista de provedores (checkbox)
        # Você pode popular dinamicamente via self.provedores
        yield Checkbox("MangaOnline", id="provider_mangaonline")
        
    async def on_mount(self) -> None:
        """Chamado automaticamente quando a UI está pronta."""
        await self.atualizar_stats()
        
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "sync_button":
            await sincronizar_provedores()
            await self.atualizar_stats()
        elif event.button.id == "search_button":
            query = self.query_one("#search_input").value
            results = await buscar_mangas_no_banco(query)
            print(results)
        elif event.button.id == "listar_button":
            results = await buscar_mangas_no_banco("")
            
            
    async def atualizar_stats(self):
        stats_widget = self.query_one("#stats", Static)
        provs, mangas, caps = await obter_estatisticas()
        stats_widget.update(f"Provedores: {provs} | Mangas: {mangas} | Capitulos: {caps}")
        
if __name__ == "__main__":
    MangaApp().run()
