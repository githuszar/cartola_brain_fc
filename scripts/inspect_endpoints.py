#!/usr/bin/env python3
from cartola_service import CartolaService
import json

s = CartolaService()

print('POSICOES sample:')
pos = s.fetch_posicoes(use_cache=False)
print(type(pos))
try:
    # if dict
    if isinstance(pos, dict):
        for k, v in list(pos.items())[:6]:
            print(k, '=>', v)
    else:
        print(pos[:6])
except Exception as e:
    print('pos error', e)

print('\nRODADAS sample:')
rod = s.fetch_rodadas(use_cache=False)
print(type(rod))
try:
    print(json.dumps(rod)[:1000])
except Exception as e:
    print('rod error', e)

print('\nPOS_RODA sample:')
d = s.fetch_pos_rodada_destaques(1, use_cache=False)
print(type(d))
try:
    print(json.dumps(d)[:1000])
except Exception as e:
    print('pos_rod error', e)

print('\nRANKINGS sample:')
rank = s.fetch_rankings(use_cache=False)
print(type(rank))
try:
    print(json.dumps(list(rank.keys())[:20]))
except Exception as e:
    print('rank error', e)

print('\nMERCADO_DESTAQUES sample:')
md = s.fetch_mercado_destaques(use_cache=False)
print(type(md))
try:
    print(json.dumps(list(md.keys())[:200])[:1000])
except Exception as e:
    print('md error', e)
