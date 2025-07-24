import streamlit as st
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import speech_recognition as sr
import tempfile
import os

def transcribe_audio(file_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
            return text
        except sr.UnknownValueError:
            return "Could not understand audio."
        except sr.RequestError:
            return "API unavailable."

def score_audio(file_path: str, reference_text: str):
    audio = AudioSegment.from_file(file_path)
    duration_seconds = len(audio) / 1000
    nonsilent_chunks = detect_nonsilent(audio, min_silence_len=200, silence_thresh=-40)
    spoken_duration = sum([chunk[1] - chunk[0] for chunk in nonsilent_chunks]) / 1000

    word_count = len(reference_text.strip().split())
    speech_rate_wpm = (word_count / spoken_duration) * 60 if spoken_duration > 0 else 0

    # Content score: based on how many words matched
    transcription = transcribe_audio(file_path).lower()
    spoken_words = set(transcription.split())
    reference_words = set(reference_text.lower().split())
    matched_words = spoken_words & reference_words
    content_accuracy = len(matched_words) / len(reference_words) if reference_words else 0
    content_score = round(content_accuracy * 90)

    fluency_score = 90 if 180 <= speech_rate_wpm <= 200 else max(40, min(90, int(100 - abs(190 - speech_rate_wpm))))
    pronunciation_score = 70  # Placeholder

    final_speaking_score = round((0.4 * content_score + 0.3 * fluency_score + 0.3 * pronunciation_score), 1)
    reading_score = round((0.6 * content_score + 0.4 * pronunciation_score), 1)

    return {
        "duration_seconds": round(duration_seconds, 2),
        "spoken_duration": round(spoken_duration, 2),
        "speech_rate_wpm": round(speech_rate_wpm, 2),
        "transcription": transcription,
        "scores": {
            "content": content_score,
            "fluency": fluency_score,
            "pronunciation": pronunciation_score,
            "estimated_speaking_score": final_speaking_score,
            "estimated_reading_score": reading_score
        }
    }

# Streamlit Interface
st.title("PTE Speaking Score Estimator")

uploaded_file = st.file_uploader("Upload your audio file (WAV/MP3)", type=["wav", "mp3"])
reference_text = st.text_area("Paste the reference reading passage below:")

if uploaded_file and reference_text:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        audio = AudioSegment.from_file(uploaded_file)
        audio.export(tmp_file.name, format="wav")
        result = score_audio(tmp_file.name, reference_text)

    st.subheader("Transcription")
    st.write(result['transcription'])

    st.subheader("Score Breakdown")
    st.json(result['scores'])

    st.subheader("Speech Metrics")
    st.write(f"Duration: {result['duration_seconds']} sec")
    st.write(f"Spoken Duration: {result['spoken_duration']} sec")
    st.write(f"Speech Rate: {result['speech_rate_wpm']} WPM")
