#!/bin/bash
# say.sh - speak one sentence on the loudspeakers.  usage: say.sh "text"
# Piper (neural voice) if $VOICE_PIPER and $VOICE_MODEL point to it, otherwise espeak-ng.
#   VOICE_PIPER=/path/to/venv/bin/piper   VOICE_MODEL=/path/to/voice.onnx
#   VOICE_DEVICE=plughw:1,0   (ALSA device; default: the system default)   VOICE_ESPEAK_LANG=en
T=$(mktemp /tmp/say_XXXX.wav)
if [ -x "$VOICE_PIPER" ] && [ -f "$VOICE_MODEL" ]; then
  echo "$1" | "$VOICE_PIPER" -m "$VOICE_MODEL" -f "$T" -q 2>/dev/null
else
  espeak-ng -v "${VOICE_ESPEAK_LANG:-en}" -s 150 "$1" --stdout > "$T"
fi
if [ -n "$VOICE_DEVICE" ]; then aplay -q -D "$VOICE_DEVICE" "$T"; else aplay -q "$T"; fi
rm -f "$T"
