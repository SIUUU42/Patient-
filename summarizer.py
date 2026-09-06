import json
import re
from typing import Union, List, Dict
import ollama

MODEL_NAME = "qwen3.5:4b"

SUMMARIZER_PROMPT = """
You are the clinical documentation assistant for MediKiosk.
Transform the multi-turn patient interview transcript into a concise, physician-ready intake summary.

Output ONLY a valid JSON object matching this exact schema:
{
  "chief_complaint": "Short 1-line statement with duration",
  "history_of_present_illness": "Concise chronological narrative covering SOCRATES details",
  "past_medical_and_surgical": "Any known past conditions or 'None reported'",
  "medications_and_allergies": "Current meds or allergies if mentioned, otherwise 'None reported'",
  "review_of_systems": "Pertinent positives or negatives reported by patient",
  "triage_priority": "Routine | Priority | Emergency"
}

Rules:
- Assign 'Emergency' for critical red flags (acute chest pain, stroke signs, respiratory failure).
- Assign 'Priority' for severe uncontrolled pain, high fever, or progressive acute symptoms.
- Assign 'Routine' for standard subacute or chronic outpatient complaints.
- Output strictly valid JSON without conversational preamble.
"""


def clean_and_parse_json(raw_text: str) -> dict:
    if not raw_text or not raw_text.strip():
        raise ValueError("Summarizer model returned empty output (0 tokens).")

    # 1. Match outer JSON block
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # 2. Strip markdown code fences if regex fallback is needed
    try:
        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"```$", "", cleaned)
        return json.loads(cleaned.strip())
    except Exception:
        raise ValueError(f"Could not parse valid JSON from summary output:\n{raw_text}")


def format_transcript_input(dialogue: Union[str, List[Dict[str, str]]]) -> str:
    """Converts either a raw string or dialogue_manager history list into clean dialogue text."""
    if isinstance(dialogue, list):
        formatted_lines = []
        for turn in dialogue:
            role = "Patient" if turn.get("role") == "user" else "Kiosk"
            content = turn.get("content", "").strip()
            formatted_lines.append(f"{role}: {content}")
        return "\n".join(formatted_lines)
    return str(dialogue).strip()


def generate_clinical_summary(dialogue_transcript: Union[str, List[Dict[str, str]]]) -> dict:
    formatted_text = format_transcript_input(dialogue_transcript)
    if not formatted_text:
        raise ValueError("Encounter transcript is empty.")

    payload_messages = [
        {"role": "system", "content": SUMMARIZER_PROMPT},
        {"role": "user", "content": f"Patient Intake Conversation:\n{formatted_text}"}
    ]

    full_response = ""
    try:
        stream = ollama.chat(
            model=MODEL_NAME,
            messages=payload_messages,
            stream=True,
            options={"temperature": 0.1}
        )
        for chunk in stream:
            token = chunk.get("message", {}).get("content", "")
            full_response += token
    except Exception as e:
        print(f"[Summarizer streaming warning: {e}], running fallback...")

    # Fallback if streaming failed or emitted 0 tokens
    if not full_response.strip():
        res = ollama.chat(
            model=MODEL_NAME,
            messages=payload_messages,
            options={"temperature": 0.1}
        )
        full_response = res.get("message", {}).get("content", "")

    return clean_and_parse_json(full_response)


if __name__ == "__main__":
    # Test case: multi-turn dialogue
    sample_dialogue = [
        {"role": "assistant", "content": "What is your primary symptom today?"},
        {"role": "user", "content": "I have had a severe throbbing headache since this morning."},
        {"role": "assistant", "content": "Where does it hurt the most?"},
        {"role": "user", "content": "Mostly on the right side behind my eye."},
        {"role": "assistant", "content": "Are you experiencing any other symptoms?"},
        {"role": "user", "content": "Nausea and extreme sensitivity to bright light. No fever or neck stiffness."},
        {"role": "assistant", "content": "Have you taken any medication for this?"},
        {"role": "user", "content": "I took one Paracetamol 500mg around noon, but it didn't help."}
    ]

    print("Generating doctor-ready clinical summary...")
    try:
        summary = generate_clinical_summary(sample_dialogue)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    except Exception as err:
        print(f"Summarizer Error: {err}")