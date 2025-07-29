from resemblyzer import VoiceEncoder, preprocess_wav
import numpy as np
import os

def analyze_audio(audio_path: str) -> dict:
    """
    Analyze the audio file to detect if it is AI-generated (fake) or real.
    Returns a dictionary with the result and confidence score.
    """
    print(f"Analyzing audio at {audio_path}")

    # Load and preprocess the audio
    wav = preprocess_wav(audio_path)
    encoder = VoiceEncoder()
    embed = encoder.embed_utterance(wav)

    # For demo: compare to a reference embedding (should be a real sample from the same speaker)
    # You need to provide a path to a real reference audio file
    reference_path = "reference_real.wav"
    if not os.path.exists(reference_path):
        return {
            "is_fake": None,
            "confidence": 0.0,
            "message": "Reference audio not found. Cannot analyze."
        }
    ref_wav = preprocess_wav(reference_path)
    ref_embed = encoder.embed_utterance(ref_wav)

    # Calculate cosine similarity
    similarity = np.dot(embed, ref_embed) / (np.linalg.norm(embed) * np.linalg.norm(ref_embed))

    # Threshold for fake detection (tune this based on your data)
    threshold = 0.75
    is_fake = similarity < threshold
    confidence = 1 - similarity if is_fake else similarity

    return {
        "is_fake": is_fake,
        "confidence": float(confidence),
        "message": "This audio is likely AI-generated (fake)." if is_fake else "This audio is likely real."
    }