import os
import pyttsx3
from faster_whisper import WhisperModel

# 'small' with int8 CPU quantization provides the best balance of
# speed and phonetic accuracy for Indian English and Hindi accents.
ASR_MODEL_SIZE = "small"

print(f"Loading local Whisper ({ASR_MODEL_SIZE}) model...")
whisper_asr = WhisperModel(ASR_MODEL_SIZE, device="cpu", compute_type="int8")

CLINICAL_PROMPTS = {
    "hi": "मरीज के लक्षण: घुटने में दर्द, सीने में दर्द, बुखार, खांसी, सिरदर्द, उल्टी, पेट दर्द, चक्कर।",
    "en": "Patient clinical intake: knee pain, chest pain, fever, cough, headache, nausea, abdominal pain, vomiting."
}


def transcribe_patient_audio(audio_file_path: str, language: str = None) -> tuple[str, str]:
    """
    Transcribes spoken patient audio into text with clinical vocabulary biasing.

    :param audio_file_path: Path to the .wav/.mp3 file.
    :param language: 'hi' for Hindi, 'en' for English, or None for Auto-Detection.
    :return: Tuple of (transcription_text, resolved_language_code)
    """
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

    # Step 1: Auto-detect language if not explicitly provided
    if language is None:
        _, detect_info = whisper_asr.transcribe(audio_file_path, beam_size=1)
        detected = detect_info.language if detect_info.language in ["hi", "en"] else "en"
        language = detected

    # Step 2: Pick relevant domain prompt
    prompt = CLINICAL_PROMPTS.get(language, CLINICAL_PROMPTS["en"])

    # Step 3: Run robust transcription with loop/hallucination guards
    segments, info = whisper_asr.transcribe(
        audio_file_path,
        language=language,
        initial_prompt=prompt,
        beam_size=5,
        repetition_penalty=1.2,
        no_repeat_ngram_size=3,
        condition_on_previous_text=False
    )

    transcription = " ".join([segment.text for segment in segments]).strip()
    return transcription, language


def speak_question_to_patient(text: str, output_path: str = "prompt.wav") -> str:
    """
    Synthesizes kiosk prompt text to an audio file for the kiosk speaker/headphones.
    """
    if not text or not text.strip():
        raise ValueError("Cannot synthesize empty text.")

    engine = pyttsx3.init()
    engine.setProperty("rate", 145)  # Slightly slower pace for clinical comprehension
    engine.setProperty("volume", 1.0)  # Full volume for noisy hospital environments

    # Select an appropriate system voice if available
    voices = engine.getProperty("voices")
    if voices:
        # Defaults to the first installed local voice (e.g., Microsoft David/Zira/Heera)
        engine.setProperty("voice", voices[0].id)

    engine.save_to_file(text, output_path)
    engine.runAndWait()
    engine.stop()

    return output_path


if __name__ == "__main__":
    # 1. Quick Test Text-to-Speech
    test_question = "Where does it hurt the most? Please point or describe."
    audio_out = speak_question_to_patient(test_question)
    print(f"Generated prompt audio at: {audio_out}")

    # 2. Quick Test ASR (if a sample exists)
    sample_file = "patient_input.wav"
    if os.path.exists(sample_file):
        print(f"\nTranscribing {sample_file}...")
        transcript, lang = transcribe_patient_audio(sample_file, language=None)
        print(f"Detected Language: {lang}")
        print(f"Transcript: {transcript}")