# Geophysics AI — Especificação técnica (Fase 1)

> Redução e interpretação de dados brutos de levantamento geofísico de campo — gravimetria (anomalia Bouguer), magnetometria (redução ao polo), eletrorresistividade (sondagem elétrica vertical) e sísmica de refração (método da distância de cruzamento), mais delimitação estatística de anomalias residuais. Distinto do **Geology AI** (que trata de sensoriamento remoto e geologia estrutural sobre DEM/litologia/rasters espectrais já classificados — lineamentos, suscetibilidade a deslizamento, anomalia mineral espectral, correlação de sondagens estratigráficas): o Geophysics AI trata da **redução/inversão de dados brutos de instrumento geofísico de campo** — a leitura de um gravímetro, a tensão/corrente de um resistivímetro, o tempo de primeira chegada de um sismógrafo — o tipo de processamento que antecede, e alimenta, a interpretação geológica estrutural feita pelo Geology AI.

## 1. Arquitetura do sistema

```
┌──────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                │
│  Next.js + TypeScript · MapLibre GL JS · gráficos SVG                │
│  Mapa de estações/sondagens/linhas · perfil gravimétrico ·           │
│  curva de sondagem elétrica · dromocrônica de refração · Chat        │
└───────────────────────────────┬────────────────────────────────────-┘
                                 │ REST (OpenAPI)
┌───────────────────────────────▼──────────────────────────────────────┐
│                              BACKEND (FastAPI)                       │
│  ┌───────────────┐   ┌────────────────────┐   ┌────────────────────┐│
│  │  API Layer     │   │  Agent Layer        │   │  Auth/Levantamentos││
│  │  routers/*.py  │──▶│  agent/orchestrator  │   │  users, orgs, RBAC ││
│  └───────────────┘   │  agent/tools.py      │   └────────────────────┘│
│                        └──────────┬───────────┘                       │
│  ┌────────────────────────────────▼──────────────────────────────┐  │
│  │  Processing Layer (determinística, testável, sem LLM)          │  │
│  │  geophysics/gravity_reduction.py · geophysics/magnetic_rtp.py   │  │
│  │  geophysics/resistivity_sounding.py                             │  │
│  │  geophysics/seismic_refraction.py · geophysics/anomaly_detection│  │
│  │  geophysics/stats.py                                            │  │
│  └───────────────────────────────┬──────────────────────────────-┘  │
│  ┌────────────────────────────────▼──────────────────────────────┐  │
│  │  Jobs assíncronos — Celery + Redis                              │  │
│  └───────────────────────────────┬──────────────────────────────-┘  │
└────────────────────────────────────┼──────────────────────────────────┘
        ┌────────────────────────────┼───────────────────────────────┐
        ▼                            ▼                                ▼
┌───────────────┐          ┌──────────────────┐            ┌───────────────────┐
│ PostgreSQL     │          │ Object Storage     │            │ Model registry     │
│ + PostGIS      │          │ (S3-compatible)    │            │ (classificação au- │
│ levantamentos, │         │ grades raster        │            │ tomática de fácies │
│ estações       │         │ (GeoTIFF), relató-   │            │ sísmica, inversão  │
│ gravimétricas, │         │ rios                 │            │ 1D/2D/3D completa  │
│ sondagens SEV, │         │                      │            │ — Fase 3)          │
│ linhas sísmicas,│        │                      │            │                    │
│ auditoria      │          │                     │            │                    │
└───────────────┘          └──────────────────┘            └───────────────────┘
```

Princípio central, igual em toda a plataforma: **o LLM não calcula**. Anomalia Bouguer (com suas correções), grade de anomalia magnética reduzida ao polo, curva de resistividade aparente de uma sondagem elétrica, velocidades/profundidade de uma interface de refração sísmica e manchas de anomalia residual delimitadas por z-score são sempre produto de funções determinísticas em `app/geophysics/` — o agente só orquestra as chamadas e interpreta os resultados numéricos já calculados.

### Fluxo de uma consulta em linguagem natural

