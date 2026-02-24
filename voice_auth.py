import os
from resemblyzer import VoiceEncoder, preprocess_wav
import numpy as np
import torch

try:
    print("Loading Voice Encoder on cpu...")
    encoder = VoiceEncoder(device="cpu")
except Exception as e:
    print(f"Warning: Voice auth unavailable: {e}")
    encoder = None


OWNER_VOICE = "E:/Data Science/Arfy-Ai/Audio/owner_voice.npy"
SAMPLES_FOLDER = "E:/Data Science/Arfy-Ai/Audio/samples/"

def enroll_voice():
    if not os.path.exists(SAMPLES_FOLDER):
        os.makedirs(SAMPLES_FOLDER)
    
    samples = [f for f in os.listdir(SAMPLES_FOLDER) if f.endswith('.wav')]

    if not samples:
        print("No voice samples found. Please record at least one sample.")
        return False
    
    print(f"Found {len(samples)} voice samples, enrolling...")
    embeddings = []

    for sample in samples:
        path = SAMPLES_FOLDER + sample
        wav = preprocess_wav(path)
        embedding = encoder.embed_utterance(wav)
        embeddings.append(embedding)

    avg_embedding = np.mean(embeddings, axis=0)
    np.save(OWNER_VOICE, avg_embedding)
    print("Voice enrolled successfully!")
    return True

def is_owner_voice(audio_path, threshold=0.50):
    if not os.path.exists(OWNER_VOICE):
        print("No enrolled voice found. Please enroll your voice first.")
        return True
    
    try:
        owner_embedding = np.load(OWNER_VOICE)
        wav = preprocess_wav(audio_path)
        current_embedding = encoder.embed_utterance(wav)
        similarity = np.dot(owner_embedding, current_embedding)

        print(f"Voice similarity: {similarity:.2f}")
        return similarity >= threshold
    
    except Exception as e:
        print(f"Voice auth error: {e}")
        return True
    