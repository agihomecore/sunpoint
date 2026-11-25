"""SunPoint core 1.0 - growth: the system changes its own surface numbers toward the goal.

  python3 -I core/grow.py <folder>

One cycle: read the raw stream of the last days, replay it through the same senses, workspace
and forecast with the present numbers and with mutated ones, keep a mutation only if it is
better on the first 70 % of the data AND on the last 30 % it has not seen. The result goes to
genome.json, which the running core takes up within a minute. Every cycle is written to
grow.jsonl, accepted or not.

What may change: parts.G inside parts.BOUNDS. What may not: the moment of +-10 s, the strict
test of a forecast, the code. Stdlib only; no network; writes only inside <folder>.
"""
import glob
import json
import os
import random
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parts                                                   # noqa: E402
from parts import Senses, Forecast, Z_UNIT                     # noqa: E402
from workspace import Workspace                                # noqa: E402

MIN_CHECKS = 30        # fewer checks than this say nothing
TRIES = 12             # mutations per cycle
GAIN = 0.02            # a mutation must be better by this much


def load(d, days=3):
    rows = []
    for p in sorted(glob.glob(os.path.join(d, 'raw-*.jsonl')))[-days:]:
        with open(p, encoding='utf-8') as f:
            for line in f:
                try:
                    r = json.loads(line)
                    rows.append((r[0], dict(zip(parts.FLOOR, r[1:]))))
                except (ValueError, IndexError):
                    pass
    causes = {}
    for name in ('moments.jsonl', 'below.jsonl'):
        p = os.path.join(d, name)
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                for line in f:
                    try:
                        x = json.loads(line)
                    except ValueError:
                        continue
                    who = x.get('who') or (x.get('cause_after') or x.get('cause') or {}).get('who')
                    if who:
                        causes[(int(x['t']), x.get('focus'))] = who
    return rows, causes


def replay(rows, g, causes):
    """Run the stored stream through the parts with the numbers g. Returns (score, facts)."""
    keep = dict(parts.G)
    parts.G.update(g)
    try:
        se = Senses()
        fc = Forecast(se)
        ws = Workspace(tempfile.gettempdir(), ignite=g['ignite'])
        ws.log = lambda *a: None

        def who(c, t):
            k = c['data']['focus']
            w = next((causes[(int(t) + dt, k)] for dt in (0, -1, 1, -2, 2) if (int(t) + dt, k) in causes), 'unknown')
            c['data']['cause'] = {'who': w}
            c['sal'] *= parts.weight(w)

        ws.modulate(who)
        ws.subscribe(fc)
        last = None
        for t, vals in rows:
            if last is not None and t - last > 5:             # a gap: the moment in the field is lost
                ws.open = None
            last = t
            for k, v, e, z in se.feel(vals, t):
                ws.post('senses', 'spike', abs(z) / Z_UNIT, {'focus': k, 'v': v, 'e': e, 'z': z})
            ws.tick(t)
        hours = max(len(rows) / 3600, 1e-6)
        per_h = ws.n_moments / hours
        if fc.n < MIN_CHECKS or not fc.e_pick:
            return None, {'checks': fc.n, 'per_h': round(per_h, 2)}
        skill = 1 - fc.e_model / fc.e_pick
        score = skill - 0.1 * max(0.0, per_h - 3.0) - 0.2 * max(0.0, 0.5 - per_h)
        return score, {'checks': fc.n, 'per_h': round(per_h, 2), 'skill': round(skill, 3), 'score': round(score, 3)}
    finally:
        parts.G.clear()
        parts.G.update(keep)


def mutate(g, rnd):
    c = dict(g)
    for k in rnd.sample(sorted(parts.BOUNDS), rnd.choice((1, 1, 2))):
        lo, hi = parts.BOUNDS[k]
        v = min(hi, max(lo, c[k] * rnd.choice((0.7, 0.85, 1.15, 1.4))))
        c[k] = int(round(v)) if k == 'r_keep' else round(v, 4)
    return c


