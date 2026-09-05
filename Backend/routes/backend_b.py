from fastapi import APIRouter
from services.ai_service import process_symptom

router = APIRouter(
    prefix="/backend-b",
    tags=["Backend-B"]
)

@router.post("/test-ai")
async def test_ai(data: dict):
    result = await process_symptom(
        data["text"],
        data["language"]
    )

    return result