from fastapi import APIRouter

from services.history import process_answer
from services.schemas import Histories

router = APIRouter(
    prefix="/history",
    tags=["Backend-A"]
)


@router.post("/answer")
async def receive_answer(data: Histories):
    try:
        result = await process_answer(
            data.user_id,
            data.session_id,
            data.language,
            data.conversation_history
        )

        return result

    except Exception as e:
        return {
            "status": "backend_a_error",
            "error_type": type(e).__name__,
            "error": str(e)
        }