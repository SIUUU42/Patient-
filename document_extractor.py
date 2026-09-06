import json
import re
import ollama

MODEL_NAME = "qwen3.5:4b"

EXTRACTOR_PROMPT = """
You are the medical document intelligence engine for MediKiosk.
Your task is to extract structured clinical entities from raw text scanned from prior prescriptions, lab reports, or discharge summaries.

Output strictly a valid JSON object matching this exact schema:
{
  "document_date": "YYYY-MM-DD or 'Unknown'",
  "document_type": "Prescription | Lab Report | Discharge Summary | Other",
  "diagnoses": ["List of diagnosed conditions"],
  "medications": [
    {
      "name": "Drug name",
      "dosage": "e.g., 500mg",
      "frequency": "e.g., Twice daily / BD",
      "duration": "e.g., 5 days"
    }
  ],
  "investigations": [
    {
      "test_name": "Test name",
      "value": "Observed value with units",
      "reference_range": "Normal range if stated",
      "is_abnormal": true
    }
  ]
}

Rules:
- Flag 'is_abnormal' as true if a lab value exceeds standard limits (e.g., HbA1c > 6.5%, Fasting Blood Sugar > 100 mg/dL).
- Do not invent data; leave fields as empty lists or 'Unknown' if not found.
"""


def clean_and_parse_json(raw_text: str) -> dict:
    if not raw_text or not raw_text.strip():
        raise ValueError("Document extractor model returned empty output (0 tokens).")

    # Match outer JSON block
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Markdown fence strip fallback
    try:
        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"```$", "", cleaned)
        return json.loads(cleaned.strip())
    except Exception:
        raise ValueError(f"Could not parse valid JSON from output:\n{raw_text}")


def extract_document_entities(raw_ocr_text: str) -> dict:
    if not raw_ocr_text or not raw_ocr_text.strip():
        raise ValueError("Input OCR text is empty.")

    payload_messages = [
        {"role": "system", "content": EXTRACTOR_PROMPT},
        {"role": "user", "content": f"Scanned Medical Document Text:\n{raw_ocr_text}"}
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
        print(f"[Document extraction streaming warning: {e}], running fallback...")

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
    sample_ocr_text = """
    CITY CARE CLINIC - Dr. R. Sharma, MD
    Date: 12/01/2026
    Patient: Ramesh Kumar, Age: 52
    Rx:
    1. Tab Metformin 500mg - 1 tab twice daily after meals x 30 days
    2. Tab Telmisartan 40mg - once daily morning x 30 days

    Clinical notes: Type 2 Diabetes Mellitus, Essential Hypertension.
    Recent Labs:
    Fasting Blood Sugar: 148 mg/dL (Normal: 70-99 mg/dL)
    HbA1c: 7.8% (Normal: < 5.7%)
    Serum Creatinine: 1.0 mg/dL (Normal: 0.7 - 1.3 mg/dL)
    """

    print("Extracting structured clinical data from scanned document text...")
    try:
        extracted_data = extract_document_entities(sample_ocr_text)
        print(json.dumps(extracted_data, indent=2, ensure_ascii=False))
    except Exception as err:
        print(f"Extraction error: {err}")