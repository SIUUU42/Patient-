from services.ai_service import process_symptom
#from services.database_service import save_history
#from services.backend_a_service import send_result_to_backend_a


async def process_answer(session_id, question_id, answer):

    # 1. Send answer to AI
    ai_result = await process_symptom(answer)

    # 2. Prepare complete history result
    result = {
        "session_id": session_id,
        "question_id": question_id,
        "answer": answer,
        "ai_result": ai_result
    }

    # Database — enable when database service is available
    #
    # database_result = await save_timeline_event(
    #     event_id=f"{session_id}-{question_id}",
    #     patient_id=session_id,
    #     event_type="INTAKE_NOTE",
    #     title="Patient History Answer",
    #     summary_data={
    #         "question_id": question_id,
    #         "answer": answer,
    #         "ai_result": ai_result
    #     }
    # )

    # 4. Send processed result to Backend-A
    #await send_result_to_backend_a(result)

    # 5. Return result to Backend-A / caller
    #return result