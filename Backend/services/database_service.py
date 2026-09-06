import httpx

DATABASE_SERVICE_URL = ""


async def save_timeline_event(
    event_id,
    patient_id,
    event_type,
    title,
    summary_data
):
    async with httpx.AsyncClient() as client:

        response = await client.post(
            f"{DATABASE_SERVICE_URL}/api/patient/timeline/event",
            json={
                "event_id": event_id,
                "patient_id": patient_id,
                "event_type": event_type,
                "title": title,
                "summary_data": summary_data
            }
        )

        response.raise_for_status()

        return response.json()