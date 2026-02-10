#!/usr/bin/env python3
from cartola_service import CartolaService
import json
s = CartolaService()
d = s.fetch_pos_rodada_destaques(1, use_cache=False)
print('TOP KEYS:', list(d.keys())[:20])
if 'mito_rodada' in d:
    m = d['mito_rodada']
    print('mito type', type(m))
    # print first 5 entries
    for k,v in list(m.items())[:5]:
        print('->', k, type(v))
        try:
            print('   sample:', json.dumps(v)[:200])
        except Exception as e:
            print('   sample err', e)

if 'destaques' in d:
    print('destaques type', type(d['destaques']))
    try:
        for i,v in enumerate(d['destaques'][:5]):
            print(i, type(v), v)
    except Exception as e:
        print('err listing destaques', e)
