"""
Fileserver v1.0
Servidor de arquivos local e em rede LAN com interface web moderna e responsiva.
Execução por duplo clique no Windows ou via terminal em qualquer SO.
"""

import os
import sys
import traceback
from socketserver import TCPServer

from server.config import get_base_files_dir, get_external_shared_dir, get_uploads_dir, load_config
from server.handler import FileserverRequestHandler
from server.net import get_lan_ip


def main() -> None:
    # Carrega configurações e caminhos universais
    config = load_config()
    porta = int(config.get("port", 9876))
    base_dir = get_base_files_dir()
    external_shared = get_external_shared_dir()
    uploads_dir = get_uploads_dir()
    lan_ip = get_lan_ip()

    # Habilita reutilização rápida da porta para evitar 'Address already in use'
    TCPServer.allow_reuse_address = True

    # Inicia o servidor HTTP escutando em todas as interfaces ("0.0.0.0")
    with TCPServer(("", porta), FileserverRequestHandler) as httpd:
        shared_status = f"{external_shared} (mapeado em /files/shared)" if external_shared else "(não detectado - modo universal ativo)"
        print("=" * 65, flush=True)
        print("  📁 Fileserver v1.0 - Servidor de Arquivos Universal", flush=True)
        print("=" * 65, flush=True)
        print(f"  Local:    http://127.0.0.1:{porta}", flush=True)
        print(f"  Rede:     http://{lan_ip}:{porta}   <-- Acesse no celular/outros PCs", flush=True)
        print(f"  Pasta:    {base_dir}", flush=True)
        print(f"  Shared:   {shared_status}", flush=True)
        print(f"  Uploads:  {uploads_dir}", flush=True)
        print("=" * 65, flush=True)
        print("  Pressione Ctrl+C para encerrar o servidor.", flush=True)
        print("=" * 65, flush=True)
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
