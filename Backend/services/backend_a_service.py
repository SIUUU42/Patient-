import httpx


BACKEND_A_URL = "http://127.0.0.1:8000/history/result"


async def send_result_to_backend_a(data):

    async with httpx.AsyncClient(timeout=30.0) as client:

        response = await client.post(
            BACKEND_A_URL,
            json=data
        )

        response.raise_for_status()

        return response.json()