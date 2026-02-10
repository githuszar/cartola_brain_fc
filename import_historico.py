#!/usr/bin/env python3
"""
FantasyBrain V1.0 - Importação de Dados Históricos do caRtola

Baixa o dataset caRtola (GitHub) e importa dados de 2018-2025 no banco SQLite local.

Uso:
    python import_historico.py                        # Importa tudo (2018-2025)
    python import_historico.py --ano 2023             # Importa só 2023
    python import_historico.py --ano 2023 --rodada 10 # Importa só rodada 10 de 2023
    python import_historico.py --stats                # Mostra o que já foi importado
    python import_historico.py --clean                # Remove dados históricos importados
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime

import pandas as pd

from database import get_connection, migrate_database, DB_PATH

# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

REPO_URL = "https://github.com/henriquepgomide/caRtola.git"
REPO_DIR = os.path.join(os.path.dirname(__file__), "caRtola_data")
RAW_DATA_DIR = os.path.join(REPO_DIR, "data", "01_raw")

ANOS_SUPORTADOS = list(range(2018, 2026))  # 2018 a 2025
ANO_JSON = 2021  # Ano com formato JSON (Mercado_*.txt)

# Mapeamento de colunas do CSV para nomes internos
COLUMN_MAP = {
    "atletas.atleta_id": "jogador_id",
    "atleta_id": "jogador_id",
    "AtletaID": "jogador_id",
    "atletas.rodada_id": "rodada",
    "rodada_id": "rodada",
    "Rodada": "rodada",
    "atletas.clube_id": "clube_id",
    "clube_id": "clube_id",
    "ClubeID": "clube_id",
    "atletas.posicao_id": "posicao_id",
    "posicao_id": "posicao_id",
    "atletas.status_id": "status_id",
    "status_id": "status_id",
    "atletas.pontos_num": "pontuacao",
    "pontos_num": "pontuacao",
    "Pontos": "pontuacao",
    "atletas.preco_num": "preco",
    "preco_num": "preco",
    "Preco": "preco",
    "atletas.variacao_num": "preco_variacao",
    "variacao_num": "preco_variacao",
    "PrecoVariacao": "preco_variacao",
    "atletas.media_num": "media_pontos",
    "media_num": "media_pontos",
    "PontosMedia": "media_pontos",
    "atletas.jogos_num": "jogos_num",
    "jogos_num": "jogos_num",
    "atletas.nome": "nome",
    "atletas.apelido": "apelido",
    "Apelido": "apelido",
    "atletas.foto": "foto_url",
    "atletas.clube.id.full.name": "clube_nome",
    "atletas.entrou_em_campo": "entrou_em_campo",
}

# Mapeamento de scouts (abreviação CSV → nome coluna banco)
SCOUT_MAP = {
    "G": "gols",
    "A": "assistencias",
    "FT": "finalizacoes",
    "FF": "finalizacoes_fora",
    "FD": "finalizacoes_defesa",
    "FS": "faltas_sofridas",
    "PE": "passes",
    "DS": "desarmes",
    "FC": "faltas_cometidas",
    "CA": "cartoes_amarelos",
    "CV": "cartoes_vermelhos",
    "I": "impedimentos",
    "PP": "penaltis_perdidos",
    "DP": "penaltis_defendidos",
    "DE": "defesas",
    "GS": "gols_sofridos",
    "SG": "jogos_sem_sofrer_gols",
    "RB": "roubadas_bola",
    "DD": "defesas_dificeis",
    "GC": "gols_contra",
    "V": "vitorias",
    "PC": "passes_certos",
    "PS": "pre_assistencias",
}

# Todas as colunas de scout no banco (ordem de inserção)
SCOUT_DB_COLS = [
    "gols", "assistencias", "finalizacoes", "finalizacoes_fora",
    "finalizacoes_defesa", "finalizacoes_trave", "passes", "desarmes",
    "faltas_cometidas", "faltas_sofridas", "cartoes_amarelos", "cartoes_vermelhos",
    "impedimentos", "penaltis_perdidos", "penaltis_defendidos", "defesas",
    "gols_sofridos", "jogos_sem_sofrer_gols", "roubadas_bola", "defesas_dificeis",
    "gols_contra", "vitorias", "passes_certos", "pre_assistencias",
]

# Nota: "finalizacoes_trave" não existe como scout separado — FT mapeia para "finalizacoes"
# No banco original, "finalizacoes" = FT (trave) e "finalizacoes_defesa" = FD.
# Mantemos essa convenção: FT → finalizacoes (coluna de trave no banco).
# A coluna "finalizacoes_trave" fica em 0 (legacy, sem uso nos dados do caRtola).


# =============================================================================
# FUNÇÕES DE DOWNLOAD
# =============================================================================

def clonar_ou_atualizar_repo():
    """Clona o repositório caRtola ou atualiza se já existir."""
    if os.path.exists(os.path.join(REPO_DIR, ".git")):
        print("[GIT] Atualizando repositório caRtola...")
        result = subprocess.run(
            ["git", "-C", REPO_DIR, "pull", "--ff-only"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"   ✓ {result.stdout.strip()}")
        else:
            print(f"   ⚠ Pull falhou, usando dados existentes: {result.stderr.strip()}")
    else:
        print("[GIT] Clonando repositório caRtola (pode demorar)...")
        result = subprocess.run(
            ["git", "clone", "--depth", "1", REPO_URL, REPO_DIR],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("   ✓ Clone concluído")
        else:
            print(f"   ❌ Erro ao clonar: {result.stderr.strip()}")
            sys.exit(1)


# =============================================================================
# FUNÇÕES DE LEITURA E NORMALIZAÇÃO
# =============================================================================

def listar_arquivos_rodada(ano):
    """Lista os arquivos de rodada disponíveis para um ano."""
    ano_dir = os.path.join(RAW_DATA_DIR, str(ano))
    if not os.path.exists(ano_dir):
        return []

    if ano == ANO_JSON:
        # 2021: arquivos Mercado_*.txt
        files = []
        for f in sorted(os.listdir(ano_dir)):
            match = re.match(r"Mercado_(\d+)\.txt$", f)
            if match:
                rodada_num = int(match.group(1))
                files.append((rodada_num, os.path.join(ano_dir, f)))
        return files
    else:
        # Outros anos: rodada-*.csv
        files = []
        for f in sorted(os.listdir(ano_dir)):
            match = re.match(r"rodada-(\d+)\.csv$", f)
            if match:
                rodada_num = int(match.group(1))
                files.append((rodada_num, os.path.join(ano_dir, f)))
        return files


def ler_csv_rodada(filepath, ano, rodada_num):
    """Lê um CSV de rodada e retorna lista de dicts normalizados."""
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        print(f"   ⚠ Erro ao ler {filepath}: {e}")
        return []

    # Renomear colunas usando mapeamento
    rename = {}
    for col in df.columns:
        if col in COLUMN_MAP:
            rename[col] = COLUMN_MAP[col]
    df = df.rename(columns=rename)

    # Garantir coluna rodada
    if "rodada" not in df.columns:
        df["rodada"] = rodada_num

    registros = []
    for _, row in df.iterrows():
        jogador_id = row.get("jogador_id")
        if pd.isna(jogador_id):
            continue

        # Dados do jogador
        reg = {
            "jogador_id": int(jogador_id),
            "rodada": int(row.get("rodada", rodada_num)),
            "temporada": ano,
            "clube_id": _safe_int(row.get("clube_id")),
            "posicao_id": _safe_int(row.get("posicao_id")),
            "status_id": _safe_int(row.get("status_id")),
            "pontuacao": _safe_float(row.get("pontuacao")),
            "preco": _safe_float(row.get("preco")),
            "preco_variacao": _safe_float(row.get("preco_variacao")),
            "media_pontos": _safe_float(row.get("media_pontos")),
            "jogos_num": _safe_int(row.get("jogos_num", 0)),
            "nome": _safe_str(row.get("nome")),
            "apelido": _safe_str(row.get("apelido")),
            "foto_url": _safe_str(row.get("foto_url")),
            "clube_nome": _safe_str(row.get("clube_nome")),
            "entrou_em_campo": _safe_int(row.get("entrou_em_campo", 0)),
        }

        # Scouts — ler diretamente das colunas originais do CSV
        scouts = {}
        for abbrev, db_col in SCOUT_MAP.items():
            val = row.get(abbrev)
            if pd.notna(val) if isinstance(val, float) else val is not None:
                scouts[db_col] = int(val) if pd.notna(val) else 0
            else:
                scouts[db_col] = 0

        reg["scouts"] = scouts
        registros.append(reg)

    return registros


def ler_json_rodada(filepath, ano, rodada_num):
    """Lê um arquivo JSON (Mercado_*.txt do 2021) e retorna lista de dicts normalizados."""
    try:
        # Tentar utf-8 primeiro, fallback para latin-1
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                with open(filepath, "r", encoding=enc) as f:
                    data = json.load(f)
                break
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        else:
            print(f"   ⚠ Não foi possível decodificar {filepath}")
            return []
    except Exception as e:
        print(f"   ⚠ Erro ao ler JSON {filepath}: {e}")
        return []

    atletas = data.get("atletas", [])
    if isinstance(atletas, dict):
        atletas = list(atletas.values())

    registros = []
    for atleta in atletas:
        jogador_id = atleta.get("atleta_id")
        if not jogador_id:
            continue

        reg = {
            "jogador_id": int(jogador_id),
            "rodada": rodada_num,
            "temporada": ano,
            "clube_id": _safe_int(atleta.get("clube_id")),
            "posicao_id": _safe_int(atleta.get("posicao_id")),
            "status_id": _safe_int(atleta.get("status_id")),
            "pontuacao": _safe_float(atleta.get("pontos_num")),
            "preco": _safe_float(atleta.get("preco_num")),
            "preco_variacao": _safe_float(atleta.get("variacao_num")),
            "media_pontos": _safe_float(atleta.get("media_num")),
            "jogos_num": _safe_int(atleta.get("jogos_num", 0)),
            "nome": atleta.get("nome"),
            "apelido": atleta.get("apelido"),
            "foto_url": atleta.get("foto"),
            "clube_nome": None,
            "entrou_em_campo": _safe_int(atleta.get("entrou_em_campo", 0)),
        }

        # Scouts do JSON vêm como dict dentro do atleta
        scout_raw = atleta.get("scout", {}) or {}
        scouts = {}
        for abbrev, db_col in SCOUT_MAP.items():
            scouts[db_col] = int(scout_raw.get(abbrev, 0) or 0)

        reg["scouts"] = scouts
        registros.append(reg)

    return registros


# =============================================================================
# FUNÇÕES DE INSERÇÃO NO BANCO
# =============================================================================

def inserir_registros(registros, ano):
    """Insere registros normalizados nas 3 tabelas do banco."""
    if not registros:
        return 0, 0, 0

    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    count_pont = 0
    count_scout = 0
    count_hist = 0

    for reg in registros:
        jid = reg["jogador_id"]
        rodada = reg["rodada"]
        temporada = reg["temporada"]

        # 1. pontuacoes_jogadores
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO pontuacoes_jogadores
                (jogador_id, rodada, pontuacao, preco, preco_variacao, clube_id,
                 adversario_id, mando, foi_titular, entrou_em_campo, temporada, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?)
            """, (
                jid, rodada,
                reg["pontuacao"], reg["preco"], reg["preco_variacao"],
                reg["clube_id"],
                1 if reg["entrou_em_campo"] else 0,
                reg["entrou_em_campo"],
                temporada, now
            ))
            count_pont += 1
        except Exception as e:
            print(f"   ⚠ Erro pontuação jogador {jid} rodada {rodada}: {e}")

        # 2. scouts_jogadores
        try:
            scouts = reg["scouts"]
            scout_values = [scouts.get(col, 0) for col in SCOUT_DB_COLS]

            cursor.execute(f"""
                INSERT OR REPLACE INTO scouts_jogadores
                (jogador_id, rodada, {', '.join(SCOUT_DB_COLS)}, temporada, atualizado_em)
                VALUES (?, ?, {', '.join(['?'] * len(SCOUT_DB_COLS))}, ?, ?)
            """, (jid, rodada, *scout_values, temporada, now))
            count_scout += 1
        except Exception as e:
            print(f"   ⚠ Erro scout jogador {jid} rodada {rodada}: {e}")

        # 3. historico_jogadores
        try:
            cursor.execute("""
                INSERT INTO historico_jogadores
                (jogador_id, rodada, temporada, clube_id, preco, variacao_preco, media_pontos,
                 jogos_num, status_id, posicao_id, nome, apelido, foto_url, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                jid, rodada, temporada, reg["clube_id"],
                reg["preco"], reg["preco_variacao"], reg["media_pontos"],
                reg["jogos_num"], reg["status_id"], reg["posicao_id"],
                reg["nome"], reg["apelido"], reg["foto_url"], now
            ))
            count_hist += 1
        except Exception as e:
            print(f"   ⚠ Erro histórico jogador {jid} rodada {rodada}: {e}")

    conn.commit()
    conn.close()
    return count_pont, count_scout, count_hist


def limpar_historico_temporada(ano):
    """Remove registros de uma temporada específica (para reimportação)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM historico_jogadores WHERE temporada = ?", (ano,))
    deleted_hist = cursor.rowcount

    conn.commit()
    conn.close()
    return deleted_hist


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def _safe_int(val, default=0):
    if val is None:
        return default
    try:
        if isinstance(val, float) and pd.isna(val):
            return default
        return int(val)
    except (ValueError, TypeError):
        return default


def _safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        if isinstance(val, float) and pd.isna(val):
            return default
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_str(val):
    if val is None:
        return None
    if isinstance(val, float) and pd.isna(val):
        return None
    return str(val)


# =============================================================================
# COMANDOS CLI
# =============================================================================

def importar(ano_filtro=None, rodada_filtro=None):
    """Importa dados históricos do caRtola."""
    # Garantir migração do banco
    migrate_database()

    # Baixar/atualizar repo
    clonar_ou_atualizar_repo()

    if not os.path.exists(RAW_DATA_DIR):
        print(f"❌ Diretório de dados não encontrado: {RAW_DATA_DIR}")
        sys.exit(1)

    anos = [ano_filtro] if ano_filtro else ANOS_SUPORTADOS
    total_pont = 0
    total_scout = 0
    total_hist = 0

    print("\n" + "=" * 60)
    print("FANTASYBRAIN - IMPORTAÇÃO HISTÓRICA caRtola")
    print("=" * 60)

    for ano in anos:
        if ano not in ANOS_SUPORTADOS:
            print(f"\n⚠ Ano {ano} não suportado (suportados: {ANOS_SUPORTADOS[0]}-{ANOS_SUPORTADOS[-1]})")
            continue

        arquivos = listar_arquivos_rodada(ano)
        if not arquivos:
            print(f"\n[{ano}] Nenhum arquivo encontrado")
            continue

        # Filtrar rodada se especificado
        if rodada_filtro:
            arquivos = [(r, f) for r, f in arquivos if r == rodada_filtro]

        print(f"\n[{ano}] {len(arquivos)} rodadas encontradas")

        # Limpar histórico existente da temporada para evitar duplicatas
        deleted = limpar_historico_temporada(ano)
        if deleted > 0:
            print(f"   Removidos {deleted} registros antigos de historico_jogadores")

        ano_pont = 0
        ano_scout = 0
        ano_hist = 0

        for rodada_num, filepath in arquivos:
            # Ler arquivo
            if ano == ANO_JSON:
                registros = ler_json_rodada(filepath, ano, rodada_num)
            else:
                registros = ler_csv_rodada(filepath, ano, rodada_num)

            if not registros:
                continue

            # Inserir no banco
            p, s, h = inserir_registros(registros, ano)
            ano_pont += p
            ano_scout += s
            ano_hist += h

            print(f"   Rodada {rodada_num:2d}: {len(registros)} jogadores importados")

        print(f"   ✓ {ano} concluído: {ano_pont} pontuações, {ano_scout} scouts, {ano_hist} históricos")
        total_pont += ano_pont
        total_scout += ano_scout
        total_hist += ano_hist

    print("\n" + "=" * 60)
    print(f"✅ IMPORTAÇÃO CONCLUÍDA")
    print(f"   Total pontuações: {total_pont:,}")
    print(f"   Total scouts: {total_scout:,}")
    print(f"   Total históricos: {total_hist:,}")
    print(f"   Banco: {DB_PATH}")
    print("=" * 60)


def mostrar_stats():
    """Mostra estatísticas dos dados históricos importados."""
    conn = get_connection()
    cursor = conn.cursor()

    print("=" * 60)
    print("FANTASYBRAIN - DADOS HISTÓRICOS IMPORTADOS")
    print("=" * 60)

    # Pontuações por temporada
    cursor.execute("""
        SELECT temporada, COUNT(*) as total, COUNT(DISTINCT rodada) as rodadas,
               COUNT(DISTINCT jogador_id) as jogadores
        FROM pontuacoes_jogadores
        GROUP BY temporada
        ORDER BY temporada
    """)

    print(f"\n{'Temporada':<12} {'Registros':>10} {'Rodadas':>8} {'Jogadores':>10}")
    print("-" * 44)

    total = 0
    for row in cursor.fetchall():
        print(f"{row[0]:<12} {row[1]:>10,} {row[2]:>8} {row[3]:>10}")
        total += row[1]

    print("-" * 44)
    print(f"{'TOTAL':<12} {total:>10,}")

    # Scouts por temporada
    cursor.execute("SELECT temporada, COUNT(*) FROM scouts_jogadores GROUP BY temporada ORDER BY temporada")
    scout_total = sum(row[1] for row in cursor.fetchall())
    print(f"\nScouts totais: {scout_total:,}")

    # Histórico
    cursor.execute("SELECT temporada, COUNT(*) FROM historico_jogadores GROUP BY temporada ORDER BY temporada")
    hist_total = sum(row[1] for row in cursor.fetchall())
    print(f"Históricos totais: {hist_total:,}")

    print(f"\nBanco: {DB_PATH}")
    print("=" * 60)

    conn.close()


def limpar():
    """Remove todos os dados históricos importados (mantém dados da temporada atual)."""
    conn = get_connection()
    cursor = conn.cursor()

    ano_atual = datetime.now().year

    print("=" * 60)
    print("FANTASYBRAIN - LIMPEZA DE DADOS HISTÓRICOS")
    print("=" * 60)

    for table in ["pontuacoes_jogadores", "scouts_jogadores", "historico_jogadores"]:
        cursor.execute(f"DELETE FROM {table} WHERE temporada < ?", (ano_atual,))
        print(f"   {table}: {cursor.rowcount} registros removidos")

    conn.commit()
    conn.close()

    print(f"\n✓ Dados anteriores a {ano_atual} removidos")
    print("=" * 60)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="FantasyBrain - Importação de dados históricos do caRtola (2018-2025)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python import_historico.py                        # Importa tudo (2018-2025)
  python import_historico.py --ano 2023             # Importa só 2023
  python import_historico.py --ano 2023 --rodada 10 # Importa só rodada 10 de 2023
  python import_historico.py --stats                # Mostra o que já foi importado
  python import_historico.py --clean                # Remove dados históricos
        """
    )

    parser.add_argument("--ano", "-a", type=int, help="Ano específico para importar")
    parser.add_argument("--rodada", "-r", type=int, help="Rodada específica (requer --ano)")
    parser.add_argument("--stats", "-s", action="store_true", help="Mostrar estatísticas dos dados importados")
    parser.add_argument("--clean", action="store_true", help="Remover dados históricos importados")

    args = parser.parse_args()

    if args.stats:
        mostrar_stats()
    elif args.clean:
        limpar()
    else:
        if args.rodada and not args.ano:
            print("❌ --rodada requer --ano")
            sys.exit(1)
        importar(args.ano, args.rodada)


if __name__ == "__main__":
    main()
