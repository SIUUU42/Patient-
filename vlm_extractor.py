import json
import os
import re
import ollama

VISION_MODEL = "qwen3.5:9b"

SYSTEM_PROMPT = """
You are an expert clinical OCR and medical document extraction engine for hospital kiosks.
Analyze medical documents, prescriptions, and clinical notes with high precision, especially handwritten text.
Always output strictly a valid JSON object matching the requested schema without conversational filler.
"""

EXTRACTION_PROMPT = """
Analyze this prescription image. Focus on section '16. TREATMENT' and any handwritten or printed clinical notes.

Return ONLY a JSON object matching this schema:
{
  "document_type": "Prescription",
  "medications": [
    {
      "name": "Exact drug name",
      "dosage": "e.g., 625mg, 40mg, or 'Not specified'",
      "frequency": "e.g., BD (twice daily), TDS (thrice daily), OD (once daily)",
      "instructions": "e.g., BBF (before breakfast), with food, or duration like 7 days"
    }
  ],
  "procedures_or_advice": ["List any procedures like Dressing, advice, etc."]
}
"""

def clean_and_parse_json(raw_text: str) -> dict:
    if not raw_text or not raw_text.strip():
        raise ValueError("Vision model returned completely empty output (0 tokens).")

    # 1. Look for outer JSON object
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # 2. Stripping markdown blocks if regex match failed
    try:
        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"```$", "", cleaned)
        return json.loads(cleaned.strip())
    except Exception:
        raise ValueError(f"Could not parse valid JSON from vision output:\n{raw_text}")


def extract_from_prescription_image(image_path: str):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at path: {image_path}")

    print(f"Reading handwritten prescription with {VISION_MODEL}...")

    # Notice: format="json" is omitted so the vision encoder is not grammar-locked
    full_response = ""
    try:
        stream = ollama.chat(
            model=VISION_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT,
                    "images": [image_path]
                }
            ],
            stream=True,
            options={"temperature": 0.1}
        )

        for chunk in stream:
            token = chunk.get("message", {}).get("content", "")
            full_response += token
            print(token, end="", flush=True)
        print()

    except Exception as stream_err:
        print(f"\n[Vision streaming warning: {stream_err}], attempting fallback...")

    # Fallback attempt if stream yielded empty tokens
    if not full_response.strip():
        print("[Vision stream returned 0 tokens. Retrying non-streaming fallback...]")
        res = ollama.chat(
            model=VISION_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT,
                    "images": [image_path]
                }
            ],
            options={"temperature": 0.1}
        )
        full_response = res.get("message", {}).get("content", "")

    return clean_and_parse_json(full_response)


if __name__ == "__main__":
    image_path = r"C:\Users\atuly\Desktop\test.jpg"

    try:
        result = extract_from_prescription_image(image_path)
        print("\n--- Extracted Document JSON ---")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"\nExtraction Error: {e}")