import os
import tempfile
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Module imports
from audio_engine import transcribe_patient_audio, speak_question_to_patient
from dialogue_manager import ask_follow_up
from ayush_engine import get_next_ayush_question, summarize_ayush_profile
from vlm_extractor import extract_from_prescription_image
from document_extractor import extract_document_entities
from summarizer import generate_clinical_summary

# --- FastAPI App Configuration ---
app = FastAPI(
    title="MediKiosk Clinical AI Engine",
    description="Offline-capable bilingual clinical intake backend supporting Allopathy & AYUSH workflows",
    version="1.0.0"
)

# Enable CORS for local network and frontend team connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())

class DialogueTurnRequest(BaseModel):
    user_id: str = "PATIENT_001"
    session_id: str = "SESS_101"
    language: str = "en"  # "en" or "hi"
    conversation_history: List[ChatMessage]

class SummaryRequest(BaseModel):
    user_id: str = "PATIENT_001"
    session_id: str = "SESS_101"
    conversation_history: List[ChatMessage]
    document_data: Optional[Dict[str, Any]] = None

class AyushTurnRequest(BaseModel):
    user_id: str = "PATIENT_001"
    session_id: str = "SESS_101"
    conversation_history: List[ChatMessage]

# --- Health & Diagnostic Routes ---
@app.get("/")
def root():
    return {
        "status": "online",
        "service": "MediKiosk Clinical AI Backend",
        "modules_loaded": [
            "audio_engine",
            "dialogue_manager",
            "ayush_engine",
            "vlm_extractor",
            "document_extractor",
            "summarizer"
        ]
    }


# --- 1. Speech & Dialogue Endpoints ---
@app.post("/api/intake/audio-turn")
async def process_audio_turn(
        audio_file: UploadFile = File(...),
        language: Optional[str] = Form(None)
):
    """
    Accepts audio (.wav/.webm/.mp3), transcribes with Whisper, and returns transcript and detected language.
    """
    suffix = os.path.splitext(audio_file.filename)[-1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio_file.read())
        tmp_path = tmp.name

    try:
        transcript, resolved_lang = transcribe_patient_audio(tmp_path, language=language)
        return {
            "transcript": transcript,
            "language": resolved_lang
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ASR error: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/api/intake/dialogue-turn")
def process_dialogue_turn(payload: DialogueTurnRequest):
    """
    Takes running conversation history with user/session IDs
    and returns the next SOCRATES turn stamped with session metadata.
    """
    try:
        # Pass conversation history to Qwen
        history_dicts = [{"role": msg.role, "content": msg.content} for msg in payload.conversation_history]
        turn_data = ask_follow_up(history_dicts, language=payload.language)

        # Echo back session context for frontend tracking
        turn_data["user_id"] = payload.user_id
        turn_data["session_id"] = payload.session_id
        turn_data["timestamp"] = datetime.utcnow().isoformat()

        return turn_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dialogue manager error: {str(e)}")


# --- 2. AYUSH Intake Endpoints ---
@app.post("/api/intake/ayush-turn")
def process_ayush_turn(payload: AyushTurnRequest):
    """
    Generates next adaptive Dashavidha Pariksha / Ahara-Vihara question for AYUSH clinics.
    """
    try:
        history_dicts = [{"role": msg.role, "content": msg.content} for msg in payload.conversation_history]
        return get_next_ayush_question(history_dicts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AYUSH engine error: {str(e)}")


@app.post("/api/intake/ayush-summary")
def process_ayush_summary(payload: AyushTurnRequest):
    """
    Generates structured Agni, Koshtha, and Dosha clinical evaluation.
    """
    try:
        history_dicts = [{"role": msg.role, "content": msg.content} for msg in payload.conversation_history]
        return summarize_ayush_profile(history_dicts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AYUSH summary error: {str(e)}")


# --- 3. Document Extraction Endpoints ---
@app.post("/api/document/extract-image")
async def extract_prescription_image(image_file: UploadFile = File(...)):
    """
    Direct Vision LLM processing of prescription or lab slip photos.
    """
    suffix = os.path.splitext(image_file.filename)[-1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await image_file.read())
        tmp_path = tmp.name

    try:
        extracted = extract_from_prescription_image(tmp_path)
        return extracted
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision extraction error: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/api/document/extract-text")
def extract_ocr_text(payload: TextOCRRequest):
    """
    Fast entity extraction from OCR strings (diagnoses, medications, abnormal lab values).
    """
    try:
        return extract_document_entities(payload.raw_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR entity extraction error: {str(e)}")


# --- 4. Synthesis & Physician Report Endpoint ---
@app.post("/api/intake/synthesize")
def synthesize_intake_report(payload: SummaryRequest):
    """
    Synthesizes interview into doctor-ready brief stamped with patient and session IDs.
    """
    try:
        history_dicts = [{"role": msg.role, "content": msg.content} for msg in payload.conversation_history]
        summary = generate_clinical_summary(history_dicts)

        if payload.document_data:
            summary["attached_records"] = payload.document_data

        # Attach metadata for EHR record storage
        summary["user_id"] = payload.user_id
        summary["session_id"] = payload.session_id
        summary["generated_at"] = datetime.utcnow().isoformat()

        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Synthesis error: {str(e)}")


# --- Execution Entrypoint ---
if __name__ == "__main__":
    print("\n=======================================================")
    print("       MediKiosk Central Backend Initialized           ")
    print("=======================================================")
    print("FastAPI docs will be available at: http://0.0.0.0:8000/docs")

    # Host bound to 0.0.0.0 so teammates on the same local network can access via IP
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)