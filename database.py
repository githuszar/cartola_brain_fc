"""
FantasyBrain V1.0 - Configuração do Banco de Dados SQLite

Gerencia a conexão e estrutura do banco de dados local.
"""

import sqlite3
import os
from datetime import datetime

# Caminho do banco de dados SQLite
DB_PATH = os.path.join(os.path.dirname(__file__), "cartola_data.db")

# Mapeamento de posições
POSICOES = {
    1: "Goleiro",
    2: "Lateral",
    3: "Zagueiro",
    4: "Meia",
    5: "Atacante",
    6: "Técnico"
}

# Mapeamento de status
STATUS = {
    2: "Dúvida",
    3: "Suspenso",
    5: "Contundido",
    6: "Nulo",
    7: "Provável"
}


def get_connection():
    """Retorna uma conexão com o banco SQLite"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    return conn


def init_database():
    """Cria as tabelas necessárias no banco SQLite"""
    conn = get_connection()
    cursor = conn.cursor()

    # Tabela de clubes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clubes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        clube_id INTEGER UNIQUE NOT NULL,
        nome TEXT NOT NULL,
        abreviacao TEXT,
        escudo_url TEXT,
        nome_fantasia TEXT,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Tabela de jogadores
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jogadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jogador_id INTEGER UNIQUE NOT NULL,
        nome TEXT,
        apelido TEXT,
        foto_url TEXT,
        clube_id INTEGER,
        clube TEXT,
        posicao_id INTEGER,
        status_id INTEGER,
        preco REAL,
        media_pontos REAL,
        jogos_num INTEGER,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (clube_id) REFERENCES clubes(clube_id)
    )
    """)

    # Tabela de partidas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS partidas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        partida_id INTEGER UNIQUE,
        rodada INTEGER NOT NULL,
        clube_casa_id INTEGER,
        clube_visitante_id INTEGER,
        placar_casa INTEGER,
        placar_visitante INTEGER,
        data_hora TEXT,
        local TEXT,
        valida INTEGER DEFAULT 1,
        encerrada INTEGER DEFAULT 0,
        temporada INTEGER,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (clube_casa_id) REFERENCES clubes(clube_id),
        FOREIGN KEY (clube_visitante_id) REFERENCES clubes(clube_id)
    )
    """)

    # Tabela de pontuações dos jogadores (com adversário)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pontuacoes_jogadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jogador_id INTEGER NOT NULL,
        rodada INTEGER NOT NULL,
        pontuacao REAL,
        preco REAL,
        preco_variacao REAL,
        clube_id INTEGER,
        adversario_id INTEGER,
        mando TEXT,
        foi_titular INTEGER,
        entrou_em_campo INTEGER,
        temporada INTEGER,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(jogador_id, rodada, temporada),
        FOREIGN KEY (clube_id) REFERENCES clubes(clube_id),
        FOREIGN KEY (adversario_id) REFERENCES clubes(clube_id)
    )
    """)

    # Tabela de scouts dos jogadores
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scouts_jogadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jogador_id INTEGER NOT NULL,
        rodada INTEGER NOT NULL,
        gols INTEGER DEFAULT 0,
        assistencias INTEGER DEFAULT 0,
        finalizacoes INTEGER DEFAULT 0,
        finalizacoes_fora INTEGER DEFAULT 0,
        finalizacoes_defesa INTEGER DEFAULT 0,
        finalizacoes_trave INTEGER DEFAULT 0,
        passes INTEGER DEFAULT 0,
        desarmes INTEGER DEFAULT 0,
        faltas_cometidas INTEGER DEFAULT 0,
        faltas_sofridas INTEGER DEFAULT 0,
        cartoes_amarelos INTEGER DEFAULT 0,
        cartoes_vermelhos INTEGER DEFAULT 0,
        impedimentos INTEGER DEFAULT 0,
        penaltis_perdidos INTEGER DEFAULT 0,
        penaltis_defendidos INTEGER DEFAULT 0,
        defesas INTEGER DEFAULT 0,
        gols_sofridos INTEGER DEFAULT 0,
        jogos_sem_sofrer_gols INTEGER DEFAULT 0,
        roubadas_bola INTEGER DEFAULT 0,
        defesas_dificeis INTEGER DEFAULT 0,
        gols_contra INTEGER DEFAULT 0,
        vitorias INTEGER DEFAULT 0,
        passes_certos INTEGER DEFAULT 0,
        pre_assistencias INTEGER DEFAULT 0,
        temporada INTEGER,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(jogador_id, rodada, temporada)
    )
    """)

    # Tabela de histórico de jogadores
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historico_jogadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jogador_id INTEGER NOT NULL,
        rodada INTEGER,
        temporada INTEGER,
        clube_id INTEGER,
        preco REAL,
        variacao_preco REAL,
        media_pontos REAL,
        jogos_num INTEGER,
        status_id INTEGER,
        posicao_id INTEGER,
        nome TEXT,
        apelido TEXT,
        foto_url TEXT,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Tabela de histórico do mercado
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historico_mercado_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rodada INTEGER,
        temporada INTEGER,
        status_mercado INTEGER,
        game_over INTEGER,
        times_escalados INTEGER,
        fechamento TEXT,
        mercado_pos_rodada INTEGER,
        reativar INTEGER,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # NOVA: Tabela de calendário (confrontos por rodada)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS calendario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rodada INTEGER NOT NULL,
        clube_id INTEGER NOT NULL,
        adversario_id INTEGER NOT NULL,
        mando TEXT NOT NULL,
        data_hora TEXT,
        temporada INTEGER,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(rodada, clube_id, temporada),
        FOREIGN KEY (clube_id) REFERENCES clubes(clube_id),
        FOREIGN KEY (adversario_id) REFERENCES clubes(clube_id)
    )
    """)

    # Tabela de posicoes (mapa de posições)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posicoes (
        posicao_id INTEGER PRIMARY KEY,
        nome TEXT NOT NULL
    )
    """)

    # Tabela de rodadas (metadados de cada rodada)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rodadas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rodada INTEGER UNIQUE NOT NULL,
        inicio TEXT,
        fim TEXT,
        status INTEGER,
        temporada INTEGER,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Tabela de destaques por pos-rodada
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pos_rodada_destaques (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rodada INTEGER NOT NULL,
        jogador_id INTEGER NOT NULL,
        tipo TEXT,
        pontuacao REAL,
        meta TEXT,
        temporada INTEGER,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Tabela de mercado destaques / rankings genéricos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mercado_destaques (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rodada INTEGER,
        jogador_id INTEGER,
        tipo TEXT,
        valor REAL,
        temporada INTEGER,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Tabela de rankings (flexível)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rankings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        jogador_id INTEGER,
        pos INTEGER,
        valor REAL,
        rodada INTEGER,
        temporada INTEGER,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def migrate_database():
    """Aplica migrações necessárias no banco existente"""
    conn = get_connection()
    cursor = conn.cursor()

    # Verificar e adicionar colunas novas em pontuacoes_jogadores
    cursor.execute("PRAGMA table_info(pontuacoes_jogadores)")
    columns = [col[1] for col in cursor.fetchall()]

    if "adversario_id" not in columns:
        cursor.execute("ALTER TABLE pontuacoes_jogadores ADD COLUMN adversario_id INTEGER")
        print("[DB] Coluna 'adversario_id' adicionada em pontuacoes_jogadores")

    if "mando" not in columns:
        cursor.execute("ALTER TABLE pontuacoes_jogadores ADD COLUMN mando TEXT")
        print("[DB] Coluna 'mando' adicionada em pontuacoes_jogadores")

    # Verificar e adicionar novas colunas de scouts em scouts_jogadores
    cursor.execute("PRAGMA table_info(scouts_jogadores)")
    scout_columns = [col[1] for col in cursor.fetchall()]

    new_scout_cols = [
        ("roubadas_bola", "INTEGER DEFAULT 0"),
        ("defesas_dificeis", "INTEGER DEFAULT 0"),
        ("gols_contra", "INTEGER DEFAULT 0"),
        ("vitorias", "INTEGER DEFAULT 0"),
        ("passes_certos", "INTEGER DEFAULT 0"),
        ("pre_assistencias", "INTEGER DEFAULT 0"),
    ]
    for col_name, col_type in new_scout_cols:
        if col_name not in scout_columns:
            cursor.execute(f"ALTER TABLE scouts_jogadores ADD COLUMN {col_name} {col_type}")
            print(f"[DB] Coluna '{col_name}' adicionada em scouts_jogadores")

    # Criar tabela calendario se não existir
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS calendario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rodada INTEGER NOT NULL,
        clube_id INTEGER NOT NULL,
        adversario_id INTEGER NOT NULL,
        mando TEXT NOT NULL,
        data_hora TEXT,
        temporada INTEGER,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(rodada, clube_id, temporada),
        FOREIGN KEY (clube_id) REFERENCES clubes(clube_id),
        FOREIGN KEY (adversario_id) REFERENCES clubes(clube_id)
    )
    """)

    # Garantir novas tabelas para integrações
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posicoes (
        posicao_id INTEGER PRIMARY KEY,
        nome TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rodadas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rodada INTEGER UNIQUE NOT NULL,
        inicio TEXT,
        fim TEXT,
        status INTEGER,
        temporada INTEGER,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Garantir tabelas adicionais para destaques/rankings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pos_rodada_destaques (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rodada INTEGER NOT NULL,
        jogador_id INTEGER NOT NULL,
        tipo TEXT,
        pontuacao REAL,
        meta TEXT,
        temporada INTEGER,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mercado_destaques (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rodada INTEGER,
        jogador_id INTEGER,
        tipo TEXT,
        valor REAL,
        temporada INTEGER,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rankings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        jogador_id INTEGER,
        pos INTEGER,
        valor REAL,
        rodada INTEGER,
        temporada INTEGER,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def get_stats():
    """Retorna estatísticas do banco de dados"""
    conn = get_connection()
    cursor = conn.cursor()

    stats = {}
    tables = [
        "clubes", "jogadores", "partidas",
        "pontuacoes_jogadores", "scouts_jogadores",
        "historico_jogadores", "historico_mercado_status", "calendario"
    ]

    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        except Exception:
            stats[table] = 0

    # Rodadas com dados
    cursor.execute("SELECT DISTINCT rodada FROM partidas ORDER BY rodada")
    stats["rodadas_com_dados"] = [row[0] for row in cursor.fetchall()]

    # Última atualização
    cursor.execute("SELECT MAX(atualizado_em) FROM jogadores")
    result = cursor.fetchone()[0]
    stats["ultima_atualizacao"] = result if result else "Nunca"

    conn.close()
    return stats


# Inicializar/migrar banco ao importar o módulo
if os.path.exists(DB_PATH):
    migrate_database()
else:
    init_database()
