import httpx

AI_SERVICE_URL = "http://10.79.50.109:8000"


async def process_symptom(
    user_id,
    session_id,
    language,
    conversation_history
):
    async with httpx.AsyncClient(timeout=600.0) as client:

        response = await client.post(
            f"{AI_SERVICE_URL}/api/intake/dialogue-turn",
            json={
                "user_id": user_id,
                "session_id": session_id,
                "language": language,
                "conversation_history": [
                    message.model_dump()
                    for message in conversation_history
                ]
            }
        )

        return {
            "ai_status_code": response.status_code,
            "ai_response": response.json()
        }