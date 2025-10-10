from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Input, Static, LoadingIndicator
from textual.reactive import reactive
import threading
import asyncio
import logging
from pathlib import Path
from app.crud import buscar_mangas_no_banco, sincronizar_provedores, obter_estatisticas
from app.services.metrics import start_metrics_server, active_workers, downloads_total, download_errors, downloads_in_progress

# disable the logs of SQLALCHEMY
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.ERROR)

async def worker_loop():
    while True:
        try:
            # simula worker
            active_workers.inc()
            # faz o download...
            downloads_total.inc()
        except Exception:
            download_errors.inc()
        finally:
            active_workers.dec()
        await asyncio.sleep(1)

class MangaApp(App):
    CSS_PATH = "styles.css"
    
    provedores = reactive([]) # dynamic list of provedores
    logs = reactive("")       # actual log of clicked provedor
    ativos = reactive(set())  # provedores in sync 
    provedor_atual = reactive(None)
    
    async def on_mount(self) -> None:
        await self.atualizar_stats()
        await self.carregar_provedores()
        self.set_interval(2, self._refresh_log) # check the log after 2 seconds
    
    async def _refresh_log(self):
        """Automatically refreshes the log."""
        if self.provedor_atual:
            caminho = Path(f"./logs/{self.provedor_atual}.log")
            if caminho.exists():
                try:
                    content = caminho.read_text(encoding="utf-8")
                    self.query_one("#log_view", Static).update(content[-2000:] or "(sem logs)")
                except Exception as e:
                    self.query_one("#log_view", Static).update(f"Erro lendo log: {e}")

    def compose(self) -> ComposeResult:
        # Campo de busca
        yield VerticalScroll(
            Horizontal(
                Input(placeholder="Pesquisar manga...", id="search_input"),
                Button("Buscar", id="search_button"),
            id="search_bar"),
            Horizontal(
                Button("Listar mangas", id="listar_button"),
                Button("Sincronizar provedores", id="sync_button"),
            ),
            id="toolbar",
        )
        
        yield Static("Provedores: 0 | Mangas: 0 | Capitulos: 0", id="stats")
        
        # Lista de provedores horizontal e rolável
        yield VerticalScroll(
            Horizontal(id="provider_list"),
            id="provider_scroll"
        )
        
        # Área de log
        yield Static("Selecione um provedor para ver os logs.", id="log_view")
        
    async def carregar_provedores(self):
        """Carrega provedores do banco."""
        from app.db import async_session
        from app.models import Provedor
        from sqlalchemy import select
        
        async with async_session() as session:
            result = await session.execute(select(Provedor.nome))
            self.provedores = [row[0] for row in result.all()]
        
        container = self.query_one("#provider_list")
        container.remove_children()
        for nome in self.provedores:
            container.mount(
                Button(nome, id=f"prov_{nome}", classes="prov_button"),
                LoadingIndicator(id=f"spin_{nome}", classes="spin_small hidden"),
            )
        
    async def on_button_pressed(self, event: Button.Pressed):
        btn_id = event.button.id

        if btn_id == "sync_button":
            await self.sincronizar()
        elif btn_id == "search_button":
            query = self.query_one("#search_input").value
            results = await buscar_mangas_no_banco(query)
            print(results)
        elif btn_id == "listar_button":
            await buscar_mangas_no_banco("")
        elif btn_id and btn_id.startswith("prov_"):
            nome = btn_id.replace("prov_", "")
            await self.mostrar_log(nome)
            
    async def sincronizar(self):
        """Sincroniza provedores e atualiza os botões visualmente."""
        from app.crud import sincronizar_provedores
        self.ativos = set(self.provedores)
        self.refresh_providers_state()

        async def run():
            await sincronizar_provedores()
            self.ativos = set()
            self.refresh_providers_state()
            await self.atualizar_stats()

        asyncio.create_task(run())

    def refresh_providers_state(self):
        """Atualiza visualmente os provedores em execução."""
        for nome in self.provedores:
            btn = self.query_one(f"#prov_{nome}", Button)
            spinner = self.query_one(f"#spin_{nome}", LoadingIndicator)
            if nome in self.ativos:
                btn.add_class("running")
                spinner.remove_class("hidden")  # mostra o spinner
            else:
                btn.remove_class("running")
                spinner.add_class("hidden")  # esconde o spinner
            
    async def mostrar_log(self, nome: str):
        """Exibe o conteúdo do log do provedor."""
        self.provedor_atual = nome  # <— salva qual está ativo
        caminho = Path(f"./logs/{nome}.log")
        if caminho.exists():
            try:
                content = caminho.read_text(encoding="utf-8")
                self.query_one("#log_view", Static).update(content[-2000:] or "(sem logs)")
            except Exception as e:
                self.query_one("#log_view", Static).update(f"Erro lendo log: {e}")
        else:
            self.query_one("#log_view", Static).update("Nenhum log encontrado.")

    async def atualizar_stats(self):
        stats_widget = self.query_one("#stats", Static)
        provs, mangas, caps = await obter_estatisticas()
        stats_widget.update(f"Provedores: {provs} | Mangas: {mangas} | Capitulos: {caps}")
        
if __name__ == "__main__":
    #roda o server do prometheus em outra thread
    threading.Thread(target=start_metrics_server, args=(9090,), daemon=True).start()
    
    # roda todo o resto normalmente
    threading.Thread(target=worker_loop, daemon=True).start()
    
    MangaApp().run()
