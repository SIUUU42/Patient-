from services.ai_service import extract_information
#from services.database_service import save_history
#from services.backend_a_service import send_result_to_backend_a


async def process_answer(session_id, question_id, answer):

    # 1. Send answer to AI
    ai_result = await extract_information(answer)

    # 2. Prepare complete history result
    result = {
        "session_id": session_id,
        "question_id": question_id,
        "answer": answer,
        "ai_result": ai_result
    }

    # 3. Save result in database
    await save_history(result)

    # 4. Send processed result to Backend-A
    await send_result_to_backend_a(result)

    # 5. Return result to Backend-A / caller
    return result