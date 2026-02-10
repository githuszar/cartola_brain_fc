"""
FantasyBrain V1.0 - Sistema de Cache Local

Cache em arquivo JSON sem dependências externas.
Substitui Redis por armazenamento local simples.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Any

# Diretório de cache
CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")


def set_cache(key: str, data: Any, expiration: int = 3600) -> None:
    """
    Salva dados no cache local.

    Args:
        key: Identificador único do cache
        data: Dados a serem salvos (deve ser serializável em JSON)
        expiration: Tempo de expiração em segundos (padrão: 1 hora)
    """
    os.makedirs(CACHE_DIR, exist_ok=True)

    # Sanitiza a key para ser um nome de arquivo válido
    safe_key = key.replace("/", "_").replace("\\", "_")
    cache_file = os.path.join(CACHE_DIR, f"{safe_key}.json")

    cache_data = {
        "data": data,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(seconds=expiration)).isoformat()
    }

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False)
    except Exception as e:
        print(f"[Cache] Erro ao salvar: {e}")


def get_cache(key: str) -> Optional[Any]:
    """
    Recupera dados do cache se não estiver expirado.

    Args:
        key: Identificador único do cache

    Returns:
        Dados do cache ou None se expirado/inexistente
    """
    safe_key = key.replace("/", "_").replace("\\", "_")
    cache_file = os.path.join(CACHE_DIR, f"{safe_key}.json")

    if not os.path.exists(cache_file):
        return None

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            cache_data = json.load(f)

        expires_at = datetime.fromisoformat(cache_data["expires_at"])

        if expires_at < datetime.now():
            # Cache expirado, remove o arquivo
            os.remove(cache_file)
            return None

        return cache_data["data"]

    except Exception as e:
        print(f"[Cache] Erro ao ler: {e}")
        return None


def clear_cache() -> int:
    """
    Limpa todo o cache.

    Returns:
        Número de arquivos removidos
    """
    if not os.path.exists(CACHE_DIR):
        return 0

    count = 0
    for filename in os.listdir(CACHE_DIR):
        if filename.endswith(".json"):
            try:
                os.remove(os.path.join(CACHE_DIR, filename))
                count += 1
            except Exception:
                pass

    return count


def cache_stats() -> dict:
    """
    Retorna estatísticas do cache.

    Returns:
        Dicionário com informações do cache
    """
    if not os.path.exists(CACHE_DIR):
        return {"total_files": 0, "total_size_kb": 0, "files": []}

    files = []
    total_size = 0

    for filename in os.listdir(CACHE_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(CACHE_DIR, filename)
            size = os.path.getsize(filepath)
            total_size += size

            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                expires_at = datetime.fromisoformat(data["expires_at"])
                expired = expires_at < datetime.now()
            except Exception:
                expired = True

            files.append({
                "key": filename.replace(".json", ""),
                "size_kb": round(size / 1024, 2),
                "expired": expired
            })

    return {
        "total_files": len(files),
        "total_size_kb": round(total_size / 1024, 2),
        "files": files
    }
