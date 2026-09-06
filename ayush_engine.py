import json
import re
import ollama

MODEL_NAME = "qwen3.5:4b"

AYUSH_SYSTEM_PROMPT = """
You are the Ayurvedic Clinical Intake Assistant for MediKiosk at an AYUSH hospital.
Your goal is to elicit clinical history following Dashavidha Pariksha (including Agni, Koshtha, Prakriti/Vikriti signs) and Ahara-Vihara (diet/lifestyle).

Respond ONLY with a valid JSON object matching this schema:
{
  "question": "Clear, accessible question about digestion, bowel habits, sleep, or daily routine",
  "ayush_parameter": "Agni | Koshtha | Prakriti | Ahara-Vihara | Nidra | Vyayama",
  "options": ["Option 1", "Option 2", "Option 3", "Not sure"]
}

Keep the language patient-friendly and practical for touch-screen choices while assessing traditional Ayurvedic parameters.
"""

AYUSH_SUMMARY_PROMPT = """
You are an expert Ayurvedic clinical documentation engine.
Synthesize the patient's dialogue responses into a structured Dashavidha Pariksha and Ahara-Vihara clinical brief.

Respond ONLY with a valid JSON object matching this schema:
{
  "agni_assessment": "Manda (sluggish) | Tikshna (sharp/hyper) | Vishama (irregular) | Sama (balanced)",
  "koshtha_type": "Krura (hard/constipated) | Mridu (soft/frequent) | Madhyama (moderate)",
  "predominant_dosha_imbalance": "Vata | Pitta | Kapha | Tridoshic / Mixed",
  "ahara_vihara_notes": "Concise summary of diet, sleep, routine, and stressors",
  "clinical_correlation": "Brief 1-2 sentence impression linking lifestyle/Agni to the presenting complaint"
}
"""


def clean_and_parse_json(raw_text: str) -> dict:
    if not raw_text or not raw_text.strip():
        raise ValueError("Model returned empty output (0 tokens).")

    # Look for the outermost JSON block
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


def safe_ollama_call(system_prompt: str, messages: list) -> dict:
    """Executes chat with streaming token accumulation and a robust retry fallback."""
    full_response = ""
    payload_messages = [{"role": "system", "content": system_prompt}] + messages

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
        print(f"[Streaming notice: {e}] Falling back to batch inference...")

    # Fallback if stream delivered 0 tokens
    if not full_response.strip():
        res = ollama.chat(
            model=MODEL_NAME,
            messages=payload_messages,
            options={"temperature": 0.2}
        )
        full_response = res.get("message", {}).get("content", "")

    return clean_and_parse_json(full_response)


def get_next_ayush_question(conversation_history: list) -> dict:
    return safe_ollama_call(AYUSH_SYSTEM_PROMPT, conversation_history)


def summarize_ayush_profile(conversation_history: list) -> dict:
    transcript = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
    user_msg = [{"role": "user", "content": f"AYUSH Intake Conversation:\n{transcript}"}]
    return safe_ollama_call(AYUSH_SUMMARY_PROMPT, user_msg)


def run_interactive_ayush_session(max_turns: int = 3):
    """Run a live terminal intake loop to test adaptive questioning without hardcoded arrays."""
    print("=== MediKiosk AYUSH Intake Session ===")
    initial_symptom = input("\nEnter your initial health complaint: ").strip()
    if not initial_symptom:
        initial_symptom = "I have persistent acidity and fatigue."
        print(f"Using default: {initial_symptom}")

    conversation = [{"role": "user", "content": initial_symptom}]

    for turn in range(max_turns):
        print(f"\n[AI is evaluating Ayurvedic parameters (Turn {turn + 1}/{max_turns})...]")
        q_data = get_next_ayush_question(conversation)

        print(f"\nAyush Axis: [{q_data.get('ayush_parameter', 'General')}]")
        print(f"Question: {q_data.get('question')}")
        options = q_data.get("options", [])
        if options:
            print("Options:")
            for i, opt in enumerate(options, 1):
                print(f"  {i}. {opt}")

        user_choice = input("\nYour answer (select option number or type response): ").strip()
        if user_choice.isdigit() and 1 <= int(user_choice) <= len(options):
            answer_text = options[int(user_choice) - 1]
        else:
            answer_text = user_choice if user_choice else "Normal"

        conversation.append({"role": "assistant", "content": q_data.get("question", "")})
        conversation.append({"role": "user", "content": answer_text})

    print("\n--- Generating Physician Ayurvedic Consultation Brief ---")
    summary = summarize_ayush_profile(conversation)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    # Runs the live interactive intake loop
    run_interactive_ayush_session(max_turns=3)