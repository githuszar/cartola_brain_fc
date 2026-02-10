"""
FantasyBrain V1.0 - Serviço de Recomendação com IA

Gera recomendações de escalação usando modelos de IA.
"""

import os
import requests
import time
from dotenv import load_dotenv
from cache import get_cache, set_cache
from database import get_connection, POSICOES
from cartola_service import CartolaService  # para acessar novos endpoints (rankings, mercado)

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
            raise ValueError("Não foi possível obter a lista de atletas")

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

        prompt = f"""Você é um especialista em Cartola FC. Analise os jogadores abaixo e monte a melhor escalação.

RODADA: {rodada_atual}
ORÇAMENTO: C$ {orcamento:.2f}
FORMAÇÃO: {formacao}

JOGADORES DISPONÍVEIS (ordenados por média):
"""
        # Tentar enriquecer jogadores com rankings / mercado
        try:
            top_jogadores = self._augment_jogadores_with_features(top_jogadores, rodada=rodada)
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

            prompt += f"{i}. {nome} ({posicao}) - {clube} | Média: {media:.1f} | C$ {preco:.1f}{extra}\n"

        prompt += f"""
TAREFA:
1. Escolha os jogadores para a formação {formacao} respeitando o orçamento de C$ {orcamento}
2. Para cada jogador escolhido, explique em 1 frase o motivo
3. Indique o capitão (pontuação dobrada)

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
            escalacao.append(("Técnico", por_posicao[6][0]))

        # Montar resposta
        resposta = f"ESCALAÇÃO RECOMENDADA ({formacao}):\n\n"
        total = 0

        for pos, j in escalacao:
            nome = j.get("apelido") or j.get("nome", "?")
            clube = j.get("clube", "?")
            media = j.get("media_num") or 0
            preco = j.get("preco_num") or 0
            total += preco

            resposta += f"• {pos}: {nome} ({clube}) - Média {media:.1f}, C$ {preco:.1f}\n"
            resposta += f"  Motivo: Boa média de pontuação e regularidade.\n\n"

        # Capitão
        if escalacao:
            capitao = max(escalacao, key=lambda x: x[1].get("media_num", 0))
            resposta += f"CAPITÃO: {capitao[1].get('apelido', '?')} - Maior média do time.\n\n"

        resposta += f"CUSTO TOTAL: C$ {total:.1f}"

        return resposta

    # ==================== OTIMIZADOR (ILP / FALLBACK) ====================
    def otimizar_escacao(self, jogadores, formacao="4-3-3", orcamento=100, include_tecnico=False, top_k=60):
        """Retorna uma escalação otimizando a soma das médias (media_num) sujeito ao orçamento e formação.

        Usa pulp para resolver ILP. Se pulp não estiver disponível, usa heurística gulosa.
        """
        # Filtrar top_k jogadores por média
        jogadores = sorted(jogadores, key=lambda x: (x.get('media_num') or 0), reverse=True)[:top_k]

        # Parse formação
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

        # Costs and values
        custos = [j.get('preco_num') or j.get('preco') or 0 for j in jogadores]
        valores = [j.get('media_num') or 0 for j in jogadores]
        pos_ids = [j.get('posicao_id') or 0 for j in jogadores]

        # Try ILP with pulp
        try:
            import pulp

            prob = pulp.LpProblem('escala', pulp.LpMaximize)
            x = [pulp.LpVariable(f'x_{i}', cat='Binary') for i in ids]

            # Objective: maximize sum(value * x)
            prob += pulp.lpSum([valores[i] * x[i] for i in ids])

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

            # tecnico optional
            if include_tecnico:
                prob += pulp.lpSum([x[i] for i in ids if pos_ids[i] == 6]) <= 1

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
                'valor_total': total_val
            }
        except Exception as e:
            # Fallback heurístico: escolha por posição respeitando orçamento
            selecionados = []
            restante = orcamento

            def choose_for_positions(pos_list, n):
                nonlocal restante
                chosen = []
                candidates = [j for j in jogadores if j.get('posicao_id') in pos_list]
                candidates = sorted(candidates, key=lambda x: (x.get('media_num') or 0) / max(1e-6, (x.get('preco_num') or x.get('preco') or 0)), reverse=True)
                for c in candidates:
                    preco = c.get('preco_num') or c.get('preco') or 0
                    if len(chosen) < n and preco <= restante:
                        chosen.append(c)
                        restante -= preco
                return chosen

            # GK
            gk_cand = choose_for_positions([1], 1)
            selecionados.extend(gk_cand)
            # Defs
            selecionados.extend(choose_for_positions([2,3], n_def))
            # Meias
            selecionados.extend(choose_for_positions([4], n_mei))
            # Atac
            selecionados.extend(choose_for_positions([5], n_atk))

            total_custo = sum([p.get('preco_num') or p.get('preco') or 0 for p in selecionados])
            total_val = sum([p.get('media_num') or 0 for p in selecionados])

            return {
                'sucesso': True,
                'selecionados': selecionados,
                'custo_total': total_custo,
                'valor_total': total_val,
                'fallback': True,
                'erro': str(e)
            }

    def consultar_ia(self, prompt, jogadores, formacao):
        """Consulta modelo de IA com fallback para simulação local"""
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

        # Fallback: simulação local
        resposta = self.simular_resposta_ia(jogadores, formacao)

        if self.use_cache:
            set_cache(cache_key, resposta, 86400)

        return resposta

    def gerar_recomendacao(self, formacao="4-3-3", orcamento=100, top_n=20, rodada=None):
        """
        Gera uma recomendação completa de escalação.

        Args:
            formacao: Formação desejada (ex: "4-3-3", "3-5-2")
            orcamento: Orçamento em cartoletas
            top_n: Número de jogadores a analisar
            rodada: Rodada específica (None = atual)

        Returns:
            dict com status, recomendação e metadados
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

            # Extrair jogadores
            top_jogadores = self.extrair_top_jogadores(atletas_data, top_n)

            # Tentar otimização para garantir orçamento
            try:
                otim = self.otimizar_escacao(top_jogadores, formacao=formacao, orcamento=orcamento, include_tecnico=False, top_k=max(top_n, 60))
            except Exception:
                otim = None

            if otim and otim.get('sucesso') and otim.get('selecionados'):
                selecionados = otim['selecionados']
                # Enriquecer seleção com features
                try:
                    selecionados = self._augment_jogadores_with_features(selecionados, rodada=rodada)
                except Exception:
                    pass

                # Construir texto objetivo com custo e motivos simples
                total_custo = otim.get('custo_total', 0)
                total_val = otim.get('valor_total', 0)

                texto = f"ESCALAÇÃO OTIMIZADA ({formacao}) - CUSTO TOTAL: C$ {total_custo:.1f}\n\n"

                # Agrupar por posição para exibição ordenada
                pos_map = {1: 'Goleiro', 2: 'Lateral', 3: 'Zagueiro', 4: 'Meia', 5: 'Atacante', 6: 'Técnico'}
                by_pos = {}
                for p in selecionados:
                    pid = p.get('posicao_id')
                    by_pos.setdefault(pid, []).append(p)

                for pos_id in [1, 2, 3, 4, 5, 6]:
                    players = by_pos.get(pos_id, [])
                    for p in players:
                        nome = p.get('apelido') or p.get('nome', '?')
                        clube = p.get('clube', '?')
                        media = p.get('media_num') or 0
                        preco = p.get('preco_num') or p.get('preco') or 0
                        motivo = f"Média {media:.1f} | Preço C$ {preco:.1f}"
                        texto += f"• {pos_map.get(pos_id, '?')}: {nome} ({clube}) - {motivo}\n"

                # Capitão: maior média
                if selecionados:
                    capitao = max(selecionados, key=lambda x: x.get('media_num', 0))
                    texto += f"\nCAPITÃO SUGERIDO: {capitao.get('apelido', capitao.get('nome', '?'))} - Média {capitao.get('media_num', 0):.1f}\n"

                # Adicionar nota sobre otimizador
                texto += f"\n(Selecionado por otimizador ILP)"

                recomendacao = texto
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


def gerar_recomendacao(formacao="4-3-3", orcamento=100, top_n=20, rodada=None):
    """Função de conveniência para gerar recomendação"""
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
    print("FANTASYBRAIN V1.0 - RECOMENDAÇÃO DE ESCALAÇÃO")
    print("=" * 60)
    print(f"\nFormação: {formacao}")
    print(f"Orçamento: C$ {orcamento}")
    print("\nGerando recomendação...\n")

    resultado = gerar_recomendacao(formacao, orcamento)

    if resultado["status"] == "success":
        print(resultado["recomendacao"])
    else:
        print(f"Erro: {resultado['message']}")
