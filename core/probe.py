"""SunPoint core 1.0 - a probe with a known cause, for the self-model indicator.

  python3 -I core/probe.py <folder> operator    run from a login shell: the operator's doing
  python3 -I core/probe.py <folder> body        run from a system timer or service: the body's doing

Burns one CPU core for 4 seconds and records what the correct answer is. core/measure.py
then compares the answer of the self-model with it. The probe says nothing to the core.
"""
import json
import os
import sys
import time

if __name__ == '__main__':
    d, expected = sys.argv[1], sys.argv[2]
    assert expected in ('operator', 'body'), expected
    t = time.time()
    with open(os.path.join(d, 'probe.jsonl'), 'a', encoding='utf-8') as f:
        f.write(json.dumps({'t': round(t, 1), 'expected': expected, 'by': 'probe'}) + '\n')
    while time.time() - t < 4:
        pass
