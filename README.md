# Geophysics AI

Redução e interpretação de dados brutos de levantamento geofísico de campo — gravimetria (anomalia Bouguer via Fórmula Internacional da Gravidade 1980 + correção ar-livre + correção Bouguer simples), magnetometria (redução ao polo via filtro espectral FFT), eletrorresistividade (sondagem elétrica vertical, arranjos Wenner e Schlumberger) e sísmica de refração (método da distância de cruzamento, 2 camadas), mais delimitação estatística de anomalias residuais (z-score + componentes conexos). O agente **nunca calcula um número sozinho**: toda anomalia, resistividade, velocidade/profundidade e mancha detectada é sempre produto de uma função determinística (numpy/scipy) em `app/geophysics/` — o LLM só decide qual ferramenta chamar e interpreta o resultado já calculado.

Este repositório é o **MVP (Fase 2)** descrito em [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md), que também cobre a Fase 1 completa.

Distinto do **Geology AI** (sensoriamento remoto/geologia estrutural sobre DEM, litologia e rasters espectrais já classificados — lineamentos, suscetibilidade a deslizamento, anomalia mineral espectral, correlação de sondagens estratigráficas): o Geophysics AI trata da **redução/inversão de dados brutos de instrumento geofísico de campo** — a leitura de um gravímetro, a tensão/corrente de um resistivímetro, o tempo de primeira chegada de um sismógrafo.

## O que já funciona

- Cadastro de levantamento (boundary GeoJSON, tipo) e de estações gravimétricas, sondagens elétricas (SEV) e linhas de refração sísmica (código, coordenadas geográficas), com importação em lote (CSV) das leituras de campo.
- **Redução Bouguer**: gravidade teórica pela Fórmula Internacional da Gravidade 1980 (IGF80/GRS80), correção ar-livre (0.3086×h) e correção Bouguer simples (0.04193×ρ×h, placa de Bouguer) — **sem** correção de terreno, uma limitação real e documentada do MVP, nunca escondida.
- **Redução ao polo (RTP)**: filtro de fase/amplitude no domínio do número de onda (Blakely, 1995) via FFT 2D — testado de forma verificável: uma anomalia sintética distorcida por um campo inclinado é recuperada com simetria e centrada exatamente sobre a fonte após o RTP.
- **Sondagem elétrica vertical (SEV)**: resistividade aparente por arranjo Wenner (`ρa=2πa·V/I`) e Schlumberger (`ρa=π((L/2)²-(l/2)²)/l·V/I`), curva vs. espaçamento, profundidade de investigação heurística — sem inversão 1D de camadas (limitação declarada).
- **Refração sísmica**: método da distância de cruzamento (2 camadas horizontais) — V1/V2 por mínimos quadrados de cada ramo da dromocrônica, ângulo crítico e profundidade da interface, com duas estimativas de profundidade independentes para checagem cruzada de consistência.
- **Detecção de anomalias**: limiar de z-score + `scipy.ndimage.label` sobre uma grade residual (Bouguer ou RTP), delimitando manchas candidatas a corpo-fonte (contagem, centroide, área, valor médio/pico) — uma ferramenta de triagem estatística, nunca uma classificação geológica automática.
- Chat com agente (tool calling via Anthropic) que decide quais dessas ferramentas chamar — o `SYSTEM_PROMPT` proíbe explicitamente inventar anomalias, valores de RTP, resistividades ou parâmetros sísmicos.
- Toda resposta de análise inclui `{method, parameters, uncertainty_note, limitations}` — nunca um número sem contexto de como foi calculado.
- Camada de processamento (`backend/app/geophysics/`) 100% testada com `pytest` (39 testes) — só numpy/scipy, sem depender de banco ou GDAL; cada teste verifica valores conferidos por cálculo numérico independente (gravimetria, resistividade) ou por uma propriedade geofísica genuína e checável (simetria pós-RTP, recuperação de V1/V2/profundidade sísmicos a partir de dados sintéticos gerados com verdade conhecida).
- Frontend: mapa de estações/sondagens/linhas, painel de gravimetria (perfil de anomalia Bouguer), painel de magnetometria (RTP sobre grade de exemplo), painel de resistividade (curva de sondagem log-log) e painel de sísmica (dromocrônica + ramos ajustados), mais chat.
- Gerador de dados simulados (`backend/scripts/seed_demo_data.py`): perfil de 12 estações gravimétricas com anomalia Bouguer "verdadeira" conhecida (corpo gaussiano + gradiente regional), 3 sondagens elétricas com curva descendente tipo H, e 2 linhas de refração sísmica de 2 camadas — todos com parâmetros verdadeiros conhecidos, recuperados pelos módulos determinísticos dentro do ruído injetado.

## O que fica para as próximas fases

Leitura/parsing de formatos binários proprietários de instrumento (gravímetro, magnetômetro, resistivímetro, sismógrafo multicanal — o MVP consome leituras já digitalizadas, sintéticas ou importadas via CSV), correção de terreno gravimétrica completa (templates de Hammer/integração sobre DEM), inversão 1D/2D/3D completa de qualquer método, classificação automática de fácies sísmicas e modelos de aprendizado de máquina (Fase 3), correção de maré terrestre/deriva instrumental do gravímetro, método de tempo-intercepto generalizado (GRM) e detecção de mergulho de camada em refração sísmica, RTP estabilizado de baixa latitude (pseudo-inclinado), geração automática de relatório PDF/DOCX, autenticação multi-tenant completa.

## Rodando localmente

### Com Docker (recomendado)

```bash
cp backend/.env.example backend/.env
# edite backend/.env e defina ANTHROPIC_API_KEY para habilitar o chat

docker compose up --build
docker compose exec backend python -m app.init_db
docker compose exec backend python -m scripts.seed_demo_data   # opcional: dados de demonstração
```

- Frontend: http://localhost:3000
- Backend (OpenAPI): http://localhost:8000/docs

### Sem Docker (desenvolvimento rápido do backend)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. pytest tests/ -v      # camada de processamento geofísica, roda sem banco/GDAL
uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
npm run dev
```

## Estrutura

Ver a árvore completa em [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md#2-estrutura-de-pastas).

```
geophysics-ai/
├── docs/ARQUITETURA.md   # Fase 1 completa
├── backend/              # FastAPI + geophysics/ (gravimetria, RTP, SEV, refração, anomalias) + agente
├── frontend/              # Next.js + mapa + painéis de gravimetria/magnetometria/resistividade/sísmica + chat
└── docker-compose.yml    # Postgres+PostGIS, Redis, MinIO, backend, worker, frontend
```
