from fastapi import APIRouter
from pydantic import BaseModel

from services.history import process_answer

router = APIRouter(
    prefix="/history",
    tags=["Backend-A"]
)


class HistoryAnswer(BaseModel):
    session_id: str
    question_id: str
    transcript: str
    language: str


@router.post("/answer")
async def receive_answer(data: HistoryAnswer):

    result = await process_answer(
        data.session_id,
        data.question_id,
        data.transcript,
        data.language
    )

    return result