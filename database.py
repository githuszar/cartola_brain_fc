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

    # Tabelas de tracking de recomendacoes
    _init_recomendacoes_tables(cursor)

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

    # Criar tabelas de tracking de recomendacoes
    _init_recomendacoes_tables(cursor)

    conn.commit()
    conn.close()


def _init_recomendacoes_tables(cursor):
    """Cria tabelas para tracking de recomendacoes (chamada dentro de migrate)"""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recomendacoes_salvas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rodada INTEGER NOT NULL,
        temporada INTEGER NOT NULL,
        formacao TEXT NOT NULL,
        orcamento REAL NOT NULL,
        custo_total REAL NOT NULL,
        pontuacao_prevista REAL NOT NULL,
        pontuacao_real REAL,
        metodo TEXT NOT NULL,
        capitao_id INTEGER,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        validado_em TEXT,
        UNIQUE(rodada, temporada, formacao, orcamento, metodo)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recomendacao_jogadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recomendacao_id INTEGER NOT NULL,
        jogador_id INTEGER NOT NULL,
        posicao_id INTEGER NOT NULL,
        clube_id INTEGER NOT NULL,
        preco REAL NOT NULL,
        media_base REAL NOT NULL,
        media_ajustada REAL NOT NULL,
        multiplicador REAL NOT NULL,
        pontuacao_prevista REAL NOT NULL,
        pontuacao_real REAL,
        is_capitao INTEGER DEFAULT 0,
        contextos TEXT,
        adversario_id INTEGER,
        mando TEXT,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (recomendacao_id) REFERENCES recomendacoes_salvas(id) ON DELETE CASCADE,
        FOREIGN KEY (jogador_id) REFERENCES jogadores(jogador_id),
        FOREIGN KEY (clube_id) REFERENCES clubes(clube_id)
    )
    """)


def salvar_recomendacao(rodada, temporada, formacao, orcamento, custo_total,
                        pontuacao_prevista, metodo, capitao_id, jogadores):
    """
    Salva uma recomendacao e seus jogadores no banco.
    Idempotente: se ja existe para mesma (rodada, temporada, formacao, orcamento, metodo), atualiza.

    Args:
        jogadores: Lista de dicts com: jogador_id, posicao_id, clube_id,
                   preco, media_base, media_ajustada, multiplicador,
                   pontuacao_prevista, is_capitao, contextos, adversario_id, mando

    Returns:
        recomendacao_id ou None se erro
    """
    import json

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO recomendacoes_salvas
            (rodada, temporada, formacao, orcamento, custo_total,
             pontuacao_prevista, metodo, capitao_id, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(rodada, temporada, formacao, orcamento, metodo)
            DO UPDATE SET
                custo_total = excluded.custo_total,
                pontuacao_prevista = excluded.pontuacao_prevista,
                capitao_id = excluded.capitao_id,
                criado_em = excluded.criado_em,
                pontuacao_real = NULL,
                validado_em = NULL
        """, (rodada, temporada, formacao, orcamento, custo_total,
              pontuacao_prevista, metodo, capitao_id,
              datetime.now().isoformat()))

        cursor.execute("""
            SELECT id FROM recomendacoes_salvas
            WHERE rodada = ? AND temporada = ? AND formacao = ?
              AND orcamento = ? AND metodo = ?
        """, (rodada, temporada, formacao, orcamento, metodo))

        rec_id = cursor.fetchone()[0]

        # Limpar jogadores antigos e reinserir
        cursor.execute("DELETE FROM recomendacao_jogadores WHERE recomendacao_id = ?", (rec_id,))

        for jog in jogadores:
            contextos_json = json.dumps(jog.get('contextos', {}))
            cursor.execute("""
                INSERT INTO recomendacao_jogadores
                (recomendacao_id, jogador_id, posicao_id, clube_id,
                 preco, media_base, media_ajustada, multiplicador,
                 pontuacao_prevista, is_capitao, contextos,
                 adversario_id, mando, criado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec_id,
                jog['jogador_id'],
                jog['posicao_id'],
                jog['clube_id'],
                jog['preco'],
                jog['media_base'],
                jog['media_ajustada'],
                jog['multiplicador'],
                jog['pontuacao_prevista'],
                1 if jog.get('is_capitao') else 0,
                contextos_json,
                jog.get('adversario_id'),
                jog.get('mando'),
                datetime.now().isoformat()
            ))

        conn.commit()
        return rec_id

    except Exception as e:
        print(f"[DB] Erro ao salvar recomendacao: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def validar_recomendacao(recomendacao_id):
    """
    Busca pontuacoes reais dos jogadores e atualiza a recomendacao.

    Returns:
        dict com {recomendacao_id, rodada, jogadores_validados, pontuacao_real} ou None
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT rodada, temporada, capitao_id
            FROM recomendacoes_salvas WHERE id = ?
        """, (recomendacao_id,))

        rec = cursor.fetchone()
        if not rec:
            return None

        rodada, temporada, capitao_id = rec[0], rec[1], rec[2]

        # Verificar se existem pontuacoes reais para esta rodada
        cursor.execute("""
            SELECT COUNT(*) FROM pontuacoes_jogadores
            WHERE rodada = ? AND temporada = ? AND pontuacao IS NOT NULL
        """, (rodada, temporada))
        n_pontuacoes = cursor.fetchone()[0]

        if n_pontuacoes == 0:
            # Rodada ainda nao tem dados reais — nao validar
            return {'recomendacao_id': recomendacao_id, 'rodada': rodada,
                    'jogadores_validados': 0, 'pontuacao_real': None,
                    'sem_dados': True}

        cursor.execute("""
            SELECT id, jogador_id, is_capitao
            FROM recomendacao_jogadores WHERE recomendacao_id = ?
        """, (recomendacao_id,))

        jogadores = cursor.fetchall()
        pontuacao_real_total = 0
        jogadores_validados = 0

        for jog_rec_id, jogador_id, is_cap in jogadores:
            cursor.execute("""
                SELECT pontuacao FROM pontuacoes_jogadores
                WHERE jogador_id = ? AND rodada = ? AND temporada = ?
            """, (jogador_id, rodada, temporada))

            pont_row = cursor.fetchone()
            pont_real = pont_row[0] if pont_row and pont_row[0] is not None else 0.0

            # Capitao pontua em dobro
            pont_contribuicao = pont_real * 2 if is_cap else pont_real
            pontuacao_real_total += pont_contribuicao

            cursor.execute("""
                UPDATE recomendacao_jogadores SET pontuacao_real = ? WHERE id = ?
            """, (pont_real, jog_rec_id))

            jogadores_validados += 1

        cursor.execute("""
            UPDATE recomendacoes_salvas
            SET pontuacao_real = ?, validado_em = ?
            WHERE id = ?
        """, (pontuacao_real_total, datetime.now().isoformat(), recomendacao_id))

        conn.commit()

        return {
            'recomendacao_id': recomendacao_id,
            'rodada': rodada,
            'jogadores_validados': jogadores_validados,
            'pontuacao_real': pontuacao_real_total
        }

    except Exception as e:
        print(f"[DB] Erro ao validar recomendacao {recomendacao_id}: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def obter_recomendacoes_pendentes():
    """Retorna recomendacoes que ainda nao foram validadas (pontuacao_real IS NULL)"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, rodada, temporada, formacao, orcamento, metodo,
               pontuacao_prevista, criado_em
        FROM recomendacoes_salvas
        WHERE pontuacao_real IS NULL
        ORDER BY rodada ASC, criado_em DESC
    """)

    recs = []
    for row in cursor.fetchall():
        recs.append({
            'id': row[0], 'rodada': row[1], 'temporada': row[2],
            'formacao': row[3], 'orcamento': row[4], 'metodo': row[5],
            'pontuacao_prevista': row[6], 'criado_em': row[7]
        })

    conn.close()
    return recs


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
