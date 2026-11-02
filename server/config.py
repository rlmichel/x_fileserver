"""Módulo de carregamento e persistência de configurações."""

import json
import os
import platform
from typing import Any, Dict

CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.json"))

DEFAULT_CONFIG: Dict[str, Any] = {
    "port": 9876,
    "shared_dir": "X:\\Shared",
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


def get_shared_paths() -> tuple[str, str]:
    """
    Retorna (caminho_base_compartilhado, caminho_pasta_uploads).
    Garante suporte ao Windows (X:\\Shared) e fallback seguro em ambientes Linux/Unix
    quando o caminho de unidade Windows não puder ser montado/acessado.
    Cria a pasta uploads se não existir.
    """
    cfg = load_config()
    raw_shared = cfg.get("shared_dir", "X:\\Shared")
    uploads_sub = cfg.get("uploads_subfolder", "uploads")

    is_windows = platform.system().lower().startswith("win")

    shared_dir = raw_shared
    if not is_windows:
        # Se estiver em Linux/macOS e for um caminho do tipo drive Windows (ex: X:\...)
        if ":" in raw_shared or "\\" in raw_shared:
            fallback_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "shared"))
            shared_dir = fallback_dir

    try:
        os.makedirs(shared_dir, exist_ok=True)
    except Exception:
        # Se a unidade X:\ não estiver conectada ou sem permissão, usa pasta local ./shared
        fallback_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "shared"))
        os.makedirs(fallback_dir, exist_ok=True)
        shared_dir = fallback_dir

    uploads_dir = os.path.join(shared_dir, uploads_sub)
    try:
        os.makedirs(uploads_dir, exist_ok=True)
    except Exception as e:
        print(f"[Aviso] Falha ao criar pasta de uploads ({uploads_dir}): {e}")

    return shared_dir, uploads_dir
