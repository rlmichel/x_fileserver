"""Módulo de manipulação e segurança de arquivos e diretórios com suporte universal."""

from datetime import datetime
import mimetypes
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from server.config import get_base_files_dir, get_external_shared_dir


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
    Higieniza o nome de um arquivo para prevenir Path Traversal e caracteres inválidos.
    """
    clean = os.path.basename(filename.replace("\\", "/"))
    clean = re.sub(r'[\x00-\x1f\x7f<>:"/\\|?*]', "_", clean)
    clean = clean.strip(". ")
    if not clean:
        clean = f"arquivo_{int(datetime.now().timestamp())}"
    return clean


def _resolve_within_base(base_dir: str, rel_path: str) -> Optional[str]:
    """Valida e resolve estritamente um caminho relativo dentro de um diretório base."""
    try:
        abs_base = os.path.abspath(base_dir)
        clean_rel = rel_path.strip().replace("\\", "/").lstrip("/")
        target_path = os.path.abspath(os.path.join(abs_base, clean_rel))

        # Garante que target_path esteja dentro de abs_base
        common = os.path.commonpath([abs_base, target_path])
        if common != abs_base:
            return None

        return target_path
    except Exception:
        return None


def resolve_safe_path(rel_path: str, base_dir: Optional[str] = None) -> Optional[str]:
    """
    Resolve um caminho relativo de forma universal e segura:
    - Se rel_path começa com 'shared' e a pasta externa X:\\Shared existe no sistema:
      Resolve dentro de X:\\Shared.
    - Caso contrário:
      Resolve dentro do diretório base local do fileserver (/fileserver/files/).
    """
    clean_rel = rel_path.strip().replace("\\", "/").lstrip("/")
    external_dir = get_external_shared_dir()

    # Roteamento transparente para a pasta compartilhada externa (X:\Shared)
    if external_dir and (clean_rel == "shared" or clean_rel.startswith("shared/")):
        sub_rel = clean_rel[len("shared") :].lstrip("/")
        return _resolve_within_base(external_dir, sub_rel)

    # Roteamento padrão para a pasta base local do fileserver
    target_base = base_dir or get_base_files_dir()
    return _resolve_within_base(target_base, clean_rel)


def list_directory(rel_path: str = "", base_dir: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Lista arquivos e diretórios de forma universal.
    - Na raiz (''), lista a pasta local 'files/' e expõe a pasta 'shared' caso X:\\Shared exista.
    - Em 'shared' ou 'shared/...', lista o conteúdo de X:\\Shared.
    """
    clean_rel = rel_path.strip().replace("\\", "/").strip("/")
    external_dir = get_external_shared_dir()
    is_in_shared = bool(external_dir and (clean_rel == "shared" or clean_rel.startswith("shared/")))

    if is_in_shared:
        assert external_dir is not None
        sub_rel = clean_rel[len("shared") :].lstrip("/")
        target_dir = _resolve_within_base(external_dir, sub_rel)
        active_base = external_dir
    else:
        target_base = base_dir or get_base_files_dir()
        target_dir = _resolve_within_base(target_base, clean_rel)
        active_base = target_base

    if not target_dir:
        return None, "Acesso negado: caminho inválido ou fora da pasta permitida."

    if not os.path.exists(target_dir):
        return None, f"Diretório não encontrado: {clean_rel}"

    if not os.path.isdir(target_dir):
        return None, f"O caminho especificado não é um diretório: {clean_rel}"

    # Determina o parent path para o breadcrumb
    parent_path: Optional[str] = None
    if clean_rel:
        if clean_rel == "shared":
            parent_path = ""
        else:
            parent_rel = os.path.dirname(clean_rel).replace("\\", "/")
            parent_path = parent_rel if parent_rel and parent_rel != "." else ""

    entries: List[Dict[str, Any]] = []

    # Se estivermos na raiz ('') e X:\Shared existir no sistema, adiciona a pasta virtual 'shared'
    if not clean_rel and external_dir:
        try:
            stat_info = os.stat(external_dir)
            ext_mtime = stat_info.st_mtime
            ext_mtime_iso = datetime.fromtimestamp(ext_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            ext_mtime = 0
            ext_mtime_iso = "-"

        entries.append({
            "name": "shared",
            "rel_path": "shared",
            "is_dir": True,
            "size": 0,
            "size_formatted": "-",
            "mtime": ext_mtime,
            "mtime_iso": ext_mtime_iso,
            "mime": "directory",
            "is_shared": True,
        })

    # Lê o conteúdo físico do diretório alvo
    try:
        with os.scandir(target_dir) as it:
            for entry in it:
                try:
                    # Se na raiz já injetamos a pasta virtual 'shared', evita duplicata
                    if not clean_rel and external_dir and entry.name.lower() == "shared":
                        continue

                    stat_info = entry.stat()
                    is_dir = entry.is_dir()
                    size_bytes = 0 if is_dir else stat_info.st_size
                    mtime_dt = datetime.fromtimestamp(stat_info.st_mtime)

                    mime_type = "directory" if is_dir else (mimetypes.guess_type(entry.name)[0] or "application/octet-stream")

                    if clean_rel:
                        item_rel = f"{clean_rel}/{entry.name}"
                    else:
                        item_rel = entry.name

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

    # Ordena: diretórios primeiro (com 'shared' em destaque se existir), depois ordem alfabética
    entries.sort(key=lambda x: (not x["is_dir"], not x.get("is_shared", False), x["name"].lower()))

    return {
        "path": clean_rel,
        "parent": parent_path,
        "entries": entries,
    }, None
