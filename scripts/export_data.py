#!/usr/bin/env python3
"""Exporta tabelas relevantes para CSV: rodadas, posicoes, rankings"""
from pathlib import Path
import csv
import sqlite3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from database import DB_PATH

OUT = Path('exports')
OUT.mkdir(exist_ok=True)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

tables = {
    'rodadas': 'SELECT rodada, inicio, fim, status, temporada, atualizado_em FROM rodadas ORDER BY rodada',
    'posicoes': 'SELECT posicao_id, nome FROM posicoes ORDER BY posicao_id',
    'rankings': 'SELECT nome, jogador_id, pos, valor, rodada, temporada, atualizado_em FROM rankings ORDER BY nome, pos'
}

for name, query in tables.items():
    out = OUT / f"{name}.csv"
    print(f"Exportando {name} -> {out}")
    c.execute(query)
    rows = c.fetchall()
    if not rows:
        print(f"  (vazio)")
        continue
    with out.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(rows[0].keys())
        for r in rows:
            writer.writerow([r[k] for k in r.keys()])

conn.close()
print('Export concluido. Arquivos em:', OUT.resolve())
