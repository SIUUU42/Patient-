import json
import re
import ollama
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="MediKiosk AI Engine",
    description="Offline-capable clinical intake backend",
    version="1.0.0"
)

# Enable CORS for external frontends/tunnels
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_NAME = "qwen3.5:4b"

# Request Schemas
class SymptomRequest(BaseModel):
    transcript: str
    language: str = "hi"

class SynthesisRequest(BaseModel):
    dialogue_transcript: str
    document_data: dict = {}

# Helpers
def clean_and_parse_json(raw_text: str) -> dict:
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError(f"Could not parse valid JSON from output:\n{raw_text}")


@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "MediKiosk AI Engine",
        "model": MODEL_NAME
    }


@app.post("/api/intake/dialogue")
def process_dialogue(payload: SymptomRequest):
    """Processes patient speech/text and generates the next follow-up question."""
    system_prompt = """
    You are the MediKiosk clinical intake assistant.
    Analyze the patient's complaint and provide the next follow-up question following the SOCRATES framework.

    Return ONLY a JSON object matching this schema:
    {
      "corrected_complaint": "Standard clinical English description",
      "follow_up_question": "Next question in patient's language",
      "suggested_options": ["Option 1", "Option 2", "Option 3", "Option 4"]
    }
    """
    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Language: {payload.language}\nPatient statement: {payload.transcript}"}
            ]
        )
        return clean_and_parse_json(response["message"]["content"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/intake/synthesize")
def synthesize_encounter(payload: SynthesisRequest):
    """Merges dialogue and scanned document entities into a final physician summary."""
    synthesis_prompt = """
    You are the Chief Clinical Intake Engine.
    Synthesize the dialogue history and any scanned document records into a single physician-ready consultation brief.

    Return ONLY a JSON object matching this schema:
    {
      "triage_priority": "Routine | Priority | Emergency",
      "chief_complaint": "1-line summary",
      "history_of_present_illness": "Chronological HPI following SOCRATES details",
      "active_medications": ["Drug names and doses"],
      "physician_brief": "2-sentence executive summary for doctor"
    }
    """
    context = f"""
    TRANSCRIPT:
    {payload.dialogue_transcript}

    DOCUMENT DATA:
    {json.dumps(payload.document_data, indent=2)}
    """
    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": synthesis_prompt},
                {"role": "user", "content": context}
            ]
        )
        return clean_and_parse_json(response["message"]["content"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))