# path: chatterbox/example_tts.py
import torchaudio as ta
import torch
from chatterbox.tts import ChatterboxTTS

# Automatically detect the best available device
if torch.cuda.is_available():
    device = "cuda"
elif torch.backends.mps.is_available():
    device = "mps"
else:
    device = "cpu"

print(f"Using device: {device}")

model = ChatterboxTTS.from_pretrained(device=device)

text = """If you want this ai agent for free DM me"""

# If you want to synthesize with a different voice, specify the audio prompt
AUDIO_PROMPT_PATH = "voice.wav"  # Replace with your Peter Griffin voice sample
wav = model.generate(text, audio_prompt_path=AUDIO_PROMPT_PATH)
ta.save("content_voiceover.wav", wav, model.sr)

print("Voiceover generated successfully! Saved as 'content_voiceover.wav'")


