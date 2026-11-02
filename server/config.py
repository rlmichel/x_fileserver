"""Módulo de carregamento e persistência de configurações."""

import json
import os
from typing import Any, Dict, Optional, Tuple

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_FILE = os.path.join(PROJECT_ROOT, "config.json")

DEFAULT_CONFIG: Dict[str, Any] = {
    "port": 9876,
    "base_dir": "files",
    "external_shared_dir": "X:\\Shared",
    "shared_alias": "shared",
    "uploads_subfolder": "uploads",
    "ftp_enabled": False,
    "filezilla_manager_enabled": False,
    "theme": "dark",
    "version": "1.0.0"
}


def load_config() -> Dict[str, Any]:
    """Carrega as configurações do arquivo JSON ou inicializa com valores padrão."""
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    config.update(data)
        except Exception:
            pass
    else:
        save_config(config)
    return config


def save_config(config: Dict[str, Any]) -> None:
    """Persiste as configurações no arquivo config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Aviso] Não foi possível salvar config.json: {e}")


def get_base_files_dir() -> str:
    """
    Retorna o caminho absoluto da pasta inicial onde o fileserver está rodando (/fileserver/files/).
    Cria a pasta automaticamente se ela não existir.
    """
    cfg = load_config()
    raw_base = cfg.get("base_dir", "files")

    if os.path.isabs(raw_base):
        base_path = raw_base
    else:
        base_path = os.path.abspath(os.path.join(PROJECT_ROOT, raw_base))

    try:
        os.makedirs(base_path, exist_ok=True)
    except Exception as e:
        print(f"[Aviso] Não foi possível criar pasta base {base_path}: {e}")

    return base_path


def get_external_shared_dir() -> Optional[str]:
    """
    Verifica se a pasta compartilhada externa (ex: X:\\Shared) existe e está acessível.
    Retorna o caminho absoluto normalizado se existir, ou None se não existir (modo universal/Linux).
    """
    cfg = load_config()
    external_dir = cfg.get("external_shared_dir", "X:\\Shared")

    if not external_dir:
        return None

    try:
        if os.path.exists(external_dir) and os.path.isdir(external_dir):
            return os.path.abspath(external_dir)
    except Exception:
        pass

    return None


def get_uploads_dir(subpath: str = "") -> str:
    """
    Retorna a pasta de uploads apropriada.
    Se subpath estiver dentro de 'shared' e a pasta externa X:\\Shared existir, grava em X:\\Shared\\uploads.
    Caso contrário, grava em /fileserver/files/uploads/.
    """
    cfg = load_config()
    uploads_sub = cfg.get("uploads_subfolder", "uploads")
    clean_sub = subpath.strip().replace("\\", "/").strip("/")

    external_dir = get_external_shared_dir()
    if external_dir and (clean_sub == "shared" or clean_sub.startswith("shared/")):
        target_uploads = os.path.join(external_dir, uploads_sub)
    else:
        target_uploads = os.path.join(get_base_files_dir(), uploads_sub)

    try:
        os.makedirs(target_uploads, exist_ok=True)
    except Exception as e:
        print(f"[Aviso] Falha ao criar pasta de uploads ({target_uploads}): {e}")

    return target_uploads


def get_shared_paths() -> Tuple[str, str]:
    """Função utilitária retrocompatível retornando (pasta_base_files, pasta_uploads)."""
    return get_base_files_dir(), get_uploads_dir()
