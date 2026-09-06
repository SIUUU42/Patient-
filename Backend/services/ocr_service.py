import httpx

AI_SERVICE_URL = "http://10.79.50.109:8000"


async def process_document(file):
    file_bytes = await file.read()

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/api/document/extract-image",
            files={
                "image_file": (
                    file.filename,
                    file_bytes,
                    file.content_type or "image/jpeg"
                )
            }
        )

        return {
            "ai_status_code": response.status_code,
            "ai_response": response.json()
        }