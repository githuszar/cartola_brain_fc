# FantasyBrain - Status do Projeto e Roadmap

## Onde estamos (Fevereiro 2026)

### V1.0 - Sistema Hibrido (Contexto + Value) - ENTREGUE

O motor de recomendacao gera escalacoes otimizadas usando:

- **Otimizacao ILP (PuLP)**: maximiza ratio pontos/preco (value investing)
- **Contextos de jogo**: 3 multiplicadores ajustam a previsao base
  - Forma recente (ultimas 3 rodadas do time)
  - Qualidade do adversario (hibrido tabela atual + historica)
  - Mando de campo (casa/fora)
- **Tecnico obrigatorio** + selecao automatica de capitao
- **Tracking ao vivo**: salva previsoes antes da rodada, valida contra pontuacao real depois
- **Decay temporal**: times promovidos da Serie B sem historico na Serie A usam somente tabela atual

### O que funciona hoje

| Componente        | Status    | Descricao                                      |
|-------------------|-----------|-------------------------------------------------|
| ia_service.py     | OK        | Motor de recomendacao com contextos e ILP       |
| database.py       | OK        | Tabelas de tracking (salvar + validar)          |
| validar.py        | OK        | CLI de validacao (pendentes, rodada, detalhe)   |
| sync.py           | OK        | Sync API + flag --validar                       |
| cartola_service.py| OK        | Fix encerrada com fallback por placar           |
| constants.py      | OK        | TABELA_2024, multiplicadores, temporadas        |

### Banco de dados

| Dado                     | Volume       | Uso atual                |
|--------------------------|-------------|--------------------------|
| Pontuacoes historicas    | 235k registros, 8 temporadas (2018-2026) | NAO USADO              |
| Scouts detalhados        | 235k registros, 29 metricas por jogo     | NAO USADO              |
| Jogadores provaveis      | 205 jogadores, media 128 jogos historicos | Usa so media_pontos API |
| Partidas                 | 8 temporadas completas                   | Usado para contextos    |

---

## O problema: motor subutiliza os dados

O sistema hoje preve a pontuacao de um jogador usando **apenas a media dos ultimos 2 jogos** (campo `media_pontos` da API do Cartola). Depois aplica multiplicadores de contexto (casa/fora, adversario, forma).

Isso e como prever a nota de um aluno olhando so as 2 ultimas provas.

No banco existem **128 jogos em media por jogador** que nao sao usados. A melhoria com maior impacto e usar esses dados historicos para construir uma previsao mais solida.

### Impacto estimado de cada melhoria

```
Estado atual (media 2 jogos + contextos):  ~50% acerto direcional
+ Media historica ponderada:               ~60-65%  << MAIOR SALTO
+ Matchup especifico (jogador vs clube):   ~65-70%
+ Mando real por jogador:                  ~68-72%
+ Consistencia/volatilidade:               ~70-73%
```

Cada nova pista melhora a previsao, mas o ganho diminui progressivamente (retornos decrescentes). A media historica ponderada e de longe a melhoria #1 porque transforma uma base de 2 jogos em 100+.

---

## Proximas 3 etapas macro

### ETAPA 1: Media Historica Ponderada (V1.1)

**Objetivo**: Substituir `media_pontos` da API (2 jogos) por uma media robusta baseada no historico completo.

**Como funciona**:
- Temporada atual (2026): peso 3
- Temporada anterior (2025): peso 2
- Retrasada (2024): peso 1
- Media ponderada = soma(pontuacao * peso) / soma(peso)

**Exemplo pratico**:
```
Raniele - media API atual: 11.4 pts (baseada em 2 jogos)
Raniele - media historica ponderada:
  2026 (2 jogos):  11.4 * peso 3 = 34.2
  2025 (38 jogos):  6.8 * peso 2 = 13.6
  2024 (35 jogos):  5.2 * peso 1 =  5.2
  Media ponderada = (34.2 + 13.6 + 5.2) / (3+2+1) = 8.8 pts
```

A previsao cai de 11.4 para 8.8 — mais realista, porque 2 jogos sao pouco para confiar. Conforme a temporada avanca e mais jogos acumulam, o peso da temporada atual domina naturalmente.

**Dados necessarios**: tabela `pontuacoes_jogadores` (ja existe, 235k registros)

**Impacto estimado**: +10-15% de acerto. Maior ganho com menor esforco.

---

### ETAPA 2: Matchup Especifico + Mando Real (V1.2)

**Objetivo**: Usar dados historicos de como cada jogador performa contra adversarios especificos e em casa/fora.

**Matchup especifico**:
- Consulta: "Como o jogador X pontuou historicamente contra o clube Y?"
- Se tem 5+ jogos contra aquele adversario, usa a media especifica como ajuste
- Substitui o multiplicador fixo de adversario (x0.85 / x1.25) por dado real

**Mando real por jogador**:
- Consulta: "Qual a media do jogador em casa vs fora nos ultimos 3 anos?"
- Jogadores com diferenca significativa (>15%) recebem ajuste personalizado
- Substitui o multiplicador fixo de mando (x1.10 / x0.95) por dado real

**Exemplo pratico**:
```
Jogador A: media geral 6.0
  - vs Santos (8 jogos): media 8.5 -> ajuste +41%
  - Em casa (50 jogos): media 6.8 -> ajuste +13%
  Previsao ajustada contra Santos em casa: muito mais precisa que x1.25 fixo
```

**Dados necessarios**: tabela `pontuacoes_jogadores` com colunas `adversario_id` e `mando` (ja existem)

**Impacto estimado**: +5-8% de acerto sobre V1.1.

---

### ETAPA 3: Scouts e Consistencia (V1.3)

**Objetivo**: Usar as 29 metricas detalhadas de scouts para refinar previsoes e medir risco.

**Consistencia/Volatilidade**:
- Calcular desvio padrao da pontuacao de cada jogador
- Jogador consistente (desvio baixo): previsao mais confiavel
- Jogador explosivo (desvio alto): alto risco/alta recompensa
- Permite ao usuario escolher: escalacao "segura" vs "arriscada"

**Perfil de scouts por posicao**:
- Goleiro que faz muitas defesas dificeis -> tende a pontuar mais
- Atacante com alta taxa de finalizacoes certas -> mais chances de gol
- Zagueiro com muitos desarmes e roubadas -> pontuacao consistente
- Usar scouts como features preditivas alem da pontuacao bruta

**Scouts disponiveis no banco**:
```
Ofensivos: gols, assistencias, finalizacoes, passes_certos, pre_assistencias
Defensivos: desarmes, roubadas_bola, defesas, defesas_dificeis, jogos_sem_sofrer_gols
Negativos: faltas_cometidas, cartoes_amarelos, cartoes_vermelhos, gols_sofridos, penaltis_perdidos
```

**Dados necessarios**: tabela `scouts_jogadores` (ja existe, 235k registros)

**Impacto estimado**: +3-5% de acerto sobre V1.2.

---

## Resumo visual do roadmap

```
V1.0 (ATUAL)                    V1.1                    V1.2                    V1.3
Media 2 jogos + contextos  -->  Media historica     -->  Matchup + Mando    -->  Scouts + Risco
~50% acerto                     ~60-65%                  ~68-72%                 ~70-75%
|                               |                        |                       |
Entregue                        Proximo passo            Refinamento             Avancado
```

---

## Principio do projeto

> Cada etapa usa dados que JA EXISTEM no banco (235k pontuacoes + 235k scouts).
> Nao precisamos buscar dados externos. O ganho vem de usar melhor o que ja temos.
> A prioridade e sempre: maior impacto com menor complexidade primeiro.
