#!/usr/bin/env python3
"""Dump and inspect pos-rodada/destaques structure for a given rodada."""
from pathlib import Path
import json
import sys
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cartola_service import CartolaService

OUT = Path('pos_rodada_1.json')

s = CartolaService()
rodada = 1
print(f"Fetching pos-rodada/destaques for rodada {rodada}...")
d = s.fetch_pos_rodada_destaques(rodada, use_cache=False)
if not d:
    print("No data returned")
    sys.exit(0)

print(f"Saving raw json to {OUT}")
with OUT.open('w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=2)

print('\nTop-level keys:')
for k in list(d.keys()):
    v = d[k]
    t = type(v).__name__
    try:
        l = len(v) if hasattr(v, '__len__') else 'n/a'
    except Exception:
        l = 'n/a'
    print(f" - {k} ({t}) len={l}")

# recursive scan looking for dicts that look like player highlights
matches = []

def scan(obj, path=None):
    if path is None:
        path = []
    if isinstance(obj, dict):
        keys = set(obj.keys())
        if keys & {'atleta_id', 'jogador_id', 'id'} or keys & {'pontuacao', 'pontos'}:
            matches.append((path.copy(), obj))
        for k,v in obj.items():
            scan(v, path + [str(k)])
    elif isinstance(obj, list):
        for i,v in enumerate(obj):
            scan(v, path + [f'[{i}]'])

scan(d)
print(f"\nFound {len(matches)} candidate objects with atleta_id/id/pontuacao (showing up to 10):")
for i,(path,obj) in enumerate(matches[:10],1):
    print(f"\nMATCH {i} @ {'/'.join(path)}")
    print(json.dumps(obj, ensure_ascii=False, indent=2)[:1000])

print('\nSample values for key mito_rodada (first 5 keys):')
if 'mito_rodada' in d and isinstance(d['mito_rodada'], dict):
    for k in list(d['mito_rodada'].keys())[:5]:
        print(' -', k, '->', type(d['mito_rodada'][k]).__name__)
        print('   sample:', json.dumps(d['mito_rodada'][k], ensure_ascii=False)[:300])

print('\nDump finished')