```
Usuário: "Qual a anomalia Bouguer ao longo do perfil G001-G012? E a SEV-02
          mostra alguma camada condutiva rasa?"
   │
   ▼
1. Agent Layer identifica o levantamento e os dados disponíveis
2. query_postgis()                      → localiza as estações G001..G012 e a SEV-02
3. calculate_bouguer_anomaly()           → (por estação) g_teorico (IGF80) + correção
                                            ar-livre + correção Bouguer simples;
                                            anomalia Bouguer em mGal, SEM correção
                                            de terreno (limitação declarada)
4. calculate_resistivity_sounding()       → curva de resistividade aparente vs.
                                            espaçamento da SEV-02 (Wenner);
                                            profundidade de investigação heurística
5. create_map_layer()                     → estações/sondagens sobrepostas no mapa
6. generate_chart()                         → perfil de anomalia Bouguer; curva de
                                            sondagem (log-log)
7. LLM interpreta os resultados numéricos → resposta com a forma do perfil de
   anomalia (ex.: baixo gravimétrico entre G005-G007) e a resistividade
   aparente da SEV-02 em cada espaçamento, sempre com o método e as
   ressalvas de cada ferramenta (sem correção de terreno; sem inversão 1D)
8. generate_report() (opcional)             → relatório técnico do levantamento
```

## 2. Estrutura de pastas

```
geophysics-ai/
├── docs/ARQUITETURA.md
├── backend/
│   ├── app/
│   │   ├── main.py · config.py · database.py · init_db.py
│   │   ├── models/
│   │   │   ├── survey.py        # Organization, User, GeophysicalSurvey
│   │   │   ├── raster.py        # RasterLayer (bouguer_anomaly|magnetic_anomaly|rtp_anomaly)
│   │   │   ├── gravity.py       # GravityStation
│   │   │   ├── resistivity.py   # ResistivitySounding, ResistivityReading
│   │   │   ├── seismic.py       # SeismicLine, SeismicReading
│   │   │   ├── analysis.py      # AnalysisResult
│   │   │   └── audit.py         # AuditLog, ChatMessage
│   │   ├── schemas/
│   │   ├── routers/
│   │   │   ├── surveys.py             # CRUD de levantamento/estações/sondagens/linhas
│   │   │   ├── field_readings.py      # import/consulta de leituras (SEV/sísmica)
│   │   │   ├── analysis.py · chat.py · reports.py
│   │   ├── geophysics/            # Processing Layer (determinística)
│   │   │   ├── gravity_reduction.py
│   │   │   ├── magnetic_rtp.py
│   │   │   ├── resistivity_sounding.py
│   │   │   ├── seismic_refraction.py
│   │   │   ├── anomaly_detection.py
│   │   │   └── stats.py
│   │   ├── agent/
│   │   │   ├── orchestrator.py
│   │   │   └── tools.py
│   │   ├── workers/celery_app.py
│   │   └── storage/s3_client.py
│   ├── tests/
│   ├── scripts/seed_demo_data.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── page.tsx                      # lista de levantamentos
│   │   └── surveys/[id]/page.tsx         # workspace
│   ├── components/
│   │   ├── SurveyMap.tsx                 # mapa de estações/sondagens/linhas
│   │   ├── GravityPanel.tsx              # perfil de anomalia Bouguer
│   │   ├── MagneticPanel.tsx             # calculadora de RTP (grade sintética/colada)
│   │   ├── ResistivityPanel.tsx          # curva de sondagem elétrica
│   │   ├── SeismicPanel.tsx              # dromocrônica + interpretação de refração
│   │   └── ChatPanel.tsx
│   ├── lib/api.ts
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## 3. Modelo de dados (PostgreSQL + PostGIS)

| Tabela | Campos-chave | Notas |
|---|---|---|
| `organizations` / `users` | — | mesma base multi-tenant/RBAC da plataforma |
| `geophysical_surveys` | id, org_id, name, `boundary GEOMETRY(POLYGON,4326)`, survey_type, created_by | contêiner de trabalho (um levantamento geofísico de campo) — análogo à `GnssNetwork` do GNSS AI/`Reservoir` do Reservoir AI |
| `raster_layers` | id, survey_id, layer_type (`bouguer_anomaly`\|`magnetic_anomaly`\|`rtp_anomaly`), reference_date, pixel_size_m, footprint GEOMETRY(POLYGON,4326) nullable, storage_uri, extra_metadata JSONB | grade regular já processada (GeoTIFF no object storage); `extra_metadata` guarda inclinação/declinação usadas no RTP, densidade usada na redução Bouguer, etc. |
| `gravity_stations` | id, survey_id, code, `geom GEOMETRY(POINT,4326)`, latitude_deg, elevation_m, observed_gravity_mgal | leitura gravimétrica bruta de campo, já amarrada a uma base absoluta — insumo de `gravity_reduction.py` |
| `resistivity_soundings` | id, survey_id, code, `geom GEOMETRY(POINT,4326)`, array_type (`wenner`\|`schlumberger`) | um ponto de sondagem elétrica vertical (SEV) |
| `resistivity_readings` | id, sounding_id, spacing_m (Wenner) \| current_spacing_m+potential_spacing_m (Schlumberger), voltage_v, current_ma | uma leitura (um espaçamento) da SEV — insumo de `resistivity_sounding.py` |
| `seismic_lines` | id, survey_id, code, `geom GEOMETRY(LINESTRING,4326)` | um alinhamento (spread) de refração sísmica |
| `seismic_readings` | id, line_id, offset_m, first_arrival_time_ms, is_direct_wave (nullable) | uma leitura de primeira chegada — insumo de `seismic_refraction.py`; `is_direct_wave` vem da leitura do sismograma pelo intérprete de campo |
| `analysis_results` | id, survey_id (nullable), result_type (`gravity_reduction`\|`magnetic_rtp`\|`resistivity_sounding`\|`seismic_refraction`\|`anomaly_detection`), entity_ids[], params JSONB, stats JSONB, confidence, created_at | versionado — nunca recalculado silenciosamente. `survey_id` é nulo para análises "avulsas" (RTP/detecção de anomalia sobre uma grade colada diretamente, sem estação/sondagem cadastrada) |
| `audit_log` / `chat_messages` | — | mesma estrutura da plataforma |

## 4. APIs (REST, documentada em OpenAPI)

```
POST   /api/v1/surveys                                            Cadastrar levantamento (boundary GeoJSON, survey_type)
GET    /api/v1/surveys
GET    /api/v1/surveys/{id}
GET    /api/v1/surveys/{id}/export?format=geojson|csv

