import httpx

BACKEND_A_URL = "https://abc123.ngrok-free.app/history/result"


async def send_to_backend_a(data):

    async with httpx.AsyncClient() as client:

        response = await client.post(
            BACKEND_A_URL,
            json=data
        )

        response.raise_for_status()

        return response.json()