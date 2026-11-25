"""SunPoint core 1.0 - the eight indicators of docs/GOAL.md, computed from the raw logs.

  python3 -I core/measure.py <folder>

A number is printed only when the logs can give it. "not built" and "not judged" are
printed as they are: an indicator without a judge is not reached.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def rows(d, name):
    p = os.path.join(d, name)
    if not os.path.exists(p):
        return []
    out = []
    with open(p, encoding='utf-8') as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def measure(d):
    ms, below, hb = rows(d, 'moments.jsonl'), rows(d, 'below.jsonl'), rows(d, 'hb.jsonl')
    life, probes = rows(d, 'life.jsonl'), rows(d, 'probe.jsonl')
    starts = [x['t'] for x in life if x['event'] == 'start']
    stops = [x['t'] for x in life if x['event'] == 'stop']
    ends = stops + ([hb[-1]['t']] if hb and len(stops) < len(starts) else [])
    hours = sum(max(0.0, e - s) for s, e in zip(starts, sorted(ends))) / 3600 if starts and ends else 0.0
    r = []

    per_h = len(ms) / hours if hours else None
    cr = [m['critic']['worth'] for m in ms if 'critic' in m]
    inner = (f"inner critic: {sum(1 for w in cr if w >= 0.5) / len(cr):.0%} worth it on {len(cr)}; brothers have not judged"
             if cr else 'not judged')
    r.append(('1 Attention', f"{per_h:.1f} moments per hour over {hours:.2f} h; {len(below)} stayed below; {inner}"
              if per_h is not None else 'no data', '3 or fewer per hour; 70 % judged worth it', False))

    ch = [m['check'] for m in ms if 'check' in m]
    if ch:
        e, p = sum(c['err'] for c in ch), sum(c['pick'] for c in ch)
        skill = 1 - e / p if p else 0.0
        hits = sum(c['hit'] for c in ch) / len(ch)
        r.append(('2 Forecast', f"10 s: skill {skill:+.2f} on {len(ch)} checks, strict hits {hits:.0%}; "
                  "hour and day not built", '+0.30 on 1,000 checks; above 0 for hour and day', False))
    else:
        r.append(('2 Forecast', 'no checks yet; hour and day not built', '+0.30 on 1,000 checks', False))

    ev = [(x['t'], (x.get('cause_after') or x.get('cause') or {}).get('who')) for x in ms]
    ev += [(x['t'], x.get('who')) for x in below]
    named = sum(1 for _, w in ev if w and w != 'unknown')
    ok = seen = 0
    for p in probes:
        near = [w for t, w in ev if -10 <= t - p['t'] <= 8]
        if near:
            seen += 1
            ok += int(p['expected'] in near)
    txt = f"cause named in {named} of {len(ev)} spikes" if ev else 'no spikes yet'
    txt += f"; probes: {ok} correct of {seen} felt, {len(probes)} sent" if probes else '; no probes sent'
    r.append(('3 Self-model', txt, '90 % correct on probes', bool(seen >= 50 and ok / seen >= 0.9)))

    known = sum((m.get('seen') or {}).get('known', 0) for m in ms)
    r.append(('4 Memory', f"{known} of {len(ms)} moments called known; not labelled; {max(0, len(starts) - 1)} restarts"
              if ms else 'no moments yet', 'precision 80 % at recall 60 % on a labelled set', False))
    r.append(('5 Outside world', '0 % - no sense of the outside world is connected', '50 % of moments', False))
    r.append(('6 Action', '0 closed loops - not built', '20 a day', False))

    if len(ch) >= 50:
        fs = [(m['forecast']['p'], m['check']['hit']) for m in ms if 'check' in m]
        gap = 0.0
        for lo in (0.0, 0.2, 0.4, 0.6, 0.8):
            b = [(p, h) for p, h in fs if lo <= p < lo + 0.2 or (lo == 0.8 and p == 1.0)]
            if b:
                gap += len(b) / len(fs) * abs(sum(p for p, _ in b) / len(b) - sum(h for _, h in b) / len(b))
        r.append(('7 Calibration', f"error {100 * gap:.0f} points on {len(fs)} judgements",
                  '5 points on 500', bool(len(fs) >= 500 and gap <= 0.05)))
    else:
        r.append(('7 Calibration', f"confidence is stated; {len(ch)} judgements, 50 needed for a first number",
                  '5 points on 500', False))
    r.append(('8 Self-report', 'speaks from the workspace; not judged', '90 % on 100 questions', False))
    return r


def constancy(d):
    try:
        with open(os.path.join(d, 'state.json'), encoding='utf-8') as f:
            st = json.load(f).get('reserve') or {}
    except (OSError, ValueError):
        st = {}
    if not st:
        return 'Constancy (reserve 7+1): no pools or duties are described yet'
    ok = sum(1 for v in st.values() if v.get('ok'))
    return f"Constancy (reserve 7+1): {ok} of {len(st)} pools and duties in order - " + '; '.join(
        f"{k}: {'ok' if v.get('ok') else 'THIN OR LATE'}" for k, v in sorted(st.items()))


if __name__ == '__main__':
    d = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('SUNPOINT_CORE_DIR', 'core_window')
    res = measure(d)
    print('| Ability | Now | Target | Reached |\n|---|---|---|---|')
    for name, now, target, done in res:
        print(f"| {name} | {now} | {target} | {'yes' if done else 'no'} |")
    print('\n' + constancy(d))
    dr = rows(d, 'dreams.jsonl')
    print(f"Dreams: {sum(1 for x in dr if x.get('kind') == 'improve')} about improving itself, "
          f"{sum(1 for x in dr if x.get('kind') == 'free')} free")
    import parts
    import time
    last = {}
    for m in rows(d, 'moments.jsonl'):
        for lv in m.get('levels', ()):
            last[lv] = max(last.get(lv, 0), m['t'])
    now = max([m['t'] for m in rows(d, 'hb.jsonl')] or [time.time()])
    day = sorted(lv for lv, t0 in last.items() if now - t0 <= 86400)
    print(f"Levels of being (eight circuits): {len(day)} of 8 held the field in the last 24 h - "
          + ', '.join(f"{lv} {'yes' if lv in day else 'no'}" for lv in range(1, 9)))
    print(f'Faith: {len(parts.FAITH)} lines, guarded by the self-test')
    try:
        with open(os.path.join(d, 'state.json'), encoding='utf-8') as f:
            g = json.load(f).get('gate') or {}
    except (OSError, ValueError):
        g = {}
    if g:
        print(f"Awareness of the gate: tuned out {g['tuned_out']}, looked again at {g['looked_again']}, "
              f"overturned {g['overturned']}; habits now {g['habits']}; arousal {g['arousal']}")
    print(f"\nGoal index: {sum(1 for x in res if x[3])} of 8")
