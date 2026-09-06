import json
import re
import ollama

MODEL_NAME = "qwen3.5:4b"

SYSTEM_PROMPT_TEMPLATE = """
You are the clinical intake AI for MediKiosk, an offline hospital outpatient kiosk.
Your task is to conduct an adaptive medical history interview using the SOCRATES clinical framework.
Target language code: "{language}" (en = English, hi = Hindi).

Rules:
1. Formulate the next logical question to clarify the symptom (Site, Onset, Character, Radiation, Associations, Time course, Exacerbating factors, Severity).
2. The question MUST be output in the target language ({language}).
3. Provide 3-4 short, simple tap-friendly choices for the kiosk touchscreen in the target language.
4. Set 'is_emergency' to true ONLY if red-flag symptoms appear (e.g., crushing chest pain radiating to arm/jaw, acute breathlessness, sudden facial droop or limb weakness, severe trauma/uncontrolled bleeding).
5. Set 'is_intake_complete' to true if you have gathered sufficient clinical details (typically 3-4 questions) or if an emergency is detected.

Respond ONLY with a valid JSON object matching this exact schema:
{{
  "question": "Clear, simple question for the patient",
  "options": ["Option 1", "Option 2", "Option 3", "Other / Not sure"],
  "is_emergency": false,
  "is_intake_complete": false,
  "clinical_dimension": "Site | Onset | Character | Radiation | Severity | Associated Symptoms"
}}
"""


def clean_and_parse_json(raw_text: str) -> dict:
    if not raw_text or not raw_text.strip():
        raise ValueError("Model returned completely empty output (0 tokens).")

    # Match outer JSON block
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Clean markdown fences fallback
    try:
        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"```$", "", cleaned)
        return json.loads(cleaned.strip())
    except Exception:
        raise ValueError(f"Could not parse valid JSON from dialogue output:\n{raw_text}")


def ask_follow_up(conversation_history: list, language: str = "en") -> dict:
    """
    Takes the running conversation history (list of role/content dicts)
    and returns the next adaptive SOCRATES question and UI buttons.
    """
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(language=language)
    payload_messages = [{"role": "system", "content": system_prompt}] + conversation_history

    full_response = ""
    try:
        stream = ollama.chat(
            model=MODEL_NAME,
            messages=payload_messages,
            stream=True,
            options={"temperature": 0.2}
        )
        for chunk in stream:
            token = chunk.get("message", {}).get("content", "")
            full_response += token
    except Exception as e:
        print(f"[Streaming warning: {e}], running fallback...")

    # Fallback if streaming failed or emitted 0 tokens
    if not full_response.strip():
        res = ollama.chat(
            model=MODEL_NAME,
            messages=payload_messages,
            options={"temperature": 0.2}
        )
        full_response = res.get("message", {}).get("content", "")

    return clean_and_parse_json(full_response)


def run_interactive_intake_session(initial_complaint: str = None, language: str = "en", max_turns: int = 4):
    """CLI simulator for testing the multi-turn kiosk loop interactively."""
    print(f"\n=== MediKiosk Intake Simulator [{language.upper()}] ===")

    if not initial_complaint:
        initial_complaint = input("Enter initial symptom: ").strip()
        if not initial_complaint:
            initial_complaint = "I have severe headache since morning."

    history = [{"role": "user", "content": initial_complaint}]

    for turn in range(max_turns):
        print(f"\n[Evaluating turn {turn + 1}/{max_turns}...]")
        turn_data = ask_follow_up(history, language=language)

        if turn_data.get("is_emergency"):
            print("\n🚨 [TRIAGE ALERT: RED FLAG EMERGENCY DETECTED] 🚨")
            print(f"Directing to Casualty: {turn_data.get('question')}")
            return history

        print(f"\nQuestion: {turn_data.get('question')}")
        options = turn_data.get("options", [])
        for idx, opt in enumerate(options, 1):
            print(f"  {idx}. {opt}")

        if turn_data.get("is_intake_complete") or turn == max_turns - 1:
            print("\n[Clinical history collection sufficient. Handing off to summary.]")
            break

        choice = input("\nSelect option number or type custom response: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            answer = options[int(choice) - 1]
        else:
            answer = choice if choice else "Moderate"

        history.append({"role": "assistant", "content": turn_data.get("question", "")})
        history.append({"role": "user", "content": answer})

    return history


if __name__ == "__main__":
    # Test a full multi-turn interview in English or Hindi
    completed_history = run_interactive_intake_session(
        initial_complaint="I have bad stomach pain since 2 days",
        language="en",
        max_turns=3
    )
    print("\n--- Completed Dialogue History ---")
    print(json.dumps(completed_history, indent=2, ensure_ascii=False))