from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, String, Integer, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship

# ==========================================
# 1. DATABASE CONFIGURATION
# ==========================================
# Uses local SQLite by default for hackathon speed. 
# Swap to PostgreSQL: "postgresql://user:password@localhost:5432/db_name"
DATABASE_URL = "sqlite:///./clinical_app.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# 2. ORM MODELS (DATABASE TABLES)
# ==========================================
class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=True)
    sex = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    language = Column(String, default="en")
    abha_id = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    consents = relationship("Consent", back_populates="patient")
    timeline_events = relationship("MedicalTimeline", back_populates="patient")


class Consent(Base):
    __tablename__ = "consents"

    consent_id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.patient_id"))
    purpose = Column(String, default="CLINICAL_CARE")
    status = Column(String, default="GRANTED")
    granted_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="consents")


class MedicalTimeline(Base):
    __tablename__ = "medical_timeline"

    event_id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patients.patient_id"))
    event_type = Column(String, nullable=False)  # LAB_REPORT | PRESCRIPTION | INTAKE_NOTE
    title = Column(String, nullable=False)
    summary_data = Column(JSON, nullable=True)
    file_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="timeline_events")

# Create tables in Database
Base.metadata.create_all(bind=engine)

# ==========================================
# 3. PYDANTIC SCHEMAS (API SCHEMAS)
# ==========================================
class ABHARequestOTP(BaseModel):
    abha_id: str = Field(..., example="patient@abdm")

class ABHAVerifyOTP(BaseModel):
    abha_id: str = Field(..., example="patient@abdm")
    otp: str = Field(..., example="123456")

class TimelineEventCreate(BaseModel):
    event_id: str
    patient_id: str
    event_type: str
    title: str
    summary_data: Optional[Dict[str, Any]] = None
    file_url: Optional[str] = None

class TimelineEventResponse(BaseModel):
    event_id: str
    patient_id: str
    event_type: str
    title: str
    summary_data: Optional[Dict[str, Any]]
    file_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# ==========================================
# 4. APP & DEPENDENCIES
# ==========================================
app = FastAPI(title="ABDM Clinical Engine", version="1.0.0")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Seed mock patient data automatically on startup
@app.on_event("startup")
def seed_data():
    db = SessionLocal()
    if not db.query(Patient).filter(Patient.patient_id == "P-101").first():
        mock_patient = Patient(
            patient_id="P-101",
            name="Rahul Sharma",
            age=34,
            sex="Male",
            phone="9876543210",
            language="hi",
            abha_id="rahul@abdm"
        )
        db.add(mock_patient)
        db.commit()
        
        # Seed initial timeline event
        mock_event = MedicalTimeline(
            event_id="E-001",
            patient_id="P-101",
            event_type="INTAKE_NOTE",
            title="Initial Triage Consultation",
            summary_data={"chief_complaint": "Acute Chest Pain", "risk": "High"}
        )
        db.add(mock_event)
        db.commit()
    db.close()

# ==========================================
# 5. ENDPOINTS
# ==========================================

# --- Task 1: Mock ABHA ID Auth Flow ---
@app.post("/api/abha/request-otp")
def request_abha_otp(payload: ABHARequestOTP, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.abha_id == payload.abha_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="ABHA ID not registered")
    
    return {
        "status": "SUCCESS",
        "message": f"OTP successfully sent to phone linked with {payload.abha_id}",
        "mock_note": "Use '123456' as OTP for hackathon testing"
    }

@app.post("/api/abha/verify-otp")
def verify_abha_otp(payload: ABHAVerifyOTP, db: Session = Depends(get_db)):
    # Hackathon Logic: Accept any 6-digit OTP
    if len(payload.otp) != 6 or not payload.otp.isdigit():
        raise HTTPException(status_code=400, detail="Invalid 6-digit OTP format")
    
    patient = db.query(Patient).filter(Patient.abha_id == payload.abha_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="ABHA ID record not found")
    
    # Auto-grant compliance consent upon verification
    consent_id = f"CNS-{int(datetime.utcnow().timestamp())}"
    consent = Consent(consent_id=consent_id, patient_id=patient.patient_id)
    db.add(consent)
    db.commit()

    return {
        "status": "VERIFIED",
        "patient": {
            "patient_id": patient.patient_id,
            "name": patient.name,
            "age": patient.age,
            "sex": patient.sex,
            "abha_id": patient.abha_id,
            "language": patient.language
        },
        "consent": {
            "consent_id": consent_id,
            "purpose": "CLINICAL_CARE",
            "dpdp_compliant": True
        }
    }


# --- Task 2: Timeline Queries & Creation ---
@app.get("/api/patient/{patient_id}/timeline", response_model=List[TimelineEventResponse])
def get_patient_timeline(patient_id: str, db: Session = Depends(get_db)):
    events = (
        db.query(MedicalTimeline)
        .filter(MedicalTimeline.patient_id == patient_id)
        .order_by(MedicalTimeline.created_at.desc())
        .all()
    )
    return events

