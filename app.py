"""
Fileserver v1.0
Servidor de arquivos local e em rede LAN com interface web moderna e responsiva.
Execução por duplo clique no Windows ou via terminal em qualquer SO.
"""

import os
import sys
import traceback
from socketserver import TCPServer

from server.config import get_shared_paths, load_config
from server.handler import FileserverRequestHandler
from server.net import get_lan_ip


def main() -> None:
    # Carrega configurações e caminhos
    config = load_config()
    porta = int(config.get("port", 9876))
    shared_dir, uploads_dir = get_shared_paths()
    lan_ip = get_lan_ip()

    # Habilita reutilização rápida da porta para evitar 'Address already in use'
    TCPServer.allow_reuse_address = True

    # Inicia o servidor HTTP escutando em todas as interfaces ("0.0.0.0")
    with TCPServer(("", porta), FileserverRequestHandler) as httpd:
        print("=" * 60, flush=True)
        print("  📁 Fileserver v1.0 - Servidor de Arquivos", flush=True)
        print("=" * 60, flush=True)
        print(f"  Local:    http://127.0.0.1:{porta}", flush=True)
        print(f"  Rede:     http://{lan_ip}:{porta}   <-- Acesse no celular/outros PCs", flush=True)
        print(f"  Pasta:    {shared_dir}", flush=True)
        print(f"  Uploads:  {uploads_dir}", flush=True)
        print("=" * 60, flush=True)
        print("  Pressione Ctrl+C para encerrar o servidor.", flush=True)
        print("=" * 60, flush=True)
        print(flush=True)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[Fileserver] Encerrando o servidor com segurança. Até logo!")
        finally:
            httpd.server_close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Fileserver] Encerrado pelo usuário.")
        sys.exit(0)
    except Exception as e:
        print("\n" + "=" * 60)
        print("  [ERRO CRÍTICO AO INICIAR O FILESERVER]")
        print("=" * 60)
        traceback.print_exc()
        print("=" * 60)
        # Mantém a janela aberta no Windows quando executado por duplo clique
        try:
            input("\nPressione Enter para fechar esta janela...")
        except (EOFError, KeyboardInterrupt):
            pass
        sys.exit(1)
