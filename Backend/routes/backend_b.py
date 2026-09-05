from fastapi import APIRouter
from pydantic import BaseModel
from services.schemas import Histories

router = APIRouter(prefix="/backend-b", tags=["Rudra"])



@router.post("/history/answer")
async def receive_answer(request: Histories):
    return {
        "session_id": request.session_id,
        "question_id": request.question_id,
        "answer": request.answer
    }