@app.post("/api/patient/timeline/event", response_model=TimelineEventResponse)
def add_timeline_event(payload: TimelineEventCreate, db: Session = Depends(get_db)):
    event = MedicalTimeline(
        event_id=payload.event_id,
        patient_id=payload.patient_id,
        event_type=payload.event_type,
        title=payload.title,
        summary_data=payload.summary_data,
        file_url=payload.file_url
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


# --- Task 3: HL7 FHIR JSON Exporter ---
@app.get("/api/patient/{patient_id}/fhir-export")
def export_fhir_bundle(patient_id: str, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    timeline_events = (
        db.query(MedicalTimeline)
        .filter(MedicalTimeline.patient_id == patient_id)
        .all()
    )

    # Build FHIR Document Bundle compliant with ABDM standards
    bundle_entries = [
        # FHIR Resource 1: Patient Details
        {
            "fullUrl": f"urn:uuid:patient-{patient.patient_id}",
            "resource": {
                "resourceType": "Patient",
                "id": patient.patient_id,
                "identifier": [
                    {
                        "system": "https://healthid.abdm.gov.in",
                        "value": patient.abha_id
                    }
                ],
                "name": [{"text": patient.name}],
                "gender": patient.sex.lower() if patient.sex else "unknown",
                "telecom": [{"system": "phone", "value": patient.phone}]
            }
        }
    ]

    # FHIR Resource 2+: Observations / Clinical Notes from Timeline
    for event in timeline_events:
        bundle_entries.append({
            "fullUrl": f"urn:uuid:event-{event.event_id}",
            "resource": {
                "resourceType": "Observation",
                "id": event.event_id,
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": event.event_type.lower(),
                                "display": event.title
                            }
                        ]
                    }
                ],
                "subject": {"reference": f"Patient/{patient.patient_id}"},
                "effectiveDateTime": event.created_at.isoformat(),
                "valueString": str(event.summary_data or event.title)
            }
        })

    return {
        "resourceType": "Bundle",
        "id": f"bundle-{patient_id}",
        "type": "document",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "entry": bundle_entries
    }
# ==========================================
# 6. INTEGRATION ENDPOINTS FOR TEAM MEMBERS
# ==========================================

class PatientIntakeSubmit(BaseModel):
    patient_id: str
    ayush_profile: Dict[str, Any]  # Person 1: Appetite, digestion, sleep
    transcript: str                # Person 1: Audio transcript
    document_ids: Optional[List[str]] = None

class AISummaryPayload(BaseModel):
    patient_id: str
    chief_complaint: str
    hpi: str
    past_meds: Optional[str] = None
    lab_anomalies: Optional[str] = None
    is_emergency: bool = False     # Person 3: Triage Flag
    emergency_reason: Optional[str] = None

# --- Endpoint 1: Person 1 saves AYUSH Form & Intake Data ---
@app.post("/api/patient/submit-intake")
def submit_patient_intake(payload: PatientIntakeSubmit, db: Session = Depends(get_db)):
    # Create or update the medical timeline entry with raw intake data
    event_id = f"EVT-{int(datetime.utcnow().timestamp())}"
    timeline_event = MedicalTimeline(
        event_id=event_id,
        patient_id=payload.patient_id,
        event_type="INTAKE_NOTE",
        title="Patient Intake & AYUSH Assessment",
        summary_data={
            "ayush_profile": payload.ayush_profile,
            "raw_transcript": payload.transcript
        }
    )
    db.add(timeline_event)
    db.commit()
    return {"status": "SUCCESS", "event_id": event_id}


# --- Endpoint 2: Person 3 (AI Lead) pushes Structured AI Summaries ---
@app.post("/api/ai/save-summary")
def save_ai_summary(payload: AISummaryPayload, db: Session = Depends(get_db)):
    event_id = f"AI-{int(datetime.utcnow().timestamp())}"
    
    # Store AI extraction as a Timeline event
    ai_event = MedicalTimeline(
        event_id=event_id,
        patient_id=payload.patient_id,
        event_type="CLINICAL_SUMMARY",
        title="AI Processed Clinical Summary",
        summary_data={
            "chief_complaint": payload.chief_complaint,
            "hpi": payload.hpi,
            "past_meds": payload.past_meds,
            "lab_anomalies": payload.lab_anomalies,
            "is_emergency": payload.is_emergency,
            "emergency_reason": payload.emergency_reason
        }
    )
    db.add(ai_event)
    db.commit()
    
    return {"status": "SUCCESS", "message": "AI summary linked to patient record"}


# --- Endpoint 3: Person 2 (Doctor) fetches active patient queue ---
@app.get("/api/doctor/queue")
def get_doctor_queue(db: Session = Depends(get_db)):
    # Fetches all patients alongside their latest clinical summary
    patients = db.query(Patient).all()
    queue = []
    
    for p in patients:
        latest_summary = (
            db.query(MedicalTimeline)
            .filter(MedicalTimeline.patient_id == p.patient_id)
            .filter(MedicalTimeline.event_type == "CLINICAL_SUMMARY")
            .order_by(MedicalTimeline.created_at.desc())
            .first()
        )
        
        summary_data = latest_summary.summary_data if latest_summary else {}
        
        queue.append({
            "patient_id": p.patient_id,
            "name": p.name,
            "age": p.age,
            "sex": p.sex,
            "chief_complaint": summary_data.get("chief_complaint", "Pending AI Processing"),
            "is_emergency": summary_data.get("is_emergency", False),
            "emergency_reason": summary_data.get("emergency_reason", None)
        })
        
    return queue
