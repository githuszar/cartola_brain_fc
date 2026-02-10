#!/usr/bin/env python3
"""Script rapido: busca pontuacoes de uma rodada e salva no banco."""

import sys
from pathlib import Path
# Ensure project root is in PYTHONPATH to import local modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cartola_service import CartolaService


def main():
    service = CartolaService()
    rodada = 1
    print(f"Buscando /atletas/pontuados/{rodada} (sem cache)...")

    try:
        data = service.fetch_atletas_pontuados(rodada, use_cache=False)
    except Exception as e:
        print(f"Erro ao buscar pontuacoes: {e}")
        sys.exit(2)

    if not data or not data.get('atletas'):
        print("Nenhuma pontuacao de jogadores retornada pela API.")
        sys.exit(0)

    print(f"Encontrado(s) {len(data.get('atletas', {}))} registros. Salvando no banco...")

    try:
        saved = service.salvar_pontuacoes_jogadores(data, rodada)
        print(f"Salvas {saved} pontuacoes de jogadores na rodada {rodada}.")
    except Exception as e:
        print(f"Erro ao salvar pontuacoes: {e}")
        sys.exit(3)

    sys.exit(0)


if __name__ == "__main__":
    main()
