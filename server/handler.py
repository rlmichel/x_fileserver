"""Módulo de handler HTTP customizado para o Fileserver v1.0."""

from datetime import datetime
import io
import json
import mimetypes
import os
import platform
import re
import shutil
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse
import zipfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler

from server.config import get_base_files_dir, get_external_shared_dir, get_uploads_dir, load_config, save_config
from server.files import format_size, list_directory, resolve_safe_path, sanitize_filename
from server.net import get_lan_ip

STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))


class MultipartParser:
    """
    Parser de multipart/form-data em streaming utilizando apenas a stdlib do Python.
    Evita o uso do módulo cgi (removido no Python 3.13) e consome a entrada em blocos
    para suportar arquivos de qualquer tamanho sem sobrecarregar a memória RAM.
    """

    def __init__(self, rfile, content_length: int, boundary: bytes, uploads_dir: str):
        self.rfile = rfile
        self.remaining = content_length
        self.boundary = boundary
        self.delimiter = b"--" + boundary
        self.end_delimiter = b"--" + boundary + b"--"
        self.uploads_dir = uploads_dir
        self.buffer = bytearray()
        self.chunk_size = 64 * 1024  # 64 KB por leitura

    def _read_chunk(self) -> bytes:
        if self.remaining <= 0:
            return b""
        to_read = min(self.chunk_size, self.remaining)
        data = self.rfile.read(to_read)
        self.remaining -= len(data)
        return data

    def parse(self) -> List[Dict[str, Any]]:
        saved_files: List[Dict[str, Any]] = []

        # Lê até encontrar o primeiro delimitador de boundary
        while self.delimiter not in self.buffer and self.remaining > 0:
            chunk = self._read_chunk()
            if not chunk:
                break
            self.buffer.extend(chunk)

        idx = self.buffer.find(self.delimiter)
        if idx == -1:
            return saved_files

        # Descarta qualquer preâmbulo antes do primeiro boundary
        del self.buffer[: idx + len(self.delimiter)]

        while True:
            # Verifica se atingimos o delimitador final (--boundary--)
            if self.buffer.startswith(b"--"):
                break

            # Se começar com \r\n, consome
            if self.buffer.startswith(b"\r\n"):
                del self.buffer[:2]
            elif self.buffer.startswith(b"\n"):
                del self.buffer[:1]

            # Lê os cabeçalhos da parte até a linha em branco (\r\n\r\n ou \n\n)
            header_end = -1
            while header_end == -1:
                header_end = self.buffer.find(b"\r\n\r\n")
                if header_end != -1:
                    header_bytes = self.buffer[:header_end]
                    del self.buffer[: header_end + 4]
                    break
                header_end_single = self.buffer.find(b"\n\n")
                if header_end_single != -1:
                    header_bytes = self.buffer[:header_end_single]
                    del self.buffer[: header_end_single + 2]
                    break

                chunk = self._read_chunk()
                if not chunk:
                    break
                self.buffer.extend(chunk)

            if header_end == -1:
                break

            header_text = header_bytes.decode("utf-8", errors="replace")
            filename = None
            for line in header_text.splitlines():
                if line.lower().startswith("content-disposition:"):
                    # Extrai filename="..." ou filename*=...
                    m = re.search(r'filename="([^"]+)"', line, re.IGNORECASE)
                    if m:
                        filename = m.group(1)
                    else:
                        m2 = re.search(r'filename=([^\s;]+)', line, re.IGNORECASE)
                        if m2:
                            filename = m2.group(1).strip("\"'")

            target_file = None
            safe_name = None
            dest_path = None
            bytes_written = 0

            if filename:
                safe_name = sanitize_filename(filename)
                # Garante nome único se já existir
                base_name, ext = os.path.splitext(safe_name)
                candidate_name = safe_name
                counter = 1
                while os.path.exists(os.path.join(self.uploads_dir, candidate_name)):
                    candidate_name = f"{base_name}_{counter}{ext}"
                    counter += 1
                safe_name = candidate_name
                dest_path = os.path.join(self.uploads_dir, safe_name)
                target_file = open(dest_path, "wb")

            # Agora consome o conteúdo até o próximo boundary (\r\n--boundary)
            search_boundary = b"\r\n" + self.delimiter
            alt_search_boundary = b"\n" + self.delimiter

            while True:
                pos = self.buffer.find(search_boundary)
                boundary_len = len(search_boundary)
                if pos == -1:
                    pos = self.buffer.find(alt_search_boundary)
                    boundary_len = len(alt_search_boundary)

                if pos != -1:
                    # Encontrou o boundary!
                    content_chunk = self.buffer[:pos]
                    if target_file:
                        target_file.write(content_chunk)
                        bytes_written += len(content_chunk)
                    del self.buffer[: pos + boundary_len]
                    break
                else:
                    # Guarda uma janela de segurança do tamanho do boundary no final do buffer
                    safe_len = max(0, len(self.buffer) - (len(search_boundary) + 4))
                    if safe_len > 0:
                        flush_chunk = self.buffer[:safe_len]
                        if target_file:
                            target_file.write(flush_chunk)
                            bytes_written += len(flush_chunk)
                        del self.buffer[:safe_len]

                    chunk = self._read_chunk()
                    if not chunk:
                        # Fim inesperado do stream
                        if target_file and len(self.buffer) > 0:
                            target_file.write(self.buffer)
                            bytes_written += len(self.buffer)
                        self.buffer.clear()
                        break
                    self.buffer.extend(chunk)

            if target_file:
                target_file.close()
                if bytes_written > 0 or filename:
                    saved_files.append({
                        "name": safe_name,
                        "size": bytes_written,
                        "size_formatted": format_size(bytes_written),
                        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

        return saved_files


class FileserverRequestHandler(BaseHTTPRequestHandler):
    """Handler HTTP para servir a UI moderna, arquivos da pasta compartilhada e API REST."""

    server_version = "Fileserver/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        """Personaliza os logs do terminal com timestamp claro."""
        now_str = datetime.now().strftime("%H:%M:%S")
        print(f"[{now_str}] {self.address_string()} - {format % args}")

    def send_json_response(self, data: Any, status: int = HTTPStatus.OK) -> None:
        """Helper para enviar respostas JSON estruturadas."""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message: str, status: int = HTTPStatus.BAD_REQUEST) -> None:
        """Helper para enviar respostas de erro padronizadas."""
        self.send_json_response({"error": message}, status=status)

    def do_OPTIONS(self) -> None:
        """Suporte a pre-flight CORS para clientes REST/mobile."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Range")
        self.end_headers()

    def do_GET(self) -> None:
        """Roteamento de requisições GET."""
        parsed_url = urlparse(self.path)
        path = unquote(parsed_url.path)
        query = parse_qs(parsed_url.query)

        # 1. Rota raiz: serve o index.html da UI
        if path in ("/", "/index.html"):
            self.serve_file(os.path.join(STATIC_DIR, "index.html"), "text/html; charset=utf-8")
            return

        # 2. Arquivos estáticos (CSS, JS, assets)
        if path.startswith("/static/"):
            rel_file = path[len("/static/") :].lstrip("/")
            file_path = os.path.abspath(os.path.join(STATIC_DIR, rel_file))
            if not file_path.startswith(STATIC_DIR) or not os.path.isfile(file_path):
                self.send_error(HTTPStatus.NOT_FOUND, "Arquivo estático não encontrado")
                return
            mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
            if mime.startswith("text/"):
                mime += "; charset=utf-8"
            self.serve_file(file_path, mime)
            return

        # 3. API Info: metadados do servidor e rede
        if path == "/api/info":
            self.handle_api_info()
            return

        # 4. API List: listagem de arquivos da pasta compartilhada
        if path == "/api/list":
            req_path = query.get("path", [""])[0]
            self.handle_api_list(req_path)
            return

        # 5. Download e preview de arquivos: /files/<caminho>
        if path.startswith("/files/"):
            rel_file = path[len("/files/") :].lstrip("/")
            is_inline = query.get("inline", ["0"])[0] == "1"
            self.handle_file_download(rel_file, inline=is_inline)
            return

        # 6. Download de múltiplos arquivos em ZIP via GET
        if path == "/api/download-zip":
            files_param = query.get("files", [])
            if files_param:
                file_list = [f.strip() for f in files_param[0].split(",") if f.strip()]
                self._send_zip_of_files(file_list)
                return
            self.send_error_json("Parâmetro 'files' ausente", status=HTTPStatus.BAD_REQUEST)
            return

        # Rota desconhecida
        self.send_error_json("Recurso não encontrado", status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        """Roteamento de requisições POST."""
        parsed_url = urlparse(self.path)
        path = unquote(parsed_url.path)

        if path == "/upload":
            self.handle_upload()
            return

        if path == "/api/download-batch":
            self.handle_download_batch()
            return

        if path == "/api/config":
            self.handle_api_config()
            return

        self.send_error_json("Endpoint não encontrado", status=HTTPStatus.NOT_FOUND)

    def serve_file(self, file_path: str, content_type: str) -> None:
        """Serve um arquivo local de forma eficiente."""
        try:
            file_size = os.path.getsize(file_path)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            with open(file_path, "rb") as f:
                shutil.copyfileobj(f, self.wfile)
        except Exception as e:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Erro ao servir arquivo: {e}")

    def handle_api_info(self) -> None:
        """Retorna informações de rede, diretórios e configurações do servidor."""
        cfg = load_config()
        base_dir = get_base_files_dir()
        external_dir = get_external_shared_dir()
        uploads_dir = get_uploads_dir()
        lan_ip = get_lan_ip()
        port = cfg.get("port", 9876)

        data = {
            "name": "Fileserver",
            "version": cfg.get("version", "1.0.0"),
            "host": "0.0.0.0",
            "lan_ip": lan_ip,
            "port": port,
            "local_url": f"http://127.0.0.1:{port}",
            "lan_url": f"http://{lan_ip}:{port}",
            "os": f"{platform.system()} {platform.release()}",
            "base_dir": base_dir,
            "shared_dir": base_dir,
            "external_shared_dir": external_dir,
            "has_external_shared": bool(external_dir is not None),
            "uploads_dir": uploads_dir,
            "ftp_enabled": bool(cfg.get("ftp_enabled", False)),
            "filezilla_manager_enabled": bool(cfg.get("filezilla_manager_enabled", False)),
            "theme": cfg.get("theme", "dark"),
        }
        self.send_json_response(data)

    def handle_api_list(self, rel_path: str) -> None:
        """Lista arquivos e subpastas de forma segura a partir do diretório inicial ou shared."""
        data, err = list_directory(rel_path)
        if err:
            self.send_error_json(err, status=HTTPStatus.BAD_REQUEST)
            return
        self.send_json_response(data)

    def handle_file_download(self, rel_file: str, inline: bool = False) -> None:
        """Realiza o download seguro ou preview de um arquivo compartilhado."""
        target_path = resolve_safe_path(rel_file)

        if not target_path or not os.path.exists(target_path):
            self.send_error_json("Arquivo não encontrado", status=HTTPStatus.NOT_FOUND)
            return

        if os.path.isdir(target_path):
            self.send_error_json("O caminho especificado é uma pasta, não um arquivo", status=HTTPStatus.BAD_REQUEST)
            return

        try:
            file_size = os.path.getsize(target_path)
            mime_type = mimetypes.guess_type(target_path)[0] or "application/octet-stream"
            filename = os.path.basename(target_path)

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(file_size))

            disp_type = "inline" if inline else "attachment"
            # Codificação segura para caracteres especiais no nome do arquivo
            encoded_filename = filename.replace('"', '\\"')
            self.send_header("Content-Disposition", f'{disp_type}; filename="{encoded_filename}"')
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            with open(target_path, "rb") as f:
                shutil.copyfileobj(f, self.wfile, length=64 * 1024)
        except Exception as e:
            self.send_error_json(f"Erro ao transmitir arquivo: {e}", status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_upload(self) -> None:
        """Processa o upload multipart de um ou mais arquivos para uploads/."""
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self.send_error_json("Requisição inválida: Esperado multipart/form-data", status=HTTPStatus.BAD_REQUEST)
            return

        # Extrai boundary do header
        boundary_match = re.search(r"boundary=([^;]+)", content_type)
        if not boundary_match:
            self.send_error_json("Boundary multipart ausente no cabeçalho", status=HTTPStatus.BAD_REQUEST)
            return

        raw_boundary = boundary_match.group(1).strip("\"'")
        boundary = raw_boundary.encode("utf-8")

        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self.send_error_json("Content-Length inválido", status=HTTPStatus.BAD_REQUEST)
            return

        if content_length <= 0:
            self.send_error_json("Nenhum conteúdo recebido para upload", status=HTTPStatus.BAD_REQUEST)
            return

        parsed_url = urlparse(self.path)
        query = parse_qs(parsed_url.query)
        current_path = query.get("path", [""])[0]

        uploads_dir = get_uploads_dir(current_path)
        os.makedirs(uploads_dir, exist_ok=True)

        try:
            parser = MultipartParser(self.rfile, content_length, boundary, uploads_dir)
            saved = parser.parse()

            if not saved:
                self.send_error_json("Nenhum arquivo válido foi encontrado no formulário de upload", status=HTTPStatus.BAD_REQUEST)
                return

            self.send_json_response({
                "ok": True,
                "message": f"{len(saved)} arquivo(s) enviado(s) com sucesso para a pasta de uploads.",
                "saved": saved
            })
        except Exception as e:
            self.send_error_json(f"Erro ao processar upload: {str(e)}", status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_api_config(self) -> None:
        """Atualiza preferências como toggles do menu de ferramentas."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)
        except Exception:
            self.send_error_json("JSON inválido no corpo da requisição", status=HTTPStatus.BAD_REQUEST)
            return

        cfg = load_config()
        if "ftp_enabled" in data:
            cfg["ftp_enabled"] = bool(data["ftp_enabled"])
        if "filezilla_manager_enabled" in data:
            cfg["filezilla_manager_enabled"] = bool(data["filezilla_manager_enabled"])
        if "theme" in data:
            cfg["theme"] = str(data["theme"])

        save_config(cfg)
        self.send_json_response({"ok": True, "config": cfg})

    def handle_download_batch(self) -> None:
        """Processa a solicitação POST de múltiplos arquivos selecionados para download em ZIP."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)
            files = data.get("files", [])
        except Exception:
            self.send_error_json("JSON inválido no corpo da requisição", status=HTTPStatus.BAD_REQUEST)
            return

        self._send_zip_of_files(files)

    def _send_zip_of_files(self, files: List[str]) -> None:
        """Gera um arquivo ZIP em memória a partir da lista de caminhos relativos e transmite."""
        if not files or not isinstance(files, list):
            self.send_error_json("Nenhum arquivo especificado para download", status=HTTPStatus.BAD_REQUEST)
            return

        valid_files: List[Tuple[str, str]] = []

        for rel_file in files:
            safe_path = resolve_safe_path(str(rel_file))
            if safe_path and os.path.exists(safe_path) and os.path.isfile(safe_path):
                valid_files.append((safe_path, os.path.basename(safe_path)))

        if not valid_files:
            self.send_error_json("Nenhum arquivo válido encontrado para compor o ZIP", status=HTTPStatus.NOT_FOUND)
            return

        try:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                seen_names: Dict[str, int] = {}
                for full_path, arc_name in valid_files:
                    if arc_name in seen_names:
                        seen_names[arc_name] += 1
                        base, ext = os.path.splitext(arc_name)
                        arc_name = f"{base}_{seen_names[arc_name]}{ext}"
                    else:
                        seen_names[arc_name] = 0
                    zip_file.write(full_path, arcname=arc_name)

            zip_bytes = zip_buffer.getvalue()
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fileserver_{timestamp_str}.zip"

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(zip_bytes)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(zip_bytes)
        except Exception as e:
            self.send_error_json(f"Erro ao gerar pacote ZIP: {e}", status=HTTPStatus.INTERNAL_SERVER_ERROR)

