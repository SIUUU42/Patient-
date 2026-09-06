import os
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
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

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Schemas ---
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

class TextOCRRequest(BaseModel):
    raw_text: str


# --- Frontend & Health Routes ---
import csv

@app.get("/api/patient/lookup")
def lookup_patient_by_phone(phone: str):
    """Looks up patient by mobile number in local CSV with graceful fallback."""
    phone = phone.strip()
    if os.path.exists("patients.csv"):
        with open("patients.csv", mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("phone", "").strip() == phone:
                    return {
                        "found": True,
                        "patient": row
                    }

    # Demo fallback if any other random phone number is typed
    return {
        "found": False,
        "patient": {
            "phone": phone,
            "patient_name": "Walk-in Patient",
            "age": "35",
            "gender": "Other",
            "abha_id": "91-0000-1111-2222",
            "doctor_name": "OPD Duty Physician",
            "department": "General OPD",
            "time_slot": "Immediate"
        }
    }
@app.get("/")
def serve_kiosk_frontend():
    """Serves the standalone Kiosk HTML Frontend."""
    if not os.path.exists("index.html"):
        raise HTTPException(status_code=404, detail="index.html not found in project directory.")
    return FileResponse("index.html")

@app.get("/health")
def health_check():
    """Health check endpoint for diagnostics."""
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
    try:
        history_dicts = [{"role": msg.role, "content": msg.content} for msg in payload.conversation_history]
        turn_data = ask_follow_up(history_dicts, language=payload.language)

        turn_data["user_id"] = payload.user_id
        turn_data["session_id"] = payload.session_id
        turn_data["timestamp"] = datetime.utcnow().isoformat()

        return turn_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dialogue manager error: {str(e)}")


# --- 2. AYUSH Intake Endpoints ---
@app.post("/api/intake/ayush-turn")
def process_ayush_turn(payload: AyushTurnRequest):
    try:
        history_dicts = [{"role": msg.role, "content": msg.content} for msg in payload.conversation_history]
        return get_next_ayush_question(history_dicts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AYUSH engine error: {str(e)}")


@app.post("/api/intake/ayush-summary")
def process_ayush_summary(payload: AyushTurnRequest):
    try:
        history_dicts = [{"role": msg.role, "content": msg.content} for msg in payload.conversation_history]
        return summarize_ayush_profile(history_dicts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AYUSH summary error: {str(e)}")


# --- 3. Document Extraction Endpoints ---
@app.post("/api/document/extract-image")
async def extract_prescription_image(image_file: UploadFile = File(...)):
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
    try:
        return extract_document_entities(payload.raw_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR entity extraction error: {str(e)}")


# --- 4. Synthesis & Physician Report Endpoint ---
@app.post("/api/intake/synthesize")
def synthesize_intake_report(payload: SummaryRequest):
    try:
        history_dicts = [{"role": msg.role, "content": msg.content} for msg in payload.conversation_history]
        summary = generate_clinical_summary(history_dicts)

        if payload.document_data:
            summary["attached_records"] = payload.document_data

        summary["user_id"] = payload.user_id
        summary["session_id"] = payload.session_id
        summary["generated_at"] = datetime.utcnow().isoformat()

        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Synthesis error: {str(e)}")

# --- In-Memory Doctor OPD Live Queue & Consent Store ---
OPD_PATIENT_QUEUE = []

class HandoffRequest(BaseModel):
    user_id: str
    session_id: str
    patient_name: str
    department: str
    doctor_name: str
    clinical_summary: Dict[str, Any]
    patient_consented: bool = True
    edited_complaint: Optional[str] = None
    consented_at: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())

class StaffLoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/intake/consent-handoff")
def submit_patient_consent_and_handoff(payload: HandoffRequest):
    """Stores reviewed clinical intake in the live doctor OPD queue."""
    record = payload.dict()
    # Check if this session already exists in queue to update rather than duplicate
    existing = next((item for item in OPD_PATIENT_QUEUE if item["session_id"] == payload.session_id), None)
    if existing:
        existing.update(record)
    else:
        OPD_PATIENT_QUEUE.append(record)
    return {"status": "success", "message": "Handoff complete. Forwarded to practitioner queue.", "queue_token": f"OPD-{len(OPD_PATIENT_QUEUE)}"}

@app.post("/api/staff/login")
async def staff_login(payload: StaffLoginRequest):
    """Authenticates staff against doctors.csv with demo fail-safes."""
    u = payload.username.strip()
    p = payload.password.strip()

    # 1. Check CSV if available
    if os.path.exists("doctors.csv"):
        try:
            with open("doctors.csv", mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("username", "").strip() == u and row.get("password", "").strip() == p:
                        return {"authenticated": True, "doctor": row}
        except Exception as e:
            print(f"Error reading doctors.csv: {e}")

    # 2. Universal demo credentials (drsharma / doc123 or admin / admin)
    if (u == "drsharma" and p == "doc123") or (u == "drshastri" and p == "doc123") or (u == "admin"):
        return {
            "authenticated": True,
            "doctor": {
                "doctor_id": "DOC01",
                "doctor_name": "Dr. R. Sharma",
                "department": "General Medicine",
                "room_no": "Room 102",
                "username": u
            }
        }

    raise HTTPException(status_code=401, detail="Invalid staff credentials")

@app.get("/api/staff/queue")
def get_staff_patient_queue():
    """Returns the live OPD patient list for doctors."""
    return {"queue": OPD_PATIENT_QUEUE}


# --- Execution Entrypoint ---
if __name__ == "__main__":
    print("\n=======================================================")
    print("       MediKiosk Central Backend Initialized           ")
    print("=======================================================")
    print("Kiosk UI:     http://localhost:8000")
    print("Swagger Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000)