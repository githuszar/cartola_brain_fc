"""
FantasyBrain V1.0 - Serviço de Dados do Cartola FC

Integração com a API oficial do Cartola FC e persistência em SQLite.
"""

import requests
import json
from datetime import datetime
from database import get_connection, migrate_database, DB_PATH
from cache import set_cache, get_cache

BASE_URL = "https://api.cartola.globo.com"


class CartolaService:
    """
    Serviço para interagir com a API do Cartola FC e sincronizar dados com SQLite local.
    """

    def __init__(self):
        self.temporada_atual = datetime.now().year
        # Garantir que o banco está atualizado
        migrate_database()

    # ==================== MÉTODOS DE FETCH (API) ====================

    def fetch_mercado_status(self, use_cache=True):
        """Obtém o status do mercado atual do Cartola FC"""
        cache_key = "mercado_status"
        if use_cache:
            cached_data = get_cache(cache_key)
            if cached_data:
                return cached_data

        try:
            url = f"{BASE_URL}/mercado/status"
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                data = response.json()
                set_cache(cache_key, data, expiration=60*15)  # 15 minutos
                return data
        except Exception as e:
            print(f"[API] Erro ao buscar status do mercado: {e}")
        return None

    def fetch_clubes(self, use_cache=True):
        """Obtém dados de todos os clubes do Cartola FC"""
        cache_key = "clubes"
        if use_cache:
            cached_data = get_cache(cache_key)
            if cached_data:
                return cached_data

        try:
            url = f"{BASE_URL}/clubes"
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                data = response.json()
                set_cache(cache_key, data, expiration=60*60*24)  # 24 horas
                return data
        except Exception as e:
            print(f"[API] Erro ao buscar clubes: {e}")
        return None

    def fetch_partidas(self, rodada=None, use_cache=True):
        """Obtém dados das partidas de uma rodada específica"""
        cache_key = f"partidas_rodada_{rodada}" if rodada else "partidas_atual"
        if use_cache:
            cached_data = get_cache(cache_key)
            if cached_data:
                return cached_data

        try:
            url = f"{BASE_URL}/partidas"
            if rodada:
                url += f"/{rodada}"

            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                data = response.json()
                set_cache(cache_key, data, expiration=60*60*6)  # 6 horas
                return data
        except Exception as e:
            print(f"[API] Erro ao buscar partidas: {e}")
        return None

    def fetch_atletas_pontuados(self, rodada=None, use_cache=True):
        """Obtém pontuações dos atletas de uma rodada específica"""
        cache_key = f"atletas_pontuados_rodada_{rodada}" if rodada else "atletas_pontuados_atual"
        if use_cache:
            cached_data = get_cache(cache_key)
            if cached_data:
                return cached_data

        try:
            url = f"{BASE_URL}/atletas/pontuados"
            if rodada:
                url += f"/{rodada}"

            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                data = response.json()
                set_cache(cache_key, data, expiration=60*60*3)  # 3 horas
                return data
        except Exception as e:
            print(f"[API] Erro ao buscar pontuações: {e}")
        return None

    def fetch_atletas_mercado(self, use_cache=True):
        """Obtém dados dos atletas no mercado"""
        cache_key = "atletas_mercado"
        if use_cache:
            cached_data = get_cache(cache_key)
            if cached_data:
                return cached_data

        try:
            url = f"{BASE_URL}/atletas/mercado"
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                data = response.json()
                set_cache(cache_key, data, expiration=60*60*6)  # 6 horas
                return data
        except Exception as e:
            print(f"[API] Erro ao buscar atletas do mercado: {e}")
        return None

    # ==================== NOVOS ENDPOINTS (INTEGRAÇÃO) ====================

    def fetch_posicoes(self, use_cache=True):
        """Obtém mapa de posições do cartola"""
        cache_key = "posicoes"
        if use_cache:
            cached = get_cache(cache_key)
            if cached:
                return cached

        try:
            url = f"{BASE_URL}/posicoes"
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                set_cache(cache_key, data, expiration=60*60*24)
                return data
        except Exception as e:
            print(f"[API] Erro ao buscar posicoes: {e}")
        return None

    def fetch_rodadas(self, use_cache=True):
        """Obtém metadados das rodadas"""
        cache_key = "rodadas"
        if use_cache:
            cached = get_cache(cache_key)
            if cached:
                return cached

        try:
            url = f"{BASE_URL}/rodadas"
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                set_cache(cache_key, data, expiration=60*60*24)
                return data
        except Exception as e:
            print(f"[API] Erro ao buscar rodadas: {e}")
        return None

    def fetch_pos_rodada_destaques(self, rodada, use_cache=True):
        """Obtém destaques da pos-rodada para uma rodada específica"""
        cache_key = f"pos_rodada_destaques_{rodada}"
        if use_cache:
            cached = get_cache(cache_key)
            if cached:
                return cached

        try:
            url = f"{BASE_URL}/pos-rodada/destaques"
            if rodada:
                url += f"/{rodada}"
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                set_cache(cache_key, data, expiration=60*60*3)
                return data
        except Exception as e:
            print(f"[API] Erro ao buscar destaques da pos-rodada: {e}")
        return None

    def fetch_rankings(self, use_cache=True):
        """Obtém rankings (diversos)"""
        cache_key = "rankings"
        if use_cache:
            cached = get_cache(cache_key)
            if cached:
                return cached

        try:
            url = f"{BASE_URL}/rankings"
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                set_cache(cache_key, data, expiration=60*60*6)
                return data
        except Exception as e:
            print(f"[API] Erro ao buscar rankings: {e}")
        return None

    def fetch_mercado_destaques(self, use_cache=True):
        """Obtém destaques do mercado"""
        cache_key = "mercado_destaques"
        if use_cache:
            cached = get_cache(cache_key)
            if cached:
                return cached

        try:
            url = f"{BASE_URL}/mercado/destaques"
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                set_cache(cache_key, data, expiration=60*60*6)
                return data
        except Exception as e:
            print(f"[API] Erro ao buscar mercado destaques: {e}")
        return None

    # ==================== MÉTODOS DE PERSISTÊNCIA (SQLite) ====================

    def salvar_clubes(self, clubes_data):
        """Salva dados dos clubes no SQLite"""
        if not clubes_data:
            return 0

        conn = get_connection()
        cursor = conn.cursor()
        count = 0

        for clube_id, clube in clubes_data.items():
            try:
                clube_data = (
                    int(clube_id),
                    clube.get('nome', ''),
                    clube.get('abreviacao', ''),
                    clube.get('escudos', {}).get('60x60', ''),
                    clube.get('nome_fantasia', ''),
                    datetime.now().isoformat()
                )

                cursor.execute("""
                    INSERT OR REPLACE INTO clubes
                    (clube_id, nome, abreviacao, escudo_url, nome_fantasia, atualizado_em)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, clube_data)
                count += 1

            except Exception as e:
                print(f"[DB] Erro ao salvar clube {clube_id}: {e}")

        conn.commit()
        conn.close()
        return count

    def salvar_partidas(self, partidas_data, rodada):
        """Salva dados das partidas no SQLite e atualiza calendário"""
        if not partidas_data or not partidas_data.get('partidas'):
            return 0

        conn = get_connection()
        cursor = conn.cursor()
        count = 0

        for partida in partidas_data['partidas']:
            try:
                partida_id = partida.get('partida_id')
                if not partida_id:
                    continue

                timestamp = partida.get('timestamp')
                data_hora = datetime.fromtimestamp(timestamp).isoformat() if timestamp else None
                clube_casa_id = partida.get('clube_casa_id')
                clube_visitante_id = partida.get('clube_visitante_id')

                partida_data = (
                    partida_id,
                    rodada,
                    clube_casa_id,
                    clube_visitante_id,
                    partida.get('placar_oficial_mandante'),
                    partida.get('placar_oficial_visitante'),
                    data_hora,
                    partida.get('local'),
                    1 if partida.get('valida', True) else 0,
                    self._determinar_partida_encerrada(partida),
                    self.temporada_atual,
                    datetime.now().isoformat()
                )

                cursor.execute("""
                    INSERT OR REPLACE INTO partidas
                    (partida_id, rodada, clube_casa_id, clube_visitante_id, placar_casa,
                     placar_visitante, data_hora, local, valida, encerrada, temporada, atualizado_em)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, partida_data)

                # Salvar calendário para time da casa
                if clube_casa_id and clube_visitante_id:
                    cursor.execute("""
                        INSERT OR REPLACE INTO calendario
                        (rodada, clube_id, adversario_id, mando, data_hora, temporada, atualizado_em)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (rodada, clube_casa_id, clube_visitante_id, 'casa', data_hora,
                          self.temporada_atual, datetime.now().isoformat()))

                    # Salvar calendário para time visitante
                    cursor.execute("""
                        INSERT OR REPLACE INTO calendario
                        (rodada, clube_id, adversario_id, mando, data_hora, temporada, atualizado_em)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (rodada, clube_visitante_id, clube_casa_id, 'fora', data_hora,
                          self.temporada_atual, datetime.now().isoformat()))

                count += 1

            except Exception as e:
                print(f"[DB] Erro ao salvar partida {partida.get('partida_id')}: {e}")

        conn.commit()
        conn.close()
        return count

    def _determinar_partida_encerrada(self, partida):
        """Determina se uma partida esta encerrada.

        Prioridade:
        1. status_transmissao_tr == 'ENCERRADA'
        2. Fallback: ambos placares existem
        """
        if partida.get('status_transmissao_tr') == 'ENCERRADA':
            return 1
        # Fallback: se ambos placares existem, considerar encerrada
        placar_casa = partida.get('placar_oficial_mandante')
        placar_visitante = partida.get('placar_oficial_visitante')
        if placar_casa is not None and placar_visitante is not None:
            return 1
        return 0

    def _get_adversario_e_mando(self, cursor, clube_id, rodada):
        """Busca adversário e mando de um clube em uma rodada"""
        cursor.execute("""
            SELECT adversario_id, mando FROM calendario
            WHERE clube_id = ? AND rodada = ? AND temporada = ?
        """, (clube_id, rodada, self.temporada_atual))
        result = cursor.fetchone()
        if result:
            return result[0], result[1]
        return None, None

    def salvar_pontuacoes_jogadores(self, atletas_data, rodada):
        """Salva pontuações dos jogadores no SQLite (com adversário)"""
        if not atletas_data or not atletas_data.get('atletas'):
            return 0

        conn = get_connection()
        cursor = conn.cursor()
        count = 0

        for atleta_id, atleta in atletas_data['atletas'].items():
            try:
                clube_id = atleta.get('clube_id')
                adversario_id, mando = self._get_adversario_e_mando(cursor, clube_id, rodada)

                pontuacao_data = (
                    int(atleta_id),
                    rodada,
                    atleta.get('pontuacao', 0),
                    atleta.get('preco_num', 0),
                    atleta.get('variacao_num', 0),
                    clube_id,
                    adversario_id,
                    mando,
                    1 if atleta.get('posicao_id', 0) > 0 else 0,
                    1 if atleta.get('entrou_em_campo', False) else 0,
                    self.temporada_atual,
                    datetime.now().isoformat()
                )

                cursor.execute("""
                    INSERT OR REPLACE INTO pontuacoes_jogadores
                    (jogador_id, rodada, pontuacao, preco, preco_variacao, clube_id,
                     adversario_id, mando, foi_titular, entrou_em_campo, temporada, atualizado_em)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, pontuacao_data)

                # Salvar scouts
                self._salvar_scouts_jogador(cursor, atleta_id, rodada, atleta.get('scout', {}))
                count += 1

            except Exception as e:
                print(f"[DB] Erro ao salvar pontuação do jogador {atleta_id}: {e}")

        conn.commit()
        conn.close()
        return count

    def _salvar_scouts_jogador(self, cursor, jogador_id, rodada, scout):
        """Salva scouts detalhados do jogador no SQLite"""
        try:
            scout_data = (
                int(jogador_id),
                rodada,
                scout.get('G', 0),
                scout.get('A', 0),
                scout.get('FT', 0),
                scout.get('FF', 0),
                scout.get('FD', 0),
                scout.get('FS', 0),
                scout.get('PS', 0),
                scout.get('DS', 0),
                scout.get('FC', 0),
                scout.get('FS', 0),
                scout.get('CA', 0),
                scout.get('CV', 0),
                scout.get('I', 0),
                scout.get('PP', 0),
                scout.get('DP', 0),
                scout.get('DE', 0),
                scout.get('GS', 0),
                scout.get('SG', 0),
                self.temporada_atual,
                datetime.now().isoformat()
            )

            cursor.execute("""
                INSERT OR REPLACE INTO scouts_jogadores
                (jogador_id, rodada, gols, assistencias, finalizacoes, finalizacoes_fora,
                 finalizacoes_defesa, finalizacoes_trave, passes, desarmes, faltas_cometidas,
                 faltas_sofridas, cartoes_amarelos, cartoes_vermelhos, impedimentos,
                 penaltis_perdidos, penaltis_defendidos, defesas, gols_sofridos,
                 jogos_sem_sofrer_gols, temporada, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, scout_data)

        except Exception as e:
            print(f"[DB] Erro ao salvar scout do jogador {jogador_id}: {e}")

    def _salvar_historico_jogador(self, cursor, jogador_id, jogador_data, rodada):
        """Salva histórico de um jogador no SQLite"""
        try:
            historico_data = (
                int(jogador_id),
                rodada,
                self.temporada_atual,
                jogador_data.get('clube_id'),
                jogador_data.get('preco_num'),
                jogador_data.get('variacao_num'),
                jogador_data.get('media_num'),
                jogador_data.get('jogos_num'),
                jogador_data.get('status_id'),
                jogador_data.get('posicao_id'),
                jogador_data.get('nome'),
                jogador_data.get('apelido'),
                jogador_data.get('foto'),
                datetime.now().isoformat()
            )

            cursor.execute("""
                INSERT INTO historico_jogadores
                (jogador_id, rodada, temporada, clube_id, preco, variacao_preco, media_pontos,
                 jogos_num, status_id, posicao_id, nome, apelido, foto_url, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, historico_data)

        except Exception as e:
            print(f"[DB] Erro ao salvar histórico do jogador {jogador_id}: {e}")

    def salvar_historico_mercado(self, mercado_data):
        """Salva histórico do status do mercado no SQLite"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            fechamento = mercado_data.get('fechamento')
            fechamento_str = json.dumps(fechamento) if fechamento else None

            historico_data = (
                mercado_data.get('rodada_atual'),
                self.temporada_atual,
                mercado_data.get('status_mercado'),
                1 if mercado_data.get('game_over') else 0,
                mercado_data.get('times_escalados'),
                fechamento_str,
                1 if mercado_data.get('mercado_pos_rodada') else 0,
                1 if mercado_data.get('reativar') else 0,
                datetime.now().isoformat()
            )

            cursor.execute("""
                INSERT INTO historico_mercado_status
                (rodada, temporada, status_mercado, game_over, times_escalados,
                 fechamento, mercado_pos_rodada, reativar, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, historico_data)

            conn.commit()

        except Exception as e:
            print(f"[DB] Erro ao salvar histórico do mercado: {e}")
        finally:
            conn.close()

    # ==================== SALVAMENTO - NOVAS ENTIDADES ====================

    def salvar_posicoes(self, posicoes_data):
        """Salva o mapa de posições no SQLite"""
        if not posicoes_data:
            return 0

        conn = get_connection()
        cursor = conn.cursor()
        count = 0

        # posicoes_data expected: dict of id -> info, or list
        if isinstance(posicoes_data, dict):
            items = list(posicoes_data.items())
        elif isinstance(posicoes_data, list):
            items = [(p.get('id'), p) for p in posicoes_data]
        else:
            items = []

        for key, val in items:
            try:
                pid = int(key)
                if isinstance(val, dict):
                    nome = val.get('nome') or val.get('name') or val.get('abreviacao') or str(val)
                else:
                    nome = str(val)
                cursor.execute("""
                    INSERT OR REPLACE INTO posicoes (posicao_id, nome)
                    VALUES (?, ?)
                """, (pid, nome))
                count += 1
            except Exception as e:
                print(f"[DB] Erro ao salvar posicao {key}: {e}")

        conn.commit()
        conn.close()
        return count

    def salvar_rodadas(self, rodadas_data):
        """Salva metadados das rodadas no SQLite"""
        if not rodadas_data:
            return 0
        conn = get_connection()
        cursor = conn.cursor()
        count = 0

        # rodadas_data expected: list of rodadas
        for r in rodadas_data:
            try:
                # API uses 'rodada_id' in some payloads
                rodada = r.get('rodada') or r.get('id') or r.get('rodada_id')
                inicio = r.get('inicio') or r.get('data_inicio') or r.get('inicio')
                fim = r.get('fim') or r.get('data_fim') or r.get('fim')
                status = r.get('status') or r.get('status_rodada') or None
                temporada = self.temporada_atual

                if rodada is None:
                    raise ValueError('rodada id not found')

                cursor.execute("""
                    INSERT OR REPLACE INTO rodadas (rodada, inicio, fim, status, temporada, atualizado_em)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (rodada, inicio, fim, status, temporada, datetime.now().isoformat()))
                count += 1
            except Exception as e:
                print(f"[DB] Erro ao salvar rodada {r}: {e}")

        conn.commit()
        conn.close()
        return count

    def salvar_pos_rodada_destaques(self, destaques_data, rodada):
        """Salva destaques da pos-rodada no SQLite de forma robusta.

        Faz parsing recursivo do payload tentando extrair objetos que representem
        jogadores/destaques (ids e pontuações) mesmo em estruturas aninhadas.
        """
        if not destaques_data:
            return 0

        conn = get_connection()
        cursor = conn.cursor()
        count = 0

        def extract_entries(obj, tipo_hint=None):
            """Extrai entradas relevantes recursivamente de dicts/arrays."""
            results = []
            if isinstance(obj, dict):
                # Caso: dict que representa diretamente um destaque (contém atleta/jogador/id)
                if any(k in obj for k in ('atleta_id', 'jogador_id', 'id', 'atleta')):
                    # normalizar objeto atleta
                    candidate = obj.get('atleta') if obj.get('atleta') and isinstance(obj.get('atleta'), dict) else obj
                    jid = candidate.get('atleta_id') or candidate.get('jogador_id') or candidate.get('id')
                    pont = obj.get('pontuacao') or obj.get('pontos') or candidate.get('pontuacao') or candidate.get('pontos')
                    results.append({'jogador_id': jid, 'pontuacao': pont, 'raw': obj, 'tipo': tipo_hint})
                    return results

                # Caso: dict com sublistas/objetos (ex.: 'mito_rodada': { '123': {...}, ... })
                for k, v in obj.items():
                    if isinstance(v, (dict, list)):
                        results.extend(extract_entries(v, tipo_hint=k))
                return results

            if isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        results.extend(extract_entries(item, tipo_hint=tipo_hint))
                return results

            # outros tipos (str, float, etc) são ignorados
            return results

        entries = extract_entries(destaques_data)

        for item in entries:
            try:
                jid = item.get('jogador_id') or (item.get('raw') and next((v.get('atleta_id') or v.get('id') or v.get('jogador_id') for v in item.get('raw').values() if isinstance(v, dict)), None))
                if not jid:
                    # sem id válido, pular
                    continue

                tipo = item.get('tipo') or None
                pont = item.get('pontuacao')

                cursor.execute("""
                    INSERT INTO pos_rodada_destaques (rodada, jogador_id, tipo, pontuacao, meta, temporada, atualizado_em)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (rodada, int(jid), tipo, pont, json.dumps(item.get('raw')), self.temporada_atual, datetime.now().isoformat()))
                count += 1
            except Exception as e:
                print(f"[DB] Erro ao salvar destaque {item}: {e}")

        conn.commit()
        conn.close()
        return count

    def salvar_mercado_destaques(self, destaque_data, rodada=None):
        """Salva dados de destaques do mercado"""
        if not destaque_data:
            return 0
        conn = get_connection()
        cursor = conn.cursor()
        count = 0

        entries = destaque_data.get('destaques') if isinstance(destaque_data, dict) else destaque_data
        if isinstance(entries, dict):
            # convert to list
            entries = list(entries.values())

        for item in entries:
            try:
                jid = item.get('atleta_id') or item.get('jogador_id') or item.get('id')
                tipo = item.get('tipo') or item.get('categoria') or None
                valor = item.get('valor') or item.get('porcentagem') or None
                cursor.execute("""
                    INSERT INTO mercado_destaques (rodada, jogador_id, tipo, valor, temporada, atualizado_em)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (rodada, jid, tipo, valor, self.temporada_atual, datetime.now().isoformat()))
                count += 1
            except Exception as e:
                print(f"[DB] Erro ao salvar destaque de mercado {item}: {e}")

        conn.commit()
        conn.close()
        return count

    def salvar_rankings(self, rankings_data, nome=None):
        """Salva rankings no banco"""
        if not rankings_data:
            return 0
        conn = get_connection()
        cursor = conn.cursor()
        count = 0

        entries = rankings_data.get('rankings') if isinstance(rankings_data, dict) else rankings_data
        if not entries and isinstance(rankings_data, list):
            entries = rankings_data

        for idx, item in enumerate(entries, start=1):
            try:
                jid = item.get('atleta_id') or item.get('jogador_id') or item.get('id')
                valor = item.get('valor') or item.get('pontos') or None
                cursor.execute("""
                    INSERT INTO rankings (nome, jogador_id, pos, valor, rodada, temporada, atualizado_em)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (nome, jid, idx, valor, item.get('rodada'), self.temporada_atual, datetime.now().isoformat()))
                count += 1
            except Exception as e:
                print(f"[DB] Erro ao salvar ranking {item}: {e}")

        conn.commit()
        conn.close()
        return count

    def salvar_jogadores(self, atletas_data):
        """Salva dados dos jogadores no SQLite"""
        if not atletas_data or not atletas_data.get('atletas'):
            return 0

        conn = get_connection()
        cursor = conn.cursor()
        count = 0

        mercado_status = self.fetch_mercado_status(use_cache=True)
        rodada_atual = mercado_status.get('rodada_atual') if mercado_status else None

        clubes = self.fetch_clubes(use_cache=True)
        clubes_map = {}
        if clubes:
            for clube_id, clube in clubes.items():
                clubes_map[clube_id] = clube.get('nome', '')

        for atleta in atletas_data['atletas']:
            try:
                atleta_id = atleta.get('atleta_id')
                if not atleta_id:
                    continue

                # Salvar histórico do jogador
                self._salvar_historico_jogador(cursor, atleta_id, atleta, rodada_atual)

                clube_id = atleta.get('clube_id')
                clube_nome = ''
                if clube_id and str(clube_id) in clubes_map:
                    clube_nome = clubes_map[str(clube_id)]

                jogador_data = (
                    atleta_id,
                    atleta.get('nome'),
                    atleta.get('apelido'),
                    atleta.get('foto'),
                    clube_id,
                    clube_nome,
                    atleta.get('posicao_id'),
                    atleta.get('status_id'),
                    atleta.get('preco_num'),
                    atleta.get('media_num'),
                    atleta.get('jogos_num'),
                    datetime.now().isoformat()
                )

                cursor.execute("""
                    INSERT OR REPLACE INTO jogadores
                    (jogador_id, nome, apelido, foto_url, clube_id, clube, posicao_id,
                     status_id, preco, media_pontos, jogos_num, atualizado_em)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, jogador_data)
                count += 1

            except Exception as e:
                print(f"[DB] Erro ao salvar jogador {atleta.get('atleta_id')}: {e}")

        conn.commit()
        conn.close()
        return count

    # ==================== SINCRONIZAÇÃO PRINCIPAL ====================

    def sincronizar(self, rodada=None, force=False, extras=False):
        """
        Sincroniza todos os dados da API do Cartola com o SQLite.

        Args:
            rodada: Rodada específica (None = rodada atual)
            force: Ignorar cache e buscar dados frescos
            extras: Buscar endpoints extras (posicoes, rodadas, destaques, rankings, mercado destaques)

        Returns:
            dict com estatísticas da sincronização
        """
        stats = {
            "sucesso": False,
            "rodada": None,
            "clubes": 0,
            "partidas": 0,
            "jogadores": 0,
            "pontuacoes": 0,
            "extras": {},
            "erros": []
        }

        print("=" * 60)
        print("FANTASYBRAIN V1.0 - SINCRONIZAÇÃO")
        print(f"Banco de dados: {DB_PATH}")
        print("=" * 60)

        # Obter status do mercado
        mercado_status = self.fetch_mercado_status(use_cache=not force)
        if not mercado_status:
            stats["erros"].append("Erro ao obter status do mercado")
            print("❌ Erro ao obter status do mercado. Abortando.")
            return stats

        # Salvar histórico do status do mercado
        self.salvar_historico_mercado(mercado_status)

        rodada_atual = rodada or mercado_status.get('rodada_atual')
        status_mercado = mercado_status.get('status_mercado')
        stats["rodada"] = rodada_atual

        status_texto = {1: "Aberto", 2: "Fechado/Em jogo", 3: "Fim de rodada"}
        print(f"\n✓ Rodada: {rodada_atual}")
        print(f"✓ Status: {status_texto.get(status_mercado, 'Desconhecido')}")

        # Sincronizar clubes
        print("\n📋 Sincronizando clubes...")
        clubes = self.fetch_clubes(use_cache=not force)
        if clubes:
            stats["clubes"] = self.salvar_clubes(clubes)
            print(f"   ✓ {stats['clubes']} clubes salvos")
        else:
            stats["erros"].append("Erro ao obter clubes")
            print("   ❌ Erro ao obter clubes")

        # Sincronizar partidas da rodada
        print(f"\n⚽ Sincronizando partidas da rodada {rodada_atual}...")
        partidas = self.fetch_partidas(rodada_atual, use_cache=not force)
        if partidas:
            stats["partidas"] = self.salvar_partidas(partidas, rodada_atual)
            print(f"   ✓ {stats['partidas']} partidas salvas")
        else:
            stats["erros"].append(f"Erro ao obter partidas da rodada {rodada_atual}")
            print(f"   ❌ Erro ao obter partidas")

        # Sincronizar jogadores do mercado
        print("\n👥 Sincronizando jogadores...")
        atletas_mercado = self.fetch_atletas_mercado(use_cache=not force)
        if atletas_mercado:
            stats["jogadores"] = self.salvar_jogadores(atletas_mercado)
            print(f"   ✓ {stats['jogadores']} jogadores salvos")
        else:
            stats["erros"].append("Erro ao obter jogadores do mercado")
            print("   ❌ Erro ao obter jogadores")

        # Sincronizar pontuações (se rodada em andamento ou finalizada)
        if status_mercado in [2, 3] or force:
            print(f"\n📊 Sincronizando pontuações da rodada {rodada_atual}...")
            atletas_pontuados = self.fetch_atletas_pontuados(rodada_atual, use_cache=not force)
            if atletas_pontuados and atletas_pontuados.get('atletas'):
                stats["pontuacoes"] = self.salvar_pontuacoes_jogadores(atletas_pontuados, rodada_atual)
                print(f"   ✓ {stats['pontuacoes']} pontuações salvas")
            else:
                print(f"   ⚠ Nenhuma pontuação disponível ainda")
        else:
            print(f"\n📊 Pontuações: Aguardando início dos jogos (use --force para forçar)")

        # Extras: posicoes, rodadas, destaques, rankings, mercado destaques
        if extras:
            print("\n✨ Sincronizando endpoints extras...")

            try:
                pos = self.fetch_posicoes(use_cache=not force)
                stats['extras']['posicoes'] = self.salvar_posicoes(pos) if pos else 0
                print(f"   ✓ posicoes: {stats['extras']['posicoes']} salvas")
            except Exception as e:
                print(f"   ❌ Erro posicoes: {e}")

            try:
                rodadas = self.fetch_rodadas(use_cache=not force)
                stats['extras']['rodadas'] = self.salvar_rodadas(rodadas) if rodadas else 0
                print(f"   ✓ rodadas: {stats['extras']['rodadas']} salvas")
            except Exception as e:
                print(f"   ❌ Erro rodadas: {e}")

            try:
                destaques = self.fetch_pos_rodada_destaques(rodada_atual, use_cache=not force)
                stats['extras']['pos_rodada_destaques'] = self.salvar_pos_rodada_destaques(destaques, rodada_atual) if destaques else 0
                print(f"   ✓ pos-rodada destaques: {stats['extras']['pos_rodada_destaques']} salvos")
            except Exception as e:
                print(f"   ❌ Erro destaques pos-rodada: {e}")

            try:
                ranks = self.fetch_rankings(use_cache=not force)
                stats['extras']['rankings'] = self.salvar_rankings(ranks, nome='rankings') if ranks else 0
                print(f"   ✓ rankings: {stats['extras']['rankings']} salvos")
            except Exception as e:
                print(f"   ❌ Erro rankings: {e}")

            try:
                md = self.fetch_mercado_destaques(use_cache=not force)
                stats['extras']['mercado_destaques'] = self.salvar_mercado_destaques(md, rodada_atual) if md else 0
                print(f"   ✓ mercado destaques: {stats['extras']['mercado_destaques']} salvos")
            except Exception as e:
                print(f"   ❌ Erro mercado destaques: {e}")

        stats["sucesso"] = len(stats["erros"]) == 0

        print("\n" + "=" * 60)
        if stats["sucesso"]:
            print("✅ SINCRONIZAÇÃO CONCLUÍDA COM SUCESSO")
        else:
            print("⚠️ SINCRONIZAÇÃO CONCLUÍDA COM ERROS")
            for erro in stats["erros"]:
                print(f"   - {erro}")
        print("=" * 60)

        return stats


# Função de conveniência para uso direto
def sincronizar(rodada=None, force=False, extras=False):
    """Sincroniza dados do Cartola FC"""
    service = CartolaService()
    return service.sincronizar(rodada, force, extras)


if __name__ == "__main__":
    import sys
    rodada = None
    force = False

    for arg in sys.argv[1:]:
        if arg == "--force":
            force = True
        else:
            try:
                rodada = int(arg)
            except ValueError:
                pass

    sincronizar(rodada, force)