POST   /api/v1/surveys/{id}/gravity-stations                       Cadastrar estação gravimétrica (code, lon/lat, latitude_deg, elevation_m, observed_gravity_mgal)
GET    /api/v1/surveys/{id}/gravity-stations
POST   /api/v1/surveys/{id}/gravity-stations/import                 Upload em lote (CSV)

POST   /api/v1/surveys/{id}/resistivity-soundings                   Cadastrar sondagem (code, lon/lat, array_type)
GET    /api/v1/surveys/{id}/resistivity-soundings
POST   /api/v1/resistivity-soundings/{sounding_id}/readings/import   Upload de leituras em lote (CSV)
GET    /api/v1/resistivity-soundings/{sounding_id}/readings

POST   /api/v1/surveys/{id}/seismic-lines                           Cadastrar linha (code, coordinates LineString)
GET    /api/v1/surveys/{id}/seismic-lines
POST   /api/v1/seismic-lines/{line_id}/readings/import                Upload de leituras de 1ª chegada em lote (CSV)
GET    /api/v1/seismic-lines/{line_id}/readings

GET    /api/v1/analysis/{result_id}                                Resultado de análise já calculado, na íntegra
POST   /api/v1/analysis/bouguer-anomaly                              {station_id, density_kg_m3?}
POST   /api/v1/analysis/magnetic-rtp                                 {grid[][], pixel_size_m, inclination_deg, declination_deg, inclination_magnetization_deg?, declination_magnetization_deg?}
POST   /api/v1/analysis/resistivity-sounding                         {sounding_id}
POST   /api/v1/analysis/seismic-refraction                           {line_id}
POST   /api/v1/analysis/anomaly-detection                            {grid[][], threshold_sigma?, direction?, pixel_size_m?}

