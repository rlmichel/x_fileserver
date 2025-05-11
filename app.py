import os
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

# Configurações
PASTA_ARQUIVOS = "X:\\Shared"  # Pasta que será compartilhada
PORTA = 9876                      # Porta do servidor (pode mudar)

# Altera o diretório para a pasta de arquivos
os.chdir(PASTA_ARQUIVOS)

# Cria o servidor HTTP
with TCPServer(("", PORTA), SimpleHTTPRequestHandler) as httpd:
    print(f"Servidor de arquivos rodando em http://localhost:{PORTA}")
    print(f"Pasta compartilhada: {PASTA_ARQUIVOS}")
    print("Acesse de outro dispositivo usando seu IP local.")
    print("Pressione Ctrl+C para encerrar.")
    httpd.serve_forever()