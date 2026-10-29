"""
Runner Scanner - Desktop Application Entrypoint (Standalone Window)
Avvia il backend locale FastAPI in un thread di supporto e apre una finestra
desktop nativa tramite Edge WebView2, che si chiude e arresta tutto cliccando sulla 'X'.
"""

import os
import socket
import sys
import threading
import time
import httpx
import uvicorn
import webview

from app import app


def find_free_port(preferred: int = 8000) -> int:
    """Restituisce la porta preferita se libera, altrimenti trova una porta dinamica disponibile."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            pass

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_server(url: str, timeout: float = 8.0) -> bool:
    """Attende che il server FastAPI sia pronto a rispondere alle richieste."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            r = httpx.get(f"{url}/api/calendar/status", timeout=0.5)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.08)
    return False


def main():
    host = "127.0.0.1"
    port = find_free_port(8000)
    base_url = f"http://{host}:{port}"

    # Configurazione server Uvicorn
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False
    )
    server = uvicorn.Server(config)

    # Avvio del server in thread separato
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # Attende che il server sia attivo
    if not wait_for_server(base_url, timeout=8.0):
        print("Errore: impossibile avviare il server interno.")
        sys.exit(1)

    # Impostazioni finestra desktop
    webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = True

    # Crea la finestra desktop nativa
    window = webview.create_window(
        title="Runner Scanner",
        url=base_url,
        width=1280,
        height=880,
        min_size=(960, 640),
        confirm_close=False,
        text_select=True
    )

    try:
        # Avvia il loop grafico della finestra (bloccante finché non si chiude con la 'X')
        webview.start()
    finally:
        # Quando l'utente chiude la finestra con la 'X', arresta il server e termina
        server.should_exit = True
        time.sleep(0.2)
        sys.exit(0)


if __name__ == "__main__":
    main()