POST   /api/v1/surveys/{id}/chat                                    {message} → resposta do agente
GET    /api/v1/surveys/{id}/chat/history

POST   /api/v1/reports/generate                                   {survey_id, result_id, format}
GET    /api/v1/reports/{survey_id}/download
```

Toda resposta de análise inclui `{method, parameters, uncertainty_note, limitations, processed_at}` (os quatro primeiros vêm de `method_metadata()` em cada módulo de `app/geophysics/`; `processed_at` é o timestamp de criação do `AnalysisResult` persistido).

## 5. Funções principais (ferramentas do agente)

```python
calculate_bouguer_anomaly(station_id: str, density_kg_m3: float = 2670.0) -> BouguerAnomalyResult
    # g_teorico: Formula Internacional da Gravidade 1980 (IGF80/GRS80, Moritz 1980)
    # FAC = 0.3086*h [mGal]; BC = 0.04193*rho[g/cm3]*h [mGal] (placa de Bouguer, SEM terreno)
    # anomalia_bouguer = g_observado - g_teorico + FAC - BC

calculate_magnetic_rtp(grid: list[list[float]], pixel_size_m: float,
                        inclination_deg: float, declination_deg: float,
                        inclination_magnetization_deg: float | None = None,
                        declination_magnetization_deg: float | None = None) -> MagneticRtpResult
    # filtro espectral (FFT 2D, Blakely 1995): H_rtp(kx,ky) = 1/(Theta_f*Theta_m);
    # torna a anomalia simetrica e centrada sobre a fonte (assume magnetizacao
    # induzida quando a remanencia nao e informada)

calculate_resistivity_sounding(sounding_id: str) -> ResistivitySoundingResult
    # Wenner: rho_a = 2*pi*a*(V/I); Schlumberger: rho_a = pi*((L/2)^2-(l/2)^2)/l*(V/I)
    # (Telford et al. 1990); curva de resistividade aparente vs. espacamento,
    # profundidade de investigacao heuristica (a/2 Wenner, L/4 Schlumberger)

interpret_seismic_refraction(line_id: str) -> SeismicRefractionResult
    # metodo da distancia de cruzamento (Kearey, Brooks & Hill, 2002): V1,V2 por
    # minimos quadrados de cada ramo da dromocronica; depth=(x_cross/2)*sqrt((V2-V1)/(V2+V1))

detect_anomalies(grid: list[list[float]], threshold_sigma: float = 2.0,
                  direction: str = "both", pixel_size_m: float = 1.0) -> AnomalyDetectionResult
    # z-score = (grid-media)/desvio_padrao; scipy.ndimage.label extrai componentes
    # conexos como corpos-fonte candidatos; centroide/area/valor medio/pico por mancha

