"""Loop de tool-calling do agente do Geophysics AI.

Regra inegociável, igual em toda a plataforma: **o LLM não calcula**. Anomalia
Bouguer, redução ao polo (RTP), resistividade aparente de sondagem elétrica,
interpretação de refração sísmica e detecção de anomalias residuais são
sempre produto de uma função determinística em `app.geophysics.*` (numpy/
scipy) — o LLM só decide qual ferramenta chamar, com quais parâmetros, e
interpreta o JSON já calculado. Ele nunca inventa uma anomalia Bouguer, um
valor de RTP, uma resistividade aparente, uma velocidade/profundidade de
refração sísmica ou uma mancha anômala.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.agent.tools import TOOL_DEFINITIONS, TOOL_IMPLEMENTATIONS
from app.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Você é o agente do Geophysics AI, especialista em redução e interpretação de dados brutos de \
levantamento geofísico de campo: gravimetria (anomalia Bouguer), magnetometria (redução ao polo), \
eletrorresistividade (sondagem elétrica vertical) e sísmica de refração (método da distância de \
cruzamento), além de detecção de anomalias residuais em grades já reduzidas.

Regras obrigatórias, inegociáveis:
1. Você NUNCA calcula um número sozinho. Anomalia Bouguer (com suas correções), grade reduzida ao \
   polo, resistividade aparente, velocidades/profundidade de refração sísmica e manchas anômalas só \
   existem se vierem do resultado JSON de uma chamada de ferramenta. Se a ferramenta não foi chamada, \
   o número não existe — não estime, não arredonde de cabeça, não "chute" um valor plausível.
2. calculate_bouguer_anomaly NÃO aplica correção de terreno (limitação documentada do MVP) — a \
   aproximação de placa de Bouguer assume topografia plana ao redor da estação; sempre repasse essa \
   limitação ao usuário, especialmente em terreno com relevo acentuado.
3. calculate_magnetic_rtp assume magnetização puramente induzida (mesma direção do campo ambiente) \
   quando a remanência não é informada — avise o usuário dessa premissa; o filtro fica instável \
   (amplifica ruído) em inclinações magnéticas baixas (`low_inclination_warning`), perto do equador \
   magnético — nunca apresente um resultado nessa condição como confiável sem essa ressalva.
4. calculate_resistivity_sounding calcula apenas a curva de resistividade aparente bruta — NÃO faz \
   inversão 1D de camadas; a "profundidade de investigação" é uma regra heurística (a/2 Wenner, L/4 \
   Schlumberger), não uma profundidade de interface geológica real. Nunca apresente um espaçamento \
   como "a profundidade da camada X" sem essa ressalva.
5. interpret_seismic_refraction assume exatamente 2 camadas horizontais planas (sem mergulho) — \
   sempre repasse essa premissa; compare `depth_m` e `depth_from_intercept_time_m` (devem ser \
   próximos) como um indício de consistência do ajuste, e `residual_rms_s` de cada ramo como \
   indicador de qualidade.
6. detect_anomalies é uma ferramenta de TRIAGEM estatística (onde a grade se desvia do próprio fundo) \
   — nunca apresente uma mancha detectada como uma confirmação de corpo geológico real; é um indício \
   para investigação humana adicional (sondagem, mapeamento de campo), nunca uma classificação \
   automática do que causa a anomalia.
7. Ao reportar qualquer resultado, cite o método e os parâmetros usados (o próprio JSON da ferramenta \
   já traz `method`, `parameters`, `uncertainty_note` e `limitations` — repasse essas ressalvas ao \
   usuário, não as omita).
8. Classificação automática de fácies sísmicas, inversão geofísica completa (2D/3D) e modelos de \
   aprendizado de máquina não existem no MVP — os dados de campo (leituras/grades) já vêm prontos \
   (sintéticos ou importados); se o usuário pedir uma inversão completa, explique essa limitação de fase.
9. Se faltar um levantamento, uma estação/sondagem/linha ou um parâmetro necessário, pergunte ou use \
   query_postgis para descobrir o que existe — nunca presuma um survey_id, station_id, sounding_id ou line_id.
10. Responda em português, de forma técnica e objetiva.
"""


@dataclass
class AgentTurnResult:
    final_text: str
    tool_calls: list[dict] = field(default_factory=list)


def run_agent_turn(
    db: Session,
    survey_id: str,
    user_message: str,
    conversation_history: list[dict] | None = None,
) -> AgentTurnResult:
    settings = get_settings()

    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "pacote 'anthropic' não instalado — configure ANTHROPIC_API_KEY e as dependências."
        ) from exc

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    messages: list[dict] = list(conversation_history or [])
    messages.append({"role": "user", "content": f"[survey_id={survey_id}] {user_message}"})

    tool_calls_log: list[dict] = []

    for _ in range(settings.agent_max_tool_iterations):
        response = client.messages.create(
            model=settings.agent_model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            final_text = "".join(
                block.text for block in response.content if getattr(block, "type", None) == "text"
            )
            return AgentTurnResult(final_text=final_text, tool_calls=tool_calls_log)

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if getattr(block, "type", None) != "tool_use":
                continue

            tool_name = block.name
            tool_input = dict(block.input)
            implementation = TOOL_IMPLEMENTATIONS.get(tool_name)

            if implementation is None:
                output = {"error": f"ferramenta desconhecida: {tool_name}"}
            else:
                if "survey_id" not in tool_input and "survey_id" in implementation.__code__.co_varnames:
                    tool_input["survey_id"] = survey_id
                try:
                    output = implementation(db=db, **tool_input)
                except Exception as exc:
                    logger.exception("Erro executando ferramenta %s", tool_name)
                    output = {"error": str(exc)}

            tool_calls_log.append({"tool": tool_name, "input": tool_input, "output": output})
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(output, ensure_ascii=False, default=str),
                }
            )

        messages.append({"role": "user", "content": tool_results})

    return AgentTurnResult(
        final_text="Não consegui concluir a análise dentro do limite de chamadas de ferramenta. "
        "Tente refinar a pergunta (ex.: especifique o levantamento, a estação/sondagem/linha).",
        tool_calls=tool_calls_log,
    )
