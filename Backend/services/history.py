import logging

from services.ai_service import process_symptom

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def process_answer(
    user_id,
    session_id,
    language,
    conversation_history
):
    logger.info(
        "Processing conversation: user_id=%s, session_id=%s",
        user_id,
        session_id
    )

    try:
        ai_result = await process_symptom(
            user_id,
            session_id,
            language,
            conversation_history
        )

        logger.info(
            "AI processing successful: user_id=%s, session_id=%s",
            user_id,
            session_id
        )

    except Exception as e:
        logger.exception(
            "AI processing failed: user_id=%s, session_id=%s",
            user_id,
            session_id
        )

        return {
            "status": "ai_error",
            "error_type": type(e).__name__,
            "error": str(e)
        }

    return {
        "user_id": user_id,
        "session_id": session_id,
        "language": language,
        "conversation_history": conversation_history,
        "ai_result": ai_result
    }