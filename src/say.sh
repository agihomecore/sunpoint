#!/bin/bash
# say.sh - speak one sentence on the loudspeakers.  usage: say.sh "text"
# Piper (neural voice) through its Python API if $VOICE_PYTHON and $VOICE_MODEL are set, otherwise espeak-ng.
#   VOICE_PYTHON=/path/to/venv/bin/python   (a Python with piper-tts installed)   VOICE_MODEL=/path/to/voice.onnx
#   VOICE_SPEED=1.1   (Piper length scale: above 1 is slower)   VOICE_VOLUME=0.7
#   VOICE_DEVICE=plughw:1,0   (ALSA device; default: the system default)   VOICE_ESPEAK_LANG=en
# The piper command line is not used: see tts.py for the reason.
HERE="$(cd "$(dirname "$0")" && pwd)"
T=$(mktemp /tmp/say_XXXX.wav)
if ! { [ -x "$VOICE_PYTHON" ] && [ -f "$VOICE_MODEL" ] &&
       "$VOICE_PYTHON" -I "$HERE/tts.py" "$VOICE_MODEL" "$T" "$1" "${VOICE_SPEED:-1.0}" "${VOICE_VOLUME:-1.0}" 2>/dev/null; }; then
  espeak-ng -v "${VOICE_ESPEAK_LANG:-en}" -s 150 "$1" --stdout > "$T"
fi
if [ -n "$VOICE_DEVICE" ]; then aplay -q -D "$VOICE_DEVICE" "$T"; else aplay -q "$T"; fi
rm -f "$T"
