from fastapi import APIRouter
from fastapi import APIRouter, UploadFile, File
from services.database_service import test_database
from services.ocr_service import process_document
from services.history import process_answer

router = APIRouter(
    prefix="/backend-b",
    tags=["Backend-B"]
)


@router.post("/test-ai")
async def test_ai(data: dict):
    try:
        result = await process_answer(
            data["user_id"],
            data["session_id"],
            data["language"],
            data["conversation_history"]
        )

        return result

    except Exception as e:
        return {
            "status": "backend_b_error",
            "error_type": type(e).__name__,
            "error": str(e)
        }

@router.post("/ocr")
async def ocr_document(file: UploadFile = File(...)):
    try:
        result = await process_document(file)
        return result

    except Exception as e:
        return {
            "status": "backend_b_error",
            "error_type": type(e).__name__,
            "error": str(e)
        }

@router.post("/test-db")
async def test_db():
    try:
        result = await test_database()

        return {
            "status": "success",
            "database": result
        }

    except Exception as e:
        return {
            "status": "database_error",
            "error_type": type(e).__name__,
            "error": str(e)
        }