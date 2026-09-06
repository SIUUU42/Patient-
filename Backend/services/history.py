import logging
from services.ai_service import process_symptom
#from services.database_service import save_history
#from services.backend_a_service import send_result_to_backend_a

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def process_answer(session_id, question_id, transcript, language):

    logger.info(
        "Processing transcript: session_id=%s, question_id=%s",
        session_id,
        question_id
    )

    try:
        ai_result = await process_symptom(
            transcript,
            language
        )

        logger.info(
            "AI processing successful: session_id=%s, question_id=%s",
            session_id,
            question_id
        )

    except Exception as e:
        logger.exception(
    "AI processing failed: session_id=%s, question_id=%s",
    session_id,
    question_id
)

    # 2. Prepare complete history result
    result = {
        "session_id": session_id,
        "question_id": question_id,
        "transcript": transcript,
        "language": language,
        "ai_result": ai_result
    }

    # Database — enable when database service is available
    #
    # database_result = await save_timeline_event(
    #     event_id=f"{session_id}-{question_id}",
    #     patient_id=session_id,
    #     event_type="INTAKE_NOTE",
    #     title="Patient History transcript",
    #     summary_data={
    #         "question_id": question_id,
    #         "transcript": transcript,
    #         "ai_result": ai_result
    #     }
    # )

    # 4. Send processed result to Backend-A
    #await send_result_to_backend_a(result)

    # 5. Return result to Backend-A / caller
    #return result