import httpx

AI_SERVICE_URL = "YOUR_AI_GUY_URL"

async def process_symptom(text, language):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/api/process-symptom",
            json={
                "text": text,
                "language": language
            }
        )

        response.raise_for_status()
        return response.json()