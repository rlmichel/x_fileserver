"""Módulo de utilitários de rede para detecção de IP local e de LAN."""

import socket


def get_lan_ip() -> str:
    """
    Detecta o endereço IP da interface de rede local (LAN).
    Conecta um socket UDP para um endereço público sem enviar pacotes reais,
    obtendo o IP do adaptador ativo atribuído pelo roteador.
    """
    try:
        # Usa socket UDP; não chega a estabelecer conexão TCP ou enviar pacotes
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except Exception:
        pass

    # Fallback 1: pelo hostname do sistema
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    # Fallback 2: loopback padrão
    return "127.0.0.1"
