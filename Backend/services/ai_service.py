import httpx

AI_SERVICE_URL = "http://10.79.50.109:8000"

async def process_symptom(text, language):
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/api/intake/dialogue",
            json={
                "transcript": text,
                "language": language
            }
        )

        return {"ai_status_code": response.status_code,"ai_response": response.json()}