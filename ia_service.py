"""
FantasyBrain V1.0 - Serviço de Recomendação com IA

Gera recomendações de escalação usando modelos de IA.
Sistema híbrido: Contexto (forma, adversário, mando) + Value (ratio pts/preço) + ILP.
"""

import os
import json
import requests
import time
from dotenv import load_dotenv
from cache import get_cache, set_cache
from database import get_connection, POSICOES
from cartola_service import CartolaService  # para acessar novos endpoints (rankings, mercado)
from constants import TABELA_2024, MULT_CONFIG, TEMPORADA_ATUAL_DB, TEMPORADA_ANTERIOR_DB

# Carregar variáveis de ambiente
load_dotenv()


class CartolaRecommendation:
    """Classe para gerar recomendações de escalação para o Cartola FC usando IA"""

    def __init__(self):
        """Inicializa a classe de recomendação"""
        self.hf_token = os.getenv("HF_TOKEN", "")
        self.use_cache = os.getenv("USE_CACHE", "true").lower() == "true"
        # Serviço para acessar endpoints extras e dados adicionais
        self.service = CartolaService()

    def obter_status_mercado(self):
        """Obtém o status atual do mercado do Cartola FC"""
        if self.use_cache:
            cache_data = get_cache("mercado_status")
            if cache_data:
                return cache_data

        url = "https://api.cartola.globo.com/mercado/status"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()

        if self.use_cache:
            set_cache("mercado_status", data, 3600)

        return data

    def obter_atletas_api(self):
        """Obtém a lista de atletas da API do Cartola FC"""
        if self.use_cache:
            cache_data = get_cache("atletas_mercado")
            if cache_data:
                return cache_data

        url = "https://api.cartola.globo.com/atletas/mercado"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()

        if self.use_cache:
            set_cache("atletas_mercado", data, 3600)

        return data

    def obter_atletas_db(self, limit=50):
        """Obtém jogadores do banco de dados local ordenados por média"""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT jogador_id, nome, apelido, clube, clube_id, posicao_id,
                   preco, media_pontos, jogos_num, status_id
            FROM jogadores
            WHERE status_id = 7
            ORDER BY media_pontos DESC
            LIMIT ?
        """, (limit,))

        jogadores = []
        for row in cursor.fetchall():
            jogadores.append({
                "atleta_id": row[0],
                "nome": row[1],
                "apelido": row[2],
                "clube": row[3],
                "clube_id": row[4],
                "posicao_id": row[5],
                "preco_num": row[6],
                "media_num": row[7] or 0,
                "jogos_num": row[8] or 0,
                "status_id": row[9]
            })

        conn.close()
        return jogadores

    def obter_proximo_adversario(self, clube_id, rodada):
        """Obtém o próximo adversário de um clube"""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT c.adversario_id, c.mando, cl.abreviacao
            FROM calendario c
            JOIN clubes cl ON c.adversario_id = cl.clube_id
            WHERE c.clube_id = ? AND c.rodada = ?
        """, (clube_id, rodada))

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "adversario_id": result[0],
                "mando": result[1],
                "adversario": result[2]
            }
        return None

    # ==================== SISTEMA DE CONTEXTOS (NOVO) ====================

    def _get_adversario_e_mando(self, cursor, clube_id, rodada):
        """Busca adversário e mando de campo para a próxima rodada"""
        cursor.execute("""
            SELECT adversario_id, mando
            FROM calendario
            WHERE clube_id = ? AND rodada = ? AND temporada = ?
        """, (clube_id, rodada, TEMPORADA_ATUAL_DB))

        result = cursor.fetchone()
        if result:
            return result[0], result[1]
        return None, None

    def _calcular_forma_recente(self, cursor, clube_id, rodada):
        """Calcula multiplicador baseado nas últimas 3 rodadas do clube.

        Retorna multiplicador:
          3 vitórias -> 1.15
          2 vitórias -> 1.05
          1 vitória  -> 1.00
          0 vitórias -> 0.90
        """
        rodada_inicio = max(1, rodada - 3)

        cursor.execute("""
            SELECT
                clube_casa_id, clube_visitante_id, placar_casa, placar_visitante
            FROM partidas
            WHERE (clube_casa_id = ? OR clube_visitante_id = ?)
              AND rodada >= ? AND rodada < ?
              AND encerrada = 1
              AND temporada = ?
        """, (clube_id, clube_id, rodada_inicio, rodada, TEMPORADA_ATUAL_DB))

        vitorias = 0
        total_jogos = 0

        for row in cursor.fetchall():
            casa_id, visit_id, placar_c, placar_v = row[0], row[1], row[2], row[3]
            if placar_c is None or placar_v is None:
                continue
            total_jogos += 1
            if casa_id == clube_id and placar_c > placar_v:
                vitorias += 1
            elif visit_id == clube_id and placar_v > placar_c:
                vitorias += 1

        # Se não há jogos encerrados, retorna neutro
        if total_jogos == 0:
            return MULT_CONFIG['forma_1_vitoria']

        if vitorias >= 3:
            return MULT_CONFIG['forma_3_vitorias']
        elif vitorias == 2:
            return MULT_CONFIG['forma_2_vitorias']
        elif vitorias == 1:
            return MULT_CONFIG['forma_1_vitoria']
        else:
            return MULT_CONFIG['forma_0_vitorias']

    def _calcular_tabela_atual(self, cursor, rodada):
        """Calcula posição atual de cada clube na tabela baseado em partidas encerradas.

        Retorna dict: {clube_id: posicao}
        """
        cursor.execute("""
            SELECT clube_casa_id, clube_visitante_id, placar_casa, placar_visitante
            FROM partidas
            WHERE encerrada = 1 AND rodada <= ? AND temporada = ?
        """, (rodada, TEMPORADA_ATUAL_DB))

        pontos = {}
        for row in cursor.fetchall():
            casa_id, visit_id, pc, pv = row[0], row[1], row[2], row[3]
            if pc is None or pv is None:
                continue

            pontos.setdefault(casa_id, 0)
            pontos.setdefault(visit_id, 0)

            if pc > pv:
                pontos[casa_id] += 3
            elif pc == pv:
                pontos[casa_id] += 1
                pontos[visit_id] += 1
            else:
                pontos[visit_id] += 3

        # Rankear
        clubes_sorted = sorted(pontos.items(), key=lambda x: x[1], reverse=True)
        tabela = {}
        for pos, (cid, _pts) in enumerate(clubes_sorted, 1):
            tabela[cid] = pos

        return tabela

    def _calcular_qualidade_adversario(self, cursor, adversario_id, rodada):
        """Calcula multiplicador baseado na posição do adversário (híbrido atual + 2024).

        Adversário forte (top 4) -> 0.85 (diminui previsão)
        Adversário fraco (bottom 4) -> 1.25 (aumenta previsão)
        """
        if adversario_id is None:
            return 1.0

        # Posição na tabela atual
        tabela_atual = self._calcular_tabela_atual(cursor, rodada)
        posicao_atual = tabela_atual.get(adversario_id, 10)

        # Time promovido (sem histórico Série A) -> somente tabela atual
        tem_historico = adversario_id in TABELA_2024

        if not tem_historico:
            posicao_efetiva = posicao_atual
        else:
            posicao_anterior = TABELA_2024[adversario_id]

            # Blend híbrido baseado em quantas rodadas já passaram
            if rodada < 10:
                peso_atual = MULT_CONFIG['peso_atual_inicio']
                peso_anterior = MULT_CONFIG['peso_anterior_inicio']
            else:
                peso_atual = MULT_CONFIG['peso_atual_meio']
                peso_anterior = MULT_CONFIG['peso_anterior_meio']

            posicao_efetiva = posicao_atual * peso_atual + posicao_anterior * peso_anterior

        # Mapear para multiplicador
        if posicao_efetiva <= 4:
            return MULT_CONFIG['adversario_top4']
        elif posicao_efetiva <= 8:
            return MULT_CONFIG['adversario_5_8']
        elif posicao_efetiva >= 17:
            return MULT_CONFIG['adversario_bottom4']
        else:
            return MULT_CONFIG['adversario_9_16']

    def _calcular_mando(self, mando):
        """Retorna multiplicador de mando de campo.
        Casa: 1.10, Fora: 0.95, Neutro/desconhecido: 1.0
        """
        mapping = {
            'casa': MULT_CONFIG['mando_casa'],
            'fora': MULT_CONFIG['mando_fora'],
        }
        return mapping.get(mando, MULT_CONFIG['mando_neutro'])

    def _descrever_contexto(self, mult, tipo):
        """Gera descrição textual de um multiplicador de contexto"""
        if tipo == 'forma':
            if mult >= 1.15:
                return "Boa fase (3V)"
            elif mult >= 1.05:
                return "Fase ok (2V)"
            elif mult <= 0.90:
                return "Ma fase (0V)"
            return None
        elif tipo == 'adversario':
            if mult >= 1.25:
                return "vs Time fraco"
            elif mult >= 1.05:
                return "vs Historico fraco"
            elif mult <= 0.85:
                return "vs Top 4"
            elif mult <= 0.95:
                return "vs Forte"
            return None
        elif tipo == 'mando':
            if mult >= 1.10:
                return "Em casa"
            elif mult <= 0.95:
                return "Fora"
            return None
        return None

    def _enriquecer_com_contextos(self, jogadores, rodada):
        """Adiciona media_ajustada, contextos e ratio a cada jogador (in-place).

        Para cada jogador:
        1. Busca adversário e mando
        2. Calcula multiplicadores de forma, adversário e mando
        3. Agrega via soma normalizada (média dos desvios)
        4. Aplica à média base para gerar media_ajustada
        5. Calcula ratio (media_ajustada / preço)
        """
        conn = get_connection()
        cursor = conn.cursor()

        # Cache de forma recente por clube (evita recalcular)
        cache_forma = {}
        # Cache de adversário por clube
        cache_adversario = {}
        # Cache de abreviacao do clube
        cache_clube_abrev = {}

        for j in jogadores:
            clube_id = j.get('clube_id')
            media_base = j.get('media_num') or 0
            preco = j.get('preco_num') or j.get('preco') or 0

            # Resolver abreviacao do clube se nao existir
            if not j.get('clube') and clube_id:
                if clube_id not in cache_clube_abrev:
                    cursor.execute("SELECT abreviacao FROM clubes WHERE clube_id = ?", (clube_id,))
                    row = cursor.fetchone()
                    cache_clube_abrev[clube_id] = row[0] if row else '?'
                j['clube'] = cache_clube_abrev[clube_id]

            # Buscar adversário e mando
            if clube_id not in cache_adversario:
                adv_id, mando = self._get_adversario_e_mando(cursor, clube_id, rodada)
                cache_adversario[clube_id] = (adv_id, mando)
            else:
                adv_id, mando = cache_adversario[clube_id]

            # Calcular multiplicadores
            if clube_id not in cache_forma:
                cache_forma[clube_id] = self._calcular_forma_recente(cursor, clube_id, rodada)
            mult_forma = cache_forma[clube_id]

            mult_adversario = self._calcular_qualidade_adversario(cursor, adv_id, rodada)
            mult_mando = self._calcular_mando(mando)

            # Agregar: soma normalizada (média dos desvios de 1.0)
            desvios = [
                mult_forma - 1.0,
                mult_adversario - 1.0,
                mult_mando - 1.0
            ]
            desvio_medio = sum(desvios) / len(desvios)
            mult_final = 1.0 + desvio_medio

            # Clamp para evitar extremos
            mult_final = max(MULT_CONFIG['clamp_min'], min(MULT_CONFIG['clamp_max'], mult_final))

            # Aplicar
            media_ajustada = media_base * mult_final

            j['media_ajustada'] = round(media_ajustada, 2)
            j['multiplicador_final'] = round(mult_final, 4)
            j['contextos'] = {
                'forma': round(mult_forma, 2),
                'adversario': round(mult_adversario, 2),
                'mando': round(mult_mando, 2),
            }
            j['ratio'] = round(media_ajustada / max(preco, 0.1), 2)

            # Descrição textual dos contextos ativos
            descricoes = []
            for tipo, mult in [('forma', mult_forma), ('adversario', mult_adversario), ('mando', mult_mando)]:
                desc = self._descrever_contexto(mult, tipo)
                if desc:
                    descricoes.append(desc)
            j['contextos_resumo'] = " | ".join(descricoes) if descricoes else "Neutro"

            # Guardar adversário info
            if adv_id:
                cursor.execute("SELECT abreviacao FROM clubes WHERE clube_id = ?", (adv_id,))
                adv_row = cursor.fetchone()
                j['adversario_abrev'] = adv_row[0] if adv_row else '?'
            else:
                j['adversario_abrev'] = '?'
            j['mando'] = mando or '?'

        conn.close()
        return jogadores

    # ==================== INTEGRAÇÃO DE FEATURES (RANKINGS / MERCADO) ====================

    def obter_rankings_api(self):
        """Obtém rankings via API (fallback para None)"""
        try:
            return self.service.fetch_rankings(use_cache=self.use_cache)
        except Exception:
            return None

    def obter_mercado_destaques_api(self):
        """Obtém destaques de mercado (ownership / percentuais)"""
        try:
            return self.service.fetch_mercado_destaques(use_cache=self.use_cache)
        except Exception:
            return None

    def _index_rankings(self, rankings):
        """Converte lista de rankings em um mapeamento jogador_id -> list de valores"""
        if not rankings:
            return {}
        mapping = {}
        if isinstance(rankings, dict):
            # alguns endpoints retornam dicts; tentar extrair lista
            entries = rankings.get('rankings') or rankings.get('destaques') or []
        else:
            entries = rankings

        for item in entries:
            try:
                jid = item.get('atleta_id') or item.get('jogador_id') or item.get('id')
                val = item.get('valor') or item.get('pontos') or item.get('porcentagem')
                if jid is None:
                    continue
                jid = int(jid)
                mapping.setdefault(jid, []).append(val)
            except Exception:
                continue
        return mapping

    def _index_mercado(self, md):
        """Cria map jogador_id -> valor/porcentagem a partir de mercado destaques"""
        if not md:
            return {}
        mapping = {}
        entries = md.get('destaques') if isinstance(md, dict) else md
        if isinstance(entries, dict):
            # values may be lists
            entries = list(entries.values())
        for item in entries:
            if isinstance(item, dict):
                jid = item.get('atleta_id') or item.get('jogador_id') or item.get('id')
                val = item.get('valor') or item.get('porcentagem') or item.get('valor_percentual')
                if jid:
                    try:
                        mapping[int(jid)] = val
                    except Exception:
                        continue
        return mapping

    def _augment_jogadores_with_features(self, jogadores, rodada=None):
        """Anexa rankings e mercado_destaques aos objetos de jogador (in-place)."""
        # Obter extras
        rankings = self.obter_rankings_api()
        mercado = self.obter_mercado_destaques_api()

        idx_rank = self._index_rankings(rankings)
        idx_market = self._index_mercado(mercado)

        for j in jogadores:
            jid = j.get('atleta_id') or j.get('jogador_id')
            if jid:
                try:
                    jid = int(jid)
                except Exception:
                    jid = None
            j['rankings'] = idx_rank.get(jid, []) if jid else []
            j['market_val'] = idx_market.get(jid)
        return jogadores

    def extrair_top_jogadores(self, atletas_data=None, top_n=20):
        """Extrai os jogadores com maior pontuação média"""
        # Tenta usar dados da API primeiro
        if atletas_data and "atletas" in atletas_data:
            atletas = atletas_data["atletas"]
            if isinstance(atletas, dict):
                atletas = list(atletas.values())
            elif isinstance(atletas, list):
                pass
            else:
                atletas = []
        else:
            # Fallback para banco local
            atletas = self.obter_atletas_db(top_n * 2)

        if not atletas:
            raise ValueError("Nao foi possivel obter a lista de atletas")

        # Filtrar apenas jogadores prováveis (status_id = 7)
        atletas_provaveis = [a for a in atletas if a.get("status_id") == 7]

        # Ordenar por média
        def get_media(x):
            if "media_num" in x:
                return x.get("media_num", 0) or 0
            jogos = max(x.get("jogos_num", 1), 1)
            return (x.get("pontos_num", 0) or 0) / jogos

        atletas_ordenados = sorted(atletas_provaveis, key=get_media, reverse=True)

        return atletas_ordenados[:top_n]

    def construir_prompt(self, status, top_jogadores, formacao="4-3-3", orcamento=100):
        """Constrói o prompt para enviar ao modelo de IA"""
        rodada_atual = status.get("rodada_atual", 1)

        prompt = f"""Voce e um especialista em Cartola FC. Analise os jogadores abaixo e monte a melhor escalacao.

RODADA: {rodada_atual}
ORCAMENTO: C$ {orcamento:.2f}
FORMACAO: {formacao}

JOGADORES DISPONIVEIS (ordenados por media):
"""
        # Tentar enriquecer jogadores com rankings / mercado
        try:
            top_jogadores = self._augment_jogadores_with_features(top_jogadores, rodada=rodada_atual)
        except Exception:
            pass

        for i, jogador in enumerate(top_jogadores, 1):
            nome = jogador.get("apelido") or jogador.get("nome", "?")
            media = jogador.get("media_num") or 0
            preco = jogador.get("preco_num") or jogador.get("preco") or 0
            posicao = POSICOES.get(jogador.get("posicao_id"), "?")
            clube = jogador.get("clube", "?")
            rank_vals = jogador.get('rankings') or []
            rank_str = f"rank:{round(rank_vals[0],1)}" if rank_vals and rank_vals[0] is not None else ""
            market_val = jogador.get('market_val')
            market_str = f"ownership:{market_val}" if market_val is not None else ""

            extra = ""
            if rank_str and market_str:
                extra = f" | {rank_str} | {market_str}"
            elif rank_str:
                extra = f" | {rank_str}"
            elif market_str:
                extra = f" | {market_str}"

            prompt += f"{i}. {nome} ({posicao}) - {clube} | Media: {media:.1f} | C$ {preco:.1f}{extra}\n"

        prompt += f"""
TAREFA:
1. Escolha os jogadores para a formacao {formacao} respeitando o orcamento de C$ {orcamento}
2. Para cada jogador escolhido, explique em 1 frase o motivo
3. Indique o capitao (pontuacao dobrada)

Responda de forma clara e objetiva."""

        return prompt

    def tentar_hugging_face(self, prompt):
        """Tenta obter resposta usando a API da HuggingFace"""
        if not self.hf_token:
            return None

        modelos = [
            "mistralai/Mistral-7B-Instruct-v0.1",
            "microsoft/phi-2",
            "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        ]

        for modelo in modelos:
            try:
                url = f"https://api-inference.huggingface.co/models/{modelo}"
                headers = {
                    "Authorization": f"Bearer {self.hf_token}",
                    "Content-Type": "application/json"
                }

                payload = {"inputs": prompt}

                response = requests.post(url, headers=headers, json=payload, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data[0].get("generated_text", "")
                    return data.get("generated_text", "")

                elif response.status_code == 503:
                    resp_data = response.json()
                    if "estimated_time" in resp_data:
                        wait_time = min(resp_data.get("estimated_time", 10), 20)
                        time.sleep(wait_time)

                        response = requests.post(url, headers=headers, json=payload, timeout=30)
                        if response.status_code == 200:
                            data = response.json()
                            if isinstance(data, list) and len(data) > 0:
                                return data[0].get("generated_text", "")
                            return data.get("generated_text", "")

            except Exception:
                continue

        return None

    def simular_resposta_ia(self, jogadores, formacao="4-3-3"):
        """Simula uma resposta de IA quando as APIs falham"""
        # Mantém o fallback existente
        # Separar jogadores por posição
        por_posicao = {1: [], 2: [], 3: [], 4: [], 5: [], 6: []}
        for j in jogadores:
            pos = j.get("posicao_id", 0)
            if pos in por_posicao:
                por_posicao[pos].append(j)

        # Definir quantos de cada posição baseado na formação
        partes = formacao.split("-")
        if len(partes) == 3:
            n_zag = int(partes[0])
            n_mei = int(partes[1])
            n_ata = int(partes[2])
        else:
            n_zag, n_mei, n_ata = 4, 3, 3

        escalacao = []

        # Goleiro
        if por_posicao[1]:
            escalacao.append(("Goleiro", por_posicao[1][0]))

        # Laterais (2 fixos)
        for j in por_posicao[2][:2]:
            escalacao.append(("Lateral", j))

        # Zagueiros
        for j in por_posicao[3][:n_zag - 2] if n_zag > 2 else []:
            escalacao.append(("Zagueiro", j))

        # Meias
        for j in por_posicao[4][:n_mei]:
            escalacao.append(("Meia", j))

        # Atacantes
        for j in por_posicao[5][:n_ata]:
            escalacao.append(("Atacante", j))

        # Técnico
        if por_posicao[6]:
            escalacao.append(("Tecnico", por_posicao[6][0]))

        # Montar resposta
        resposta = f"ESCALACAO RECOMENDADA ({formacao}):\n\n"
        total = 0

        for pos, j in escalacao:
            nome = j.get("apelido") or j.get("nome", "?")
            clube = j.get("clube", "?")
            media = j.get("media_num") or 0
            preco = j.get("preco_num") or 0
            total += preco

            resposta += f"* {pos}: {nome} ({clube}) - Media {media:.1f}, C$ {preco:.1f}\n"
            resposta += f"  Motivo: Boa media de pontuacao e regularidade.\n\n"

        # Capitão
        if escalacao:
            capitao = max(escalacao, key=lambda x: x[1].get("media_num", 0))
            resposta += f"CAPITAO: {capitao[1].get('apelido', '?')} - Maior media do time.\n\n"

        resposta += f"CUSTO TOTAL: C$ {total:.1f}"

        return resposta

    # ==================== OTIMIZADOR (ILP / FALLBACK) ====================
    def otimizar_escacao(self, jogadores, formacao="4-3-3", orcamento=100, include_tecnico=True, top_k=60):
        """Retorna uma escalacao otimizando o ratio (media_ajustada/preco) sujeito ao orcamento e formacao.

        Usa pulp para resolver ILP. Se pulp nao estiver disponivel, usa heuristica gulosa.
        Agora otimiza ratio (value investing) em vez de soma bruta de medias.
        """
        # Filtrar top_k jogadores por media_ajustada (ou media_num se contextos nao aplicados)
        def get_valor(j):
            return j.get('media_ajustada') or j.get('media_num') or 0

        jogadores = sorted(jogadores, key=get_valor, reverse=True)[:top_k]

        # Parse formacao
        partes = formacao.split("-")
        if len(partes) == 3:
            n_def = int(partes[0])
            n_mei = int(partes[1])
            n_atk = int(partes[2])
        else:
            n_def, n_mei, n_atk = 4, 3, 3

        # Convert player list to indices
        N = len(jogadores)
        ids = list(range(N))

        # Costs and values (usa media_ajustada se disponivel)
        custos = [j.get('preco_num') or j.get('preco') or 0 for j in jogadores]
        valores = [get_valor(j) for j in jogadores]
        pos_ids = [j.get('posicao_id') or 0 for j in jogadores]

        # Calcular ratios para objetivo
        ratios = [valores[i] / max(custos[i], 0.1) for i in ids]

        # Try ILP with pulp
        try:
            import pulp

            prob = pulp.LpProblem('escala', pulp.LpMaximize)
            x = [pulp.LpVariable(f'x_{i}', cat='Binary') for i in ids]

            # Objective: maximize sum(ratio * x) - Value investing
            prob += pulp.lpSum([ratios[i] * x[i] for i in ids])

            # Budget constraint
            prob += pulp.lpSum([custos[i] * x[i] for i in ids]) <= orcamento

            # Position constraints
            # 1 goleiro
            prob += pulp.lpSum([x[i] for i in ids if pos_ids[i] == 1]) == 1
            # defenders: pos 2 (Lateral) and pos 3 (Zagueiro)
            prob += pulp.lpSum([x[i] for i in ids if pos_ids[i] in (2, 3)]) == n_def
            # meias
            prob += pulp.lpSum([x[i] for i in ids if pos_ids[i] == 4]) == n_mei
            # atacantes
            prob += pulp.lpSum([x[i] for i in ids if pos_ids[i] == 5]) == n_atk

            # Tecnico obrigatorio
            if include_tecnico:
                has_tecnico = any(pos_ids[i] == 6 for i in ids)
                if has_tecnico:
                    prob += pulp.lpSum([x[i] for i in ids if pos_ids[i] == 6]) == 1
                # Se nao tem tecnico nos candidatos, nao adiciona constraint

            # Solve
            prob.solve(pulp.PULP_CBC_CMD(msg=False))

            # Check solver status
            status = pulp.LpStatus.get(prob.status, None) if hasattr(pulp, 'LpStatus') else None
            if status and status.lower() != 'optimal':
                raise RuntimeError(f'Solver status: {status}')

            selecionados = [jogadores[i] for i in ids if (pulp.value(x[i]) or 0) >= 0.5]

            # Ensure budget satisfied
            total_custo = sum([custos[i] for i in ids if (pulp.value(x[i]) or 0) >= 0.5])
            total_val = sum([valores[i] for i in ids if (pulp.value(x[i]) or 0) >= 0.5])

            return {
                'sucesso': True,
                'selecionados': selecionados,
                'custo_total': total_custo,
                'valor_total': total_val,
                'metodo': 'ilp_ratio'
            }
        except Exception as e:
            # Fallback heuristico: escolha por posicao respeitando orcamento
            selecionados = []
            restante = orcamento

            def choose_for_positions(pos_list, n):
                nonlocal restante
                chosen = []
                candidates = [j for j in jogadores if j.get('posicao_id') in pos_list]
                candidates = sorted(candidates, key=lambda j: (get_valor(j)) / max(1e-6, (j.get('preco_num') or j.get('preco') or 0)), reverse=True)
                for c in candidates:
                    preco = c.get('preco_num') or c.get('preco') or 0
                    if len(chosen) < n and preco <= restante:
                        chosen.append(c)
                        restante -= preco
                return chosen

            # GK
            selecionados.extend(choose_for_positions([1], 1))
            # Defs
            selecionados.extend(choose_for_positions([2, 3], n_def))
            # Meias
            selecionados.extend(choose_for_positions([4], n_mei))
            # Atac
            selecionados.extend(choose_for_positions([5], n_atk))
            # Tecnico
            if include_tecnico:
                selecionados.extend(choose_for_positions([6], 1))

            total_custo = sum([p.get('preco_num') or p.get('preco') or 0 for p in selecionados])
            total_val = sum([get_valor(p) for p in selecionados])

            return {
                'sucesso': True,
                'selecionados': selecionados,
                'custo_total': total_custo,
                'valor_total': total_val,
                'fallback': True,
                'metodo': 'heuristica_ratio',
                'erro': str(e)
            }

    def consultar_ia(self, prompt, jogadores, formacao):
        """Consulta modelo de IA com fallback para simulacao local"""
        if self.use_cache:
            cache_key = f"recomendacao_{hash(prompt)}"
            cache_data = get_cache(cache_key)
            if cache_data:
                return cache_data

        # Tenta HuggingFace
        resposta = self.tentar_hugging_face(prompt)
        if resposta:
            if self.use_cache:
                set_cache(cache_key, resposta, 86400)
            return resposta

        # Fallback: simulacao local
        resposta = self.simular_resposta_ia(jogadores, formacao)

        if self.use_cache:
            set_cache(cache_key, resposta, 86400)

        return resposta

    def gerar_recomendacao(self, formacao="4-3-3", orcamento=100, top_n=20, rodada=None):
        """
        Gera uma recomendacao completa de escalacao.

        Fluxo:
        1. Obtém jogadores (API ou DB)
        2. Enriquece com contextos (forma, adversário, mando)
        3. Otimiza via ILP maximizando ratio (media_ajustada/preco)
        4. Seleciona capitão (maior media_ajustada)
        5. Retorna escalação com breakdown de contextos

        Args:
            formacao: Formacao desejada (ex: "4-3-3", "3-5-2")
            orcamento: Orcamento em cartoletas
            top_n: Numero de jogadores a analisar
            rodada: Rodada especifica (None = atual)

        Returns:
            dict com status, recomendacao e metadados
        """
        try:
            # Obter dados
            status = self.obter_status_mercado()

            # Tentar API primeiro, fallback para DB
            try:
                atletas_data = self.obter_atletas_api()
            except Exception:
                atletas_data = None

            if rodada is None:
                rodada = status.get("rodada_atual", 1)

            # Extrair jogadores (pegar mais para ter pool amplo)
            top_jogadores = self.extrair_top_jogadores(atletas_data, max(top_n, 80))

            # NOVO: Enriquecer com contextos ANTES do ILP
            try:
                top_jogadores = self._enriquecer_com_contextos(top_jogadores, rodada)
            except Exception as ctx_err:
                # Se contextos falham, continua com media_num pura
                print(f"[WARN] Contextos nao aplicados: {ctx_err}")
                for j in top_jogadores:
                    j['media_ajustada'] = j.get('media_num') or 0
                    j['multiplicador_final'] = 1.0
                    j['contextos'] = {'forma': 1.0, 'adversario': 1.0, 'mando': 1.0}
                    j['ratio'] = (j.get('media_num') or 0) / max(j.get('preco_num') or j.get('preco') or 0.1, 0.1)
                    j['contextos_resumo'] = "Sem dados"

            # Tentar otimizacao
            try:
                otim = self.otimizar_escacao(
                    top_jogadores,
                    formacao=formacao,
                    orcamento=orcamento,
                    include_tecnico=True,
                    top_k=max(top_n, 80)
                )
            except Exception:
                otim = None

            if otim and otim.get('sucesso') and otim.get('selecionados'):
                selecionados = otim['selecionados']

                # Enriquecer selecao com features de API (rankings, mercado)
                try:
                    selecionados = self._augment_jogadores_with_features(selecionados, rodada=rodada)
                except Exception:
                    pass

                # Construir texto com contextos
                total_custo = otim.get('custo_total', 0)
                total_val = otim.get('valor_total', 0)
                metodo = otim.get('metodo', 'ilp')

                # Capitao: maior media_ajustada (excluindo tecnico)
                jogadores_campo = [j for j in selecionados if j.get('posicao_id') != 6]
                if jogadores_campo:
                    capitao = max(jogadores_campo, key=lambda x: x.get('media_ajustada') or x.get('media_num', 0))
                    capitao['is_capitao'] = True
                    capitao['pontuacao_dobrada'] = round((capitao.get('media_ajustada') or capitao.get('media_num', 0)) * 2, 2)
                else:
                    capitao = None

                # Calcular pontuacao total prevista (com capitao dobrado)
                pont_total = sum(j.get('media_ajustada') or j.get('media_num', 0) for j in selecionados)
                if capitao:
                    pont_total += capitao.get('media_ajustada') or capitao.get('media_num', 0)  # somar extra do capitao

                economia = orcamento - total_custo

                texto = self._formatar_saida(selecionados, formacao, total_custo, pont_total, economia, capitao, metodo, rodada)
                recomendacao = texto

                # AUTO-SAVE: Salvar recomendacao para tracking
                try:
                    self._salvar_recomendacao(rodada, formacao, orcamento, otim, capitao)
                except Exception as save_err:
                    print(f"[WARN] Falha ao salvar recomendacao: {save_err}")

                # Montar response JSON rico
                response_data = {
                    "status": "success",
                    "rodada": rodada,
                    "formacao": formacao,
                    "orcamento": orcamento,
                    "jogadores_analisados": len(top_jogadores),
                    "recomendacao": recomendacao,
                    "timestamp": time.time(),
                    "time_otimizado": {
                        "custo_total": round(total_custo, 1),
                        "pontuacao_prevista": round(pont_total, 1),
                        "economia": round(economia, 1),
                        "metodo": metodo,
                        "jogadores": [
                            {
                                "posicao": POSICOES.get(j.get('posicao_id'), '?'),
                                "nome": j.get('apelido') or j.get('nome', '?'),
                                "clube": j.get('clube', '?'),
                                "preco": j.get('preco_num') or j.get('preco') or 0,
                                "pontuacao_prevista": j.get('media_ajustada') or j.get('media_num', 0),
                                "media_base": j.get('media_num', 0),
                                "ratio": j.get('ratio', 0),
                                "is_capitao": j.get('is_capitao', False),
                                "multiplicador": j.get('multiplicador_final', 1.0),
                                "contextos": j.get('contextos', {}),
                                "contextos_resumo": j.get('contextos_resumo', ''),
                            }
                            for j in selecionados
                        ]
                    }
                }
                return response_data

            else:
                # Construir prompt e consultar IA
                prompt = self.construir_prompt(status, top_jogadores, formacao, orcamento)
                recomendacao = self.consultar_ia(prompt, top_jogadores, formacao)

            return {
                "status": "success",
                "rodada": rodada,
                "formacao": formacao,
                "orcamento": orcamento,
                "jogadores_analisados": len(top_jogadores),
                "recomendacao": recomendacao,
                "timestamp": time.time()
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def _formatar_saida(self, selecionados, formacao, total_custo, pont_total, economia, capitao, metodo, rodada):
        """Formata saida textual rica com contextos e breakdown"""
        pos_map = {1: 'GOL', 2: 'LAT', 3: 'ZAG', 4: 'MEI', 5: 'ATA', 6: 'TEC'}
        pos_order = [1, 2, 3, 4, 5, 6]

        texto = ""
        texto += f"ESCALACAO OTIMIZADA ({formacao}) | Rodada {rodada}\n"
        texto += f"Custo: C$ {total_custo:.1f} | Previsto: {pont_total:.1f} pts | Economia: C$ {economia:.1f}\n"
        texto += "-" * 60 + "\n\n"

        # Agrupar por posicao
        by_pos = {}
        for p in selecionados:
            pid = p.get('posicao_id')
            by_pos.setdefault(pid, []).append(p)

        for pos_id in pos_order:
            players = by_pos.get(pos_id, [])
            for p in players:
                nome = p.get('apelido') or p.get('nome', '?')
                clube = p.get('clube', '?')
                preco = p.get('preco_num') or p.get('preco') or 0
                media_base = p.get('media_num') or 0
                media_aj = p.get('media_ajustada') or media_base
                mult = p.get('multiplicador_final', 1.0)
                ratio = p.get('ratio', 0)
                ctx_resumo = p.get('contextos_resumo', '')
                is_cap = p.get('is_capitao', False)
                adv = p.get('adversario_abrev', '?')
                mando = p.get('mando', '?')

                # Indicador de mando
                mando_icon = "(C)" if mando == 'casa' else "(F)" if mando == 'fora' else ""

                # Linha principal
                cap_marker = " [C]" if is_cap else ""
                texto += f"  {pos_map.get(pos_id, '?'):3s} {nome:<20s} [{clube:3s}]  vs {adv:3s} {mando_icon}\n"
                texto += f"      C$ {preco:<6.1f} | {media_base:.1f} -> {media_aj:.1f} pts (x{mult:.2f}) | ratio {ratio:.2f}{cap_marker}\n"

                # Contextos se nao neutro
                if ctx_resumo and ctx_resumo != "Neutro":
                    texto += f"      [{ctx_resumo}]\n"

                texto += "\n"

        # Capitao
        if capitao:
            cap_nome = capitao.get('apelido') or capitao.get('nome', '?')
            cap_pts = capitao.get('media_ajustada') or capitao.get('media_num', 0)
            texto += "-" * 60 + "\n"
            texto += f"CAPITAO: {cap_nome} ({cap_pts:.1f} pts x2 = {cap_pts*2:.1f} pts)\n"

        texto += f"\n(Metodo: {metodo})"
        return texto


    def _salvar_recomendacao(self, rodada, formacao, orcamento, resultado_otim, capitao):
        """Salva recomendacao no banco para tracking futuro."""
        from database import salvar_recomendacao

        try:
            selecionados = resultado_otim['selecionados']
            custo_total = resultado_otim['custo_total']
            metodo = resultado_otim.get('metodo', 'ilp')

            # Pontuacao prevista total (com capitao dobrado)
            pont_prevista = sum(
                j.get('media_ajustada') or j.get('media_num', 0)
                for j in selecionados
            )
            if capitao:
                pont_prevista += capitao.get('media_ajustada') or capitao.get('media_num', 0)

            jogadores_db = []
            for j in selecionados:
                jogadores_db.append({
                    'jogador_id': j.get('atleta_id') or j.get('jogador_id'),
                    'posicao_id': j.get('posicao_id'),
                    'clube_id': j.get('clube_id'),
                    'preco': j.get('preco_num') or j.get('preco', 0),
                    'media_base': j.get('media_num', 0),
                    'media_ajustada': j.get('media_ajustada') or j.get('media_num', 0),
                    'multiplicador': j.get('multiplicador_final', 1.0),
                    'pontuacao_prevista': j.get('media_ajustada') or j.get('media_num', 0),
                    'is_capitao': j.get('is_capitao', False),
                    'contextos': j.get('contextos', {}),
                    'adversario_id': j.get('adversario_id'),
                    'mando': j.get('mando')
                })

            capitao_id = (capitao.get('atleta_id') or capitao.get('jogador_id')) if capitao else None

            rec_id = salvar_recomendacao(
                rodada=rodada,
                temporada=TEMPORADA_ATUAL_DB,
                formacao=formacao,
                orcamento=orcamento,
                custo_total=custo_total,
                pontuacao_prevista=pont_prevista,
                metodo=metodo,
                capitao_id=capitao_id,
                jogadores=jogadores_db
            )

            if rec_id:
                print(f"\n[TRACKING] Recomendacao salva: ID={rec_id}, Rodada={rodada}")
            return rec_id

        except Exception as e:
            print(f"[TRACKING] Erro ao salvar: {e}")
            return None


def gerar_recomendacao(formacao="4-3-3", orcamento=100, top_n=20, rodada=None):
    """Funcao de conveniencia para gerar recomendacao"""
    recommender = CartolaRecommendation()
    return recommender.gerar_recomendacao(formacao, orcamento, top_n, rodada)


if __name__ == "__main__":
    import sys

    formacao = "4-3-3"
    orcamento = 100

    for arg in sys.argv[1:]:
        if "-" in arg and arg[0].isdigit():
            formacao = arg
        else:
            try:
                orcamento = float(arg)
            except ValueError:
                pass

    print("=" * 60)
    print("FANTASYBRAIN V1.0 - RECOMENDACAO HIBRIDA (Contexto + Value)")
    print("=" * 60)
    print(f"\nFormacao: {formacao}")
    print(f"Orcamento: C$ {orcamento}")
    print("\nGerando recomendacao...\n")

    resultado = gerar_recomendacao(formacao, orcamento)

    if resultado["status"] == "success":
        print(resultado["recomendacao"])

        # Mostrar resumo JSON se disponivel
        if "time_otimizado" in resultado:
            print("\n" + "=" * 60)
            print("RESUMO JSON:")
            print(f"  Jogadores: {len(resultado['time_otimizado']['jogadores'])}")
            print(f"  Custo: C$ {resultado['time_otimizado']['custo_total']}")
            print(f"  Pontuacao prevista: {resultado['time_otimizado']['pontuacao_prevista']} pts")
            print(f"  Economia: C$ {resultado['time_otimizado']['economia']}")
            print(f"  Metodo: {resultado['time_otimizado']['metodo']}")
    else:
        print(f"Erro: {resultado['message']}")
