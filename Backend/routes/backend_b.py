from fastapi import APIRouter
from services.history import process_symptom

router = APIRouter(
    prefix="/backend-b",
    tags=["Backend-B"]
)

@router.post("/test-ai")
async def test_ai(data: dict):
        try:
            result = await process_symptom(
            data["transcript"],
            data["language"]
        )
            return result

        except Exception as e:
               return {
            "status": "backend_b_error",
            "error_type": type(e).__name__,
            "error": str(e)
        }
    



