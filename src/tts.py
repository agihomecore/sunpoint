#!/usr/bin/env python3
"""tts.py - one sentence to a WAV file through the Piper Python API.

Why not the piper command line: on the reference server the command-line tool of piper-tts 1.8 returned about
0.8 s of audio for any text, so the loudspeakers played a fragment instead of a sentence. The Python API of the
same package and the same voice model gives the whole sentence.

Usage:  <python with piper-tts installed> tts.py MODEL.onnx OUT.wav "text" [speed=1.0] [volume=1.0]
        speed is Piper's length scale: 1.1 is ten percent slower.
The file starts with a short silence so that loudspeakers which wake up on sound do not swallow the first word.
"""
import sys, wave
from piper import PiperVoice

model, out, text = sys.argv[1], sys.argv[2], sys.argv[3]
speed = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
volume = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
LEAD, GAP, TAIL = 0.35, 0.4, 0.2          # seconds of silence: before, between sentences, after

voice = PiperVoice.load(model)
try:
    from piper import SynthesisConfig
    cfg = SynthesisConfig(length_scale=speed, volume=volume)
except Exception:                          # an older piper without SynthesisConfig: default speed and volume
    cfg = None
chunks = list(voice.synthesize(text, cfg) if cfg else voice.synthesize(text))
if not chunks: sys.exit(1)
c = chunks[0]; rate, width, chans = c.sample_rate, c.sample_width, c.sample_channels
def silence(sec): return b'\x00' * (int(rate * sec) * width * chans)
with wave.open(out, 'wb') as w:
    w.setframerate(rate); w.setsampwidth(width); w.setnchannels(chans)
    w.writeframes(silence(LEAD))
    for i, ch in enumerate(chunks):
        if i: w.writeframes(silence(GAP))
        w.writeframes(ch.audio_int16_bytes)
    w.writeframes(silence(TAIL))
