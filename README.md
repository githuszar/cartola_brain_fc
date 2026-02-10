# FantasyBrain V1.0

Sistema inteligente de coleta, análise e recomendação para o Cartola FC.

## O que é

O FantasyBrain coleta dados do Cartola FC (jogadores, partidas, pontuações) e armazena localmente para análise. Com esses dados, você pode:

- Acompanhar a evolução de preços dos jogadores
- Analisar performance por adversário (casa/fora)
- Gerar recomendações de escalação com IA
- Construir estratégias baseadas em dados históricos

## Instalação

```bash
# 1. Clone o repositório
git clone <seu-repositorio>
cd cartola_brain_fc

# 2. Crie e ative o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou: .venv\Scripts\activate  # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. (Opcional) Configure variáveis de ambiente
cp .env.example .env
# Edite .env se quiser usar IA da HuggingFace
```

## Uso

### Sincronizar dados

```bash
# Sincroniza rodada atual
python sync.py

# Sincroniza rodada específica
python sync.py --rodada 5

# Força atualização (ignora cache)
python sync.py --force

# Ver status do mercado
python sync.py --status

# Ver estatísticas do banco
python sync.py --stats

# Ver top jogadores
python sync.py --top
```

### Gerar recomendação de escalação

```bash
# Recomendação padrão (4-3-3, orçamento 100)
python ia_service.py

# Formação e orçamento específicos
python ia_service.py 3-5-2 120
```

## Estrutura do Projeto

```
fantasybrain/
├── sync.py              # Script principal de sincronização
├── cartola_service.py   # Integração com API do Cartola
├── ia_service.py        # Geração de recomendações com IA
├── database.py          # Configuração do SQLite
├── cache.py             # Sistema de cache local
├── cartola_data.db      # Banco de dados (criado automaticamente)
├── requirements.txt     # Dependências Python
├── .env                 # Variáveis de ambiente (opcional)
└── .cache/              # Cache de requisições (criado automaticamente)
```

## Banco de Dados

O sistema usa SQLite para armazenamento local. As tabelas são:

| Tabela | Descrição |
|--------|-----------|
| `clubes` | Times do Brasileirão |
| `jogadores` | Jogadores disponíveis no Cartola |
| `partidas` | Jogos de cada rodada |
| `pontuacoes_jogadores` | Pontuação por jogador por rodada |
| `scouts_jogadores` | Estatísticas detalhadas (gols, assistências, etc) |
| `historico_jogadores` | Evolução de preço/média ao longo do tempo |
| `calendario` | Confrontos futuros (adversário, casa/fora) |

### Consultas úteis

```bash
# Abrir banco no terminal
sqlite3 cartola_data.db

# Ver jogadores mais caros
SELECT apelido, clube, preco FROM jogadores ORDER BY preco DESC LIMIT 10;

# Ver pontuações contra um time específico
SELECT j.apelido, p.pontuacao, c.abreviacao as adversario
FROM pontuacoes_jogadores p
JOIN jogadores j ON p.jogador_id = j.jogador_id
JOIN clubes c ON p.adversario_id = c.clube_id
WHERE c.abreviacao = 'FLA';
```

## Comandos Rápidos

```bash
# Sincronização diária (rode 1-2x por dia)
python sync.py

# Ver status antes de escalar
python sync.py --status

# Gerar recomendação
python ia_service.py

# Ver seus dados
python sync.py --stats
```

## Variáveis de Ambiente

Crie um arquivo `.env` (opcional):

```env
# Token HuggingFace para usar IA (opcional)
HF_TOKEN=seu_token_aqui

# Usar cache (padrão: true)
USE_CACHE=true
```

## Dicas de Uso

1. **Sincronize regularmente**: Rode `python sync.py` pelo menos 1x por dia durante o campeonato

2. **Melhor momento para sincronizar**:
   - Após o fechamento do mercado (dados de escalação)
   - Após o fim da rodada (pontuações)

3. **Cache**: O sistema cacheia requisições para não sobrecarregar a API. Use `--force` se precisar de dados frescos

4. **Backup**: O arquivo `cartola_data.db` é seu banco. Faça backup periodicamente!

## Roadmap

- [ ] Interface web para visualização
- [ ] Análise de confrontos diretos
- [ ] Previsão com Machine Learning
- [ ] Integração com outras fontes de dados

## Licença

MIT

---

Desenvolvido para o Brasileirão 2026