def cycle(d, seed=None):
    rnd = random.Random(seed)
    rows, causes = load(d)
    gp = os.path.join(d, 'genome.json')
    try:
        with open(gp, encoding='utf-8') as f:
            cur = json.load(f)
    except (OSError, ValueError):
        cur = {'version': 0, 'g': dict(parts.G)}
    g = dict(parts.G)
    g.update({k: v for k, v in cur['g'].items() if k in parts.BOUNDS})
    rec = {'t': round(time.time(), 1), 'rows': len(rows), 'version': cur['version'], 'accepted': False}
    cut = int(len(rows) * 0.7)
    train, test = rows[:cut], rows[cut:]
    s0, f0 = replay(train, g, causes)
    t0, h0 = replay(test, g, causes)
    rec['now'] = {'train': f0, 'test': h0}
    if s0 is None or t0 is None:
        rec['why'] = f'too little data: at least {MIN_CHECKS} checks are needed in each part'
    else:
        best, bs, bf = None, s0, None
        for _ in range(TRIES):
            c = mutate(g, rnd)
            s, f = replay(train, c, causes)
            if s is not None and s > bs + GAIN:
                best, bs, bf = c, s, f
        if best is None:
            rec['why'] = 'no mutation was better on the first part'
        else:
            t1, h1 = replay(test, best, causes)
            rec['try'] = {'g': best, 'train': bf, 'test': h1}
            if t1 is not None and t1 >= t0 + GAIN / 2:
                rec['accepted'] = True
                new = {'version': cur['version'] + 1, 't': rec['t'], 'g': best, 'from': g,
                       'gain': {'train': round(bs - s0, 3), 'test': round(t1 - t0, 3)}}
                tmp = gp + '.tmp'
                with open(tmp, 'w', encoding='utf-8') as f:
                    json.dump(new, f)
                os.replace(tmp, gp)
            else:
                rec['why'] = 'better on the first part, not on the part it had not seen'
    with open(os.path.join(d, 'grow.jsonl'), 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, separators=(',', ':')) + '\n')
    if s0 is not None:                                    # the first dream: a free flight beyond the bounds
        with open(os.path.join(d, 'dreams.jsonl'), 'a', encoding='utf-8') as f:
            for _ in range(2):
                k = rnd.choice(sorted(parts.BOUNDS))
                c = dict(g)
                c[k] = g[k] * rnd.choice((0.4, 2.5))
                c[k] = int(round(c[k])) if k == 'r_keep' else round(c[k], 4)
                s, fact = replay(train, c, causes)
                f.write(json.dumps({'t': rec['t'], 'kind': 'improve', 'what_if': {k: c[k]}, 'now': {k: g[k]},
                                    'score_now': round(s0, 3), 'score_then': None if s is None else round(s, 3),
                                    'facts': fact, 'note': 'outside the bounds: a dream, not applied'}) + '\n')
    for p in sorted(glob.glob(os.path.join(d, 'raw-*.jsonl')))[:-4]:   # the raw stream is kept for four days
        os.remove(p)
    return rec


def selftest():
    d = tempfile.mkdtemp(prefix='spgrow_')
    rnd = random.Random(7)
    t = 1.0e9
    with open(os.path.join(d, 'raw-20010909.jsonl'), 'w') as f:
        level = 0.0
        for i in range(40000):                            # a quiet body with a load every 100 s that decays slowly
            if i % 100 == 0 and i:
                level = 40.0
            level *= 0.93
            v = {k: 1.0 + rnd.gauss(0, 0.01) for k in parts.FLOOR}
            v['cpu'] = 5.0 + rnd.gauss(0, 0.3) + level
            f.write(json.dumps([t + i] + [round(v[k], 3) for k in parts.FLOOR]) + '\n')
    r = cycle(d, seed=1)
    assert r['now']['train'] and r['now']['train']['checks'] >= MIN_CHECKS, r
    again = cycle(d, seed=2)
    assert again['version'] == (1 if r['accepted'] else 0), again
    with open(os.path.join(d, 'dreams.jsonl')) as f:
        assert len(f.readlines()) == 4, 'two dreams per cycle with data'
    print('grow selftest ok:', json.dumps({'first': r['now']['train'], 'accepted': r['accepted'],
                                           'try': (r.get('try') or {}).get('test'), 'why': r.get('why')}))


if __name__ == '__main__':
    if sys.argv[1:2] == ['--selftest']:
        selftest()
    else:
        print(json.dumps(cycle(sys.argv[1])))
