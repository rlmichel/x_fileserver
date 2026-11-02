"""Módulo de manipulação e segurança de arquivos e diretórios."""

from datetime import datetime
import mimetypes
import os
import re
from typing import Any, Dict, List, Optional, Tuple


def format_size(size_bytes: int) -> str:
    """Converte tamanho em bytes para representação legível (Bytes, KB, MB, GB, TB)."""
    if size_bytes < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    value = float(size_bytes)
    unit_index = 0
    while value >= 1024.0 and unit_index < len(units) - 1:
        value /= 1024.0
        unit_index += 1

    if unit_index == 0:
        return f"{int(value)} B"
    return f"{value:.1f} {units[unit_index]}"


def sanitize_filename(filename: str) -> str:
    """
    Higieniza o nome de um arquivo para prevenir Path Traversal e injeções.
    Remove diretórios, barras invertidas/normais e caracteres inválidos.
    """
    # Remove qualquer caminho prefixado enviado pelo cliente
    clean = os.path.basename(filename.replace("\\", "/"))
    # Remove caracteres de controle nulos e outros caracteres arriscados
    clean = re.sub(r'[\x00-\x1f\x7f<>:"/\\|?*]', "_", clean)
    # Evita nomes perigosos como '.' ou '..'
    clean = clean.strip(". ")
    if not clean:
        clean = f"arquivo_{int(datetime.now().timestamp())}"
    return clean


def resolve_safe_path(base_dir: str, rel_path: str) -> Optional[str]:
    """
    Resolve um caminho relativo dentro de base_dir de forma estritamente segura.
    Garante que o caminho final esteja dentro de base_dir (prevenindo path traversal).
    Retorna o caminho absoluto seguro ou None se for inválido/violador.
    """
    try:
        abs_base = os.path.abspath(base_dir)
        # Normaliza barras e remove separadores iniciais
        clean_rel = rel_path.strip().replace("\\", "/").lstrip("/")
        
        # Cria caminho absoluto proposto
        target_path = os.path.abspath(os.path.join(abs_base, clean_rel))
        
        # Verifica se base_dir é prefixo estrito do target_path
        common = os.path.commonpath([abs_base, target_path])
        if common != abs_base:
            return None
            
        return target_path
    except Exception:
        return None


def list_directory(base_dir: str, rel_path: str = "") -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Lista arquivos e subdiretórios de um caminho seguro.
    Retorna (dicionário_com_dados, erro_se_houver).
    """
    target_dir = resolve_safe_path(base_dir, rel_path)
    if not target_dir:
        return None, "Acesso negado: caminho inválido ou fora da pasta compartilhada."

    if not os.path.exists(target_dir):
        return None, f"Diretório não encontrado: {rel_path}"

    if not os.path.isdir(target_dir):
        return None, f"O caminho especificado não é um diretório: {rel_path}"

    abs_base = os.path.abspath(base_dir)
    # Caminho relativo atual normalizado com barras normais
    current_rel = os.path.relpath(target_dir, abs_base).replace("\\", "/")
    if current_rel == ".":
        current_rel = ""

    # Determina o parent path para o botão voltar / breadcrumbs
    parent_path: Optional[str] = None
    if current_rel:
        parent_rel = os.path.dirname(current_rel).replace("\\", "/")
        parent_path = parent_rel if parent_rel and parent_rel != "." else ""

    entries: List[Dict[str, Any]] = []

    try:
        with os.scandir(target_dir) as it:
            for entry in it:
                try:
                    stat_info = entry.stat()
                    is_dir = entry.is_dir()
                    size_bytes = 0 if is_dir else stat_info.st_size
                    mtime_dt = datetime.fromtimestamp(stat_info.st_mtime)

                    # Obter tipo MIME para arquivos
                    mime_type = "directory" if is_dir else (mimetypes.guess_type(entry.name)[0] or "application/octet-stream")

                    # Subcaminho relativo do item
                    item_rel = f"{current_rel}/{entry.name}" if current_rel else entry.name

                    entries.append({
                        "name": entry.name,
                        "rel_path": item_rel,
                        "is_dir": is_dir,
                        "size": size_bytes,
                        "size_formatted": "-" if is_dir else format_size(size_bytes),
                        "mtime": stat_info.st_mtime,
                        "mtime_iso": mtime_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "mime": mime_type,
                    })
                except (PermissionError, FileNotFoundError, OSError):
                    continue
    except PermissionError:
        return None, "Permissão negada para ler o diretório."
    except Exception as e:
        return None, f"Erro ao listar diretório: {str(e)}"

    # Ordena por padrão: diretórios primeiro, depois em ordem alfabética
    entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

    return {
        "path": current_rel,
        "parent": parent_path,
        "entries": entries,
    }, None
