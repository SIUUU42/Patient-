import httpx

DATABASE_SERVICE_URL = "https://gruffly-divisible-tarnish.ngrok-free.dev/docs#/"


async def test_database():
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{DATABASE_SERVICE_URL}/api/ai/save-summary",
            json={
                "patient_id": "U001",
                "chief_complaint": "Test complaint",
                "hpi": "Backend database connectivity test",
                "past_meds": "None",
                "lab_anomalies": "None",
                "is_emergency": False,
                "emergency_reason": ""
            }
        )

        return {
            "db_status_code": response.status_code,
            "db_response": response.json()
        }