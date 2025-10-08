from prometheus_client import Gauge, Counter, start_http_server

# Métricas principais
active_workers = Gauge("sync_active_workers", "Número de workers ativos")
downloads_in_progress = Gauge("sync_downloads_in_progress", "Downloads em andamento")
downloads_total = Counter("sync_downloads_total", "Total de downloads feitos")
download_errors = Counter("sync_download_errors", "Total de erros de download")

async def start_metrics_server(port=9090):
    """Inicia o servidor Prometheus local."""
    start_http_server(port)
