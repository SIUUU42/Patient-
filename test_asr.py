import json
import re
import ollama
import sounddevice as sd
from scipy.io.wavfile import write
from faster_whisper import WhisperModel

MODEL_NAME = "qwen3.5:4b"

print("Loading Whisper 'small' model...")
asr_model = WhisperModel("small", device="cpu", compute_type="int8")

CLINICAL_PROMPTS = {
    "hi": "मरीज के लक्षण: घुटने में दर्द, सीने में दर्द, बुखार, खांसी, सिरदर्द, उल्टी, पेट दर्द।",
    "en": "Patient clinical intake: knee pain, chest pain, fever, cough, headache, nausea, breathlessness."
}


def record_audio(filename="patient_input.wav", duration=5, sample_rate=16000):
    print(f"\n[Recording for {duration} seconds... Speak your symptom clearly]")
    audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
    sd.wait()
    write(filename, sample_rate, audio_data)
    print("Recording saved.")
    return filename


def transcribe_audio(audio_path: str, language: str = None):
    if language is None:
        print("Detecting language...")
        _, detect_info = asr_model.transcribe(audio_path, beam_size=1)
        language = detect_info.language if detect_info.language in ["hi", "en"] else "en"
        print(f"Auto-detected language: {language} (Confidence: {detect_info.language_probability:.2f})")

    prompt = CLINICAL_PROMPTS.get(language, CLINICAL_PROMPTS["en"])

    segments, info = asr_model.transcribe(
        audio_path,
        language=language,
        initial_prompt=prompt,
        beam_size=5,
        repetition_penalty=1.2,
        no_repeat_ngram_size=3,
        condition_on_previous_text=False
    )
    full_text = " ".join([seg.text for seg in segments]).strip()
    return full_text, language


def clean_and_parse_json(raw_text: str) -> dict:
    if not raw_text or not raw_text.strip():
        raise ValueError("Model returned completely empty output (0 tokens).")

    # 1. Look for JSON markdown block or raw braces
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # 2. If standard regex parse fails, try basic repair
    try:
        cleaned = raw_text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except Exception:
        raise ValueError(f"Could not parse valid JSON from output:\n{raw_text}")


def ask_qwen_intake(transcript: str, language: str):
    # Guard: if speech was silent or junk
    if not transcript or len(transcript.strip()) < 2:
        print("[Warning] No valid speech detected in transcript.")
        return {
            "normalized_complaint_en": "Unclear speech",
            "follow_up_question": "कृपया अपनी समस्या दोबारा बताएं।" if language == "hi" else "Could you please describe your symptoms again?",
            "touchscreen_options": ["बोलें / Speak Again", "स्क्रीन पर टाइप करें / Type"]
        }

    print(f"\nPassing to {MODEL_NAME} for clinical intake...")

    system_prompt = f"""
You are the AI clinical intake assistant for an outpatient hospital kiosk (MediKiosk).
The patient spoke in language code: "{language}" (hi = Hindi, en = English).

Task:
1. Identify the chief complaint from the patient speech.
2. Formulate the next logical follow-up question following the SOCRATES clinical framework.
3. The follow-up question MUST be in the patient's spoken language ({language}).
4. Provide 3-4 short touchscreen options in the patient's language.

Output strictly valid JSON matching this schema:
{{
  "normalized_complaint_en": "Standard clinical English description",
  "follow_up_question": "Follow-up question in patient's language",
  "touchscreen_options": ["Option 1", "Option 2", "Option 3", "Option 4"]
}}
"""

    # Primary attempt: Streaming with token accumulation
    full_response = ""
    try:
        stream = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Patient speech transcript: \"{transcript}\""}
            ],
            stream=True,
            options={"temperature": 0.2}
        )

        for chunk in stream:
            token = chunk.get("message", {}).get("content", "")
            full_response += token
            print(token, end="", flush=True)
        print()

    except Exception as stream_err:
        print(f"\n[Streaming hiccup: {stream_err}], attempting fallback call...")

    # Fallback attempt if stream came back blank
    if not full_response.strip():
        print("[Ollama streamed 0 tokens. Retrying non-streaming fallback...]")
        res = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Patient speech transcript: \"{transcript}\""}
            ],
            options={"temperature": 0.2}
        )
        full_response = res.get("message", {}).get("content", "")

    return clean_and_parse_json(full_response)


if __name__ == "__main__":
    # 1. Record voice from mic
    audio_file = record_audio(duration=5)

    # 2. Whisper Speech-to-Text
    transcript, lang = transcribe_audio(audio_file, language=None)
    print(f"\n--- ASR Transcript ({lang}) ---")
    print(transcript if transcript else "[No speech detected]")

    # 3. Pipe into Qwen LLM
    if transcript:
        result = ask_qwen_intake(transcript, lang)
        print("\n--- Kiosk UI Payload (Ready for Frontend) ---")
        print(json.dumps(result, indent=2, ensure_ascii=False))