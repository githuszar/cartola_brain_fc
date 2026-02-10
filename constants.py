"""
FantasyBrain V1.0 - Constantes e configurações do sistema de recomendação

Tabela final do Brasileirão 2024 e multiplicadores de contexto.
"""

# ==================== TABELA FINAL BRASILEIRÃO 2024 ====================
# Posição final de cada clube (clube_id -> posição 1-20)
# Fonte: Brasileirão 2024 - Classificação final
# Nota: temporada 2025 no DB = Brasileirão 2024
TABELA_2024 = {
    263: 1,    # Botafogo - Campeão
    275: 2,    # Palmeiras
    262: 3,    # Flamengo
    356: 4,    # Fortaleza
    285: 5,    # Internacional
    276: 6,    # São Paulo
    264: 7,    # Corinthians
    265: 8,    # Bahia
    283: 9,    # Cruzeiro
    267: 10,   # Vasco
    282: 11,   # Atlético-MG
    284: 12,   # Grêmio
    280: 13,   # Red Bull Bragantino
    354: 14,   # Ceará (subiu como campeão Série B)
    287: 15,   # Vitória
    266: 16,   # Fluminense
    286: 17,   # Juventude
    292: 18,   # Sport (subiu)
    277: 19,   # Santos (subiu como campeão Série B 2024)
    2305: 20,  # Mirassol (subiu)
    # Clubes da temporada 2026 que não estavam em 2025
    293: 15,   # Athletico-PR (default meio de tabela)
    294: 15,   # Coritiba (default)
    315: 18,   # Chapecoense (default rebaixamento)
    364: 18,   # Retrô (default rebaixamento)
}

# ==================== MULTIPLICADORES DE CONTEXTO ====================
MULT_CONFIG = {
    # Forma recente (últimas 3 rodadas do clube)
    'forma_3_vitorias': 1.15,     # 3 vitórias seguidas
    'forma_2_vitorias': 1.05,     # 2 vitórias
    'forma_1_vitoria': 1.00,      # 1 vitória
    'forma_0_vitorias': 0.90,     # 0 vitórias (má fase)

    # Qualidade do adversário (baseado em posição na tabela)
    'adversario_top4': 0.85,      # Top 4 (adversário forte)
    'adversario_5_8': 0.95,       # 5º-8º
    'adversario_9_16': 1.00,      # Meio de tabela
    'adversario_bottom4': 1.25,   # Bottom 4 (zona de rebaixamento)

    # Mando de campo
    'mando_casa': 1.10,
    'mando_fora': 0.95,
    'mando_neutro': 1.00,

    # Limites do multiplicador final (evitar extremos)
    'clamp_min': 0.70,
    'clamp_max': 1.50,

    # Pesos para blend de posição (híbrido atual + anterior)
    'peso_atual_inicio': 0.3,     # peso da tabela atual quando rodada < 10
    'peso_anterior_inicio': 0.7,
    'peso_atual_meio': 0.6,       # peso quando rodada >= 10
    'peso_anterior_meio': 0.4,
}

# ==================== MAPEAMENTO TEMPORADA DB -> BRASILEIRÃO ====================
# No banco: temporada 2026 = Brasileirão 2025 (temporada atual)
# No banco: temporada 2025 = Brasileirão 2024
TEMPORADA_ATUAL_DB = 2026
TEMPORADA_ANTERIOR_DB = 2025
