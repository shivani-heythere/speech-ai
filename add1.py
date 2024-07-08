import os
import uuid
import subprocess
import speech_recognition as sr
from pydub import AudioSegment
import difflib

CHUNK_DURATION = 5  # Reduced duration of each audio chunk in seconds
OVERLAP_DURATION = 2  # Overlap between chunks in seconds

def convert_video_to_audio(video_path, audio_path):
    subprocess.run(['ffmpeg', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2', audio_path])

def transcribe_audio_chunk(audio_chunk, recognizer, language='hi-IN'):
    try:
        text = recognizer.recognize_google(audio_chunk, language=language)
        return text
    except sr.UnknownValueError:
        return ""

def generate_subtitles_with_timing(transcribed_text, chunk_durations, overlap_duration):
    subtitles = []
    start_time = 0
    for i, (text, duration) in enumerate(zip(transcribed_text, chunk_durations)):
        end_time = start_time + duration - (overlap_duration if i < len(transcribed_text) - 1 else 0)
        subtitles.append(f"{i+1}\n{convert_seconds_to_srt_time(start_time)} --> {convert_seconds_to_srt_time(end_time)}\n{text}\n")
        start_time = end_time
    return '\n'.join(subtitles)

def convert_seconds_to_srt_time(seconds):
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def remove_repeated_words(previous_text, current_text):
    sm = difflib.SequenceMatcher(None, previous_text.split(), current_text.split())
    match = sm.find_longest_match(0, len(previous_text.split()), 0, len(current_text.split()))
    if match.size > 0:
        overlap = " ".join(current_text.split()[match.b + match.size:])
        return overlap
    return current_text

def generate_subtitles(video_path, video_language='hi-IN'):
    audio_path = os.path.splitext(video_path)[0] + '.wav'

    unique_id = uuid.uuid4().hex[:6]
    subtitle_filename = f"{os.path.splitext(os.path.basename(video_path))[0]}_{unique_id}.srt"
    subtitle_path = os.path.join('subtitles', subtitle_filename)

    convert_video_to_audio(video_path, audio_path)

    audio = AudioSegment.from_wav(audio_path)
    total_duration = len(audio) / 1000.0
    transcribed_text = []
    chunk_durations = []

    recognizer = sr.Recognizer()
    chunk_start = 0
    previous_text = ""

    while chunk_start < total_duration:
        chunk_end = min(chunk_start + CHUNK_DURATION, total_duration)
        audio_chunk = audio[chunk_start * 1000:chunk_end * 1000]
        audio_chunk.export("temp.wav", format="wav")

        with sr.AudioFile("temp.wav") as source:
            chunk_audio_data = recognizer.record(source)

        text = transcribe_audio_chunk(chunk_audio_data, recognizer, language=video_language)
        if previous_text:
            text = remove_repeated_words(previous_text, text)
        transcribed_text.append(text)
        chunk_durations.append(chunk_end - chunk_start)
        previous_text = text

        chunk_start += CHUNK_DURATION - OVERLAP_DURATION

    subtitles_with_timing = generate_subtitles_with_timing(transcribed_text, chunk_durations, OVERLAP_DURATION)

    with open(subtitle_path, 'w', encoding='utf-8') as f:
        f.write(subtitles_with_timing)

    os.remove("temp.wav")
    os.remove(audio_path)  # Clean up the audio file after processing

    return subtitle_filename
