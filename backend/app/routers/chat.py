import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent.orchestrator import run_agent_turn
from app.database import get_db
from app.models.audit import ChatMessage
from app.schemas.survey import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/v1/surveys/{survey_id}/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(survey_id: uuid.UUID, payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    result = run_agent_turn(db=db, survey_id=str(survey_id), user_message=payload.message)

    db.add(ChatMessage(survey_id=survey_id, role="user", content=payload.message))
    db.add(
        ChatMessage(
            survey_id=survey_id, role="assistant", content=result.final_text, tool_calls={"calls": result.tool_calls}
        )
    )
    db.commit()

    return ChatResponse(reply=result.final_text, tool_calls=result.tool_calls)


@router.get("/history")
def chat_history(survey_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(ChatMessage).filter(ChatMessage.survey_id == survey_id).order_by(ChatMessage.created_at).all()
    return [{"role": r.role, "content": r.content, "created_at": r.created_at.isoformat()} for r in rows]