query_postgis(survey_id: str, filters: dict) -> dict
create_map_layer(result_id: str) -> MapLayer
generate_chart(result_id: str, chart_type: str) -> ChartSpec
generate_report(survey_id: str, result_id: str | None, format: str) -> ReportFile
```

### Redução Bouguer: por que a correção de terreno fica de fora do MVP, de forma declarada

`geophysics/gravity_reduction.py` aplica a cadeia clássica de correção — gravidade teórica pela Fórmula Internacional da Gravidade 1980 (IGF80), correção ar-livre (`0.3086*h`) e correção Bouguer simples (`0.04193*rho*h`, placa de Bouguer infinita) — mas **não** calcula a correção de terreno completa (que soma de volta massa "faltante" em vales e subtrai excesso de massa em morros ao redor de cada estação). Essa correção exige um DEM de alta resolução ao redor de cada estação e um algoritmo de integração de massa (ex.: templates de Hammer, 1939) — infraestrutura de processamento raster fora do escopo desta versão. A limitação é reportada explicitamente em todo resultado (`limitations`), nunca escondida: em terreno com relevo acentuado, a anomalia Bouguer simples subestima sistematicamente o efeito geológico de interesse.

### RTP: por que o filtro é reversível e por que ele "explode" perto do equador magnético

`geophysics/magnetic_rtp.py` aplica o filtro clássico de fase/amplitude no domínio do número de onda (Blakely, 1995): a mesma anomalia, vista sob um campo magnético inclinado, aparece deslocada e assimétrica em relação à fonte real; o filtro de RTP desfaz essa distorção geométrica simulando como a anomalia apareceria sob um campo vertical (polo). O teste do módulo (`tests/test_magnetic_rtp.py`) demonstra essa propriedade de forma verificável: uma anomalia simétrica conhecida é deliberadamente "distorcida" pelo operador recíproco do RTP (simulando a observação sob campo inclinado) e então processada por `reduce_to_pole` — o resultado recupera a simetria original e o pico exatamente sobre a posição da fonte, com uma diferença de simetria residual da ordem de `1e-7` (o piso numérico da FFT), contra ~60% de assimetria na anomalia não corrigida. O operador tem no denominador um termo proporcional a `sin(inclinação)` — perto do equador magnético (inclinação baixa) esse termo se aproxima de zero e o filtro amplifica desproporcionalmente o ruído de alta frequência; o módulo apenas **sinaliza** essa condição (`low_inclination_warning`), sem aplicar uma correção estabilizada de baixa latitude (RTP pseudo-inclinado), que fica para uma fase posterior.

### Resistividade aparente: por que não há inversão de camadas no MVP

`geophysics/resistivity_sounding.py` calcula a resistividade aparente exata para cada leitura (Wenner ou Schlumberger, os dois fatores geométricos clássicos de Telford et al., 1990) e monta a curva de sondagem vs. espaçamento — mas **não** inverte essa curva para um modelo de terra em camadas (espessura + resistividade por camada), o que exigiria um algoritmo de otimização não-linear sobre uma função de sensibilidade de Fréchet dependente do próprio modelo (um problema clássico de não-unicidade em geofísica de potencial). A "profundidade de investigação" reportada é uma regra heurística amplamente citada (`a/2` para Wenner, `L/4` para Schlumberger) — uma referência aproximada de escala, nunca uma profundidade de interface geológica confirmada; o módulo é explícito sobre essa distinção em todo resultado.

### Refração sísmica: por que o modelo assume exatamente 2 camadas horizontais

`geophysics/seismic_refraction.py` usa o método clássico da distância de cruzamento — um método fechado (sem iteração) que funciona porque a suposição de 2 camadas horizontais planas torna a dromocrônica exatamente linear em 2 ramos (direto e refratado crítico). O módulo é testado gerando dados sintéticos **a partir de** V1/V2/profundidade conhecidos (pelas equações padrão de tempo de trânsito), depois verificando que a interpretação recupera esses mesmos valores dentro de uma tolerância pequena (`tests/test_seismic_refraction.py`) — incluindo um teste com ruído gaussiano realista no tempo de leitura. Mergulho de interface (dip), uma terceira camada oculta (camada de baixa velocidade) e o método de tempo-intercepto generalizado (GRM) para geometrias mais complexas ficam fora do escopo — o módulo reporta duas estimativas independentes de profundidade (via distância de cruzamento e via tempo de intercepto) exatamente para que o usuário detecte, pela divergência entre elas, quando a suposição de 2 camadas simples pode não ser adequada.

### Detecção de anomalias: triagem estatística, não classificação geológica

`geophysics/anomaly_detection.py` aplica um limiar de z-score seguido de `scipy.ndimage.label` (o mesmo padrão já usado no Radar AI para detecção de mudança e no Geology AI para anomalia espectral) a uma grade de anomalia residual (Bouguer ou RTP). O módulo é deliberadamente uma ferramenta de **triagem**: aponta onde a grade se desvia estatisticamente do próprio fundo, nunca o que causa essa anomalia — não estima profundidade, forma ou natureza litológica do corpo-fonte (isso exigiria modelagem/inversão direta, fora do escopo). O teste do módulo usa uma grade sintética com duas anomalias gaussianas de sinal oposto sobre ruído de fundo conhecido, verificando que a rotulagem de componentes conexos recupera o número, centroide e sinal corretos de cada mancha.

## 6. Interface inicial

- **Mapa do levantamento**: estações gravimétricas, sondagens elétricas e linhas sísmicas sobre o mapa base, coloridas por tipo; clique num elemento para selecioná-lo nos painéis de análise.
- **Painel de Gravimetria**: perfil de anomalia Bouguer ao longo das estações selecionadas (gráfico SVG), com a decomposição g_teórico/FAC/BC visível por estação.
- **Painel de Magnetometria**: calculadora de RTP — cola/edita uma grade pequena (ou usa uma grade sintética de exemplo), define inclinação/declinação, mostra a grade observada e a grade reduzida ao polo lado a lado.
- **Painel de Eletrorresistividade**: curva de resistividade aparente vs. espaçamento (escala log-log) de uma sondagem selecionada, com a profundidade de investigação heurística marcada.
- **Painel de Sísmica de Refração**: dromocrônica (tempo vs. offset) de uma linha selecionada, com os dois ramos ajustados sobrepostos e o resultado (V1, V2, profundidade, ângulo crítico).
- **Chat GeoAI**: pergunta em linguagem natural, tool calls transparentes.
- **Exportação**: GeoJSON, CSV.

## 7. Definição do MVP funcional

1. Cadastro de levantamento (boundary/área, tipo) e de estações gravimétricas, sondagens elétricas e linhas sísmicas (código, coordenadas geográficas).
2. Cadastro/importação em lote (CSV) de leituras de campo: leitura gravimétrica + latitude + elevação por estação; tensão/corrente/espaçamento por leitura de SEV; offset/tempo de primeira chegada por leitura sísmica.
3. Redução Bouguer simples (gravidade teórica IGF80 + correção ar-livre + correção Bouguer simples) por estação, com densidade crustal configurável — SEM correção de terreno (limitação documentada).
4. Redução ao polo (RTP) de uma grade de anomalia magnética via filtro espectral (FFT), a partir de inclinação/declinação informadas.
5. Curva de resistividade aparente vs. espaçamento (Wenner e Schlumberger) a partir de leituras de campo, com profundidade de investigação heurística.
6. Interpretação de refração sísmica de 2 camadas pelo método da distância de cruzamento, recuperando V1, V2, ângulo crítico e profundidade da interface.
7. Detecção de manchas anômalas (candidatas a corpo-fonte) numa grade residual por limiar de z-score e componentes conexos.
8. Chat com agente capaz de orquestrar as chamadas acima — o `SYSTEM_PROMPT` proíbe explicitamente inventar anomalias, valores de RTP, resistividades, velocidades/profundidades sísmicas ou manchas anômalas.
9. Exportação em GeoJSON/CSV.

Fora do escopo do MVP: leitura/parsing de formatos brutos proprietários de instrumento (ex.: arquivos binários de gravímetro CG-5, magnetômetro, resistivímetro ou sismógrafo multicanal — o MVP consome leituras já digitalizadas, sintéticas ou importadas via CSV), correção de terreno gravimétrica completa (templates de Hammer/integração sobre DEM), inversão 1D/2D/3D completa de qualquer método (resistividade em camadas, sísmica tomográfica, gravimetria/magnetometria 3D), classificação automática de fácies sísmicas e modelos de aprendizado de máquina (Fase 3), correção de maré terrestre e deriva instrumental do gravímetro (assume-se leitura já corrigida), método de tempo-intercepto generalizado (GRM) e detecção de mergulho de camada em refração sísmica, RTP estabilizado de baixa latitude (pseudo-inclinado), geração automática de relatório PDF/DOCX, autenticação multi-tenant completa. O MVP roda com um gerador de dados simulados (`backend/scripts/seed_demo_data.py`) cuja gravimetria, sondagens elétricas e linhas sísmicas são construídas a partir de parâmetros "verdadeiros" conhecidos — permitindo verificar, a cada demonstração, que os módulos determinísticos recuperam esses parâmetros dentro do ruído injetado.
