#!/usr/bin/env python3
"""baseline_check.py - an honest check of the SunPoint forecast against trivial forecasts.

Reads the stored moments (*.bau) and looks at where the signal really was 10 s after the spike:

    r = (actual - expected) / (spike - expected)      0 = back at the expected value, 1 = still at the spike

Three forecasts are scored under the same tolerance:
    model        the forecast stored in the moment (v0.5.x: "returns halfway", r = 0.5)
    Mean         "returns to the expected value"   (r = 0)
    Persistence  "stays where it is"               (r = 1)

A forecast that does not beat Mean and Persistence shows no understanding, whatever its hit rate is.

stdlib only. Reads numbers from the moments, nothing else.
Usage:  python3 -I baseline_check.py [data_dir]          data_dir defaults to ../src/window
        UNTIL='2026-11-23 13:07:00' python3 -I baseline_check.py data_dir     only moments up to that time
"""
import os, sys, json, zipfile, glob, statistics as st
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'src', 'window')
rows = []
for f in sorted(glob.glob(os.path.join(BASE, 'sunpoints', '*', '*.bau'))):
    try:
        with zipfile.ZipFile(f) as z: sp = json.loads(z.read('sunpoint.json'))
    except Exception: continue
    fo, fc, fx = sp.get('focus') or {}, sp.get('forecast_check'), sp.get('forecast') or {}
    if fo.get('src') != 'num' or not fc or fx.get('sd') is None or fo.get('exp') is None: continue
    v, e, pred, real, sd = float(fo['v']), float(fo['exp']), float(fc['pred']), float(fc['real']), float(fx['sd'])
    if abs(v - e) < 1e-9: continue
    rf = sp.get('reflex') or {}
    rows.append(dict(when=sp.get('when', '?'), ver=sp.get('v', '?'), k=fo['k'], v=v, e=e, pred=pred, real=real, sd=sd,
                     z=abs(v - e) / sd if sd else 0, r=(real - e) / (v - e), ok=bool(fc.get('ok')),
                     recall=bool(sp.get('recall')), reflex=rf.get('code', 'none') != 'none' if 'code' in rf else rf.get('kind') not in (None, 'нет', 'none')))
rows.sort(key=lambda x: x['when'])
UNTIL = os.environ.get('UNTIL')
if UNTIL: rows = [x for x in rows if x['when'] <= UNTIL]; print(f'cut: up to {UNTIL}')
n = len(rows)
print(f'moments with a checked forecast: {n}')
if not n: sys.exit(0)

def hit(real, p, sd): return abs(real - p) <= max(2 * sd, 0.15 * abs(p))          # the tolerance used by v0.5.x
def strict(real, p, v, e): return abs(real - p) <= 0.25 * abs(v - e)              # strict: a quarter of the surprise

def table(rs, title):
    m = len(rs)
    if not m: return
    a = dict(model=sum(hit(x['real'], x['pred'], x['sd']) for x in rs),
             pers=sum(hit(x['real'], x['v'], x['sd']) for x in rs),
             mean=sum(hit(x['real'], x['e'], x['sd']) for x in rs))
    s = dict(model=sum(strict(x['real'], x['pred'], x['v'], x['e']) for x in rs),
             pers=sum(strict(x['real'], x['v'], x['v'], x['e']) for x in rs),
             mean=sum(strict(x['real'], x['e'], x['v'], x['e']) for x in rs))
    err = lambda key: st.mean(abs(x['real'] - x[key]) / abs(x['v'] - x['e']) for x in rs)
    rr = [x['r'] for x in rs]
    cover = st.mean(min(1.0, 2 * max(2 * x['sd'], 0.15 * abs(x['pred'])) / abs(x['v'] - x['e'])) for x in rs)
    print(f'\n== {title}: n={m}')
    print(f'  v0.5 tolerance (wide):       model {a["model"]}/{m} = {100*a["model"]/m:.0f}%   Persistence {a["pers"]}/{m} = {100*a["pers"]/m:.0f}%   Mean {a["mean"]}/{m} = {100*a["mean"]/m:.0f}%')
    print(f'  strict tolerance (1/4 spike): model {s["model"]}/{m} = {100*s["model"]/m:.0f}%   Persistence {s["pers"]}/{m} = {100*s["pers"]/m:.0f}%   Mean {s["mean"]}/{m} = {100*s["mean"]/m:.0f}%')
    print(f'  mean error in units of surprise: model {err("pred"):.2f}   Persistence {err("v"):.2f}   Mean {err("e"):.2f}')
    print(f'  r (where it went): median {st.median(rr):.2f}, mean {st.mean(rr):.2f}, min {min(rr):.2f}, max {max(rr):.2f}')
    bins = [('below expected (r<-0.25)', lambda r: r < -0.25), ('back at expected (-0.25..0.25)', lambda r: -0.25 <= r < 0.25),
            ('middle (0.25..0.75)', lambda r: 0.25 <= r < 0.75), ('stayed at the spike (0.75..1.25)', lambda r: 0.75 <= r <= 1.25),
            ('kept growing (r>1.25)', lambda r: r > 1.25)]
    print('  ' + ' | '.join(f'{name}: {sum(1 for r in rr if f(r))}' for name, f in bins))
    print(f'  spike strength z: median {st.median(x["z"] for x in rs):.1f}, min {min(x["z"] for x in rs):.1f}, max {max(x["z"] for x in rs):.1f}')
    print(f'  share of the "expected…spike" segment covered by the v0.5 tolerance: {100*cover:.0f}% on average')

table(rows, 'all moments')
byk = defaultdict(list)
for x in rows: byk[x['k']].append(x)
for k, rs in sorted(byk.items(), key=lambda kv: -len(kv[1])): table(rs, f'signal {k}')

# would a learned return coefficient help? leave-one-out, per signal (median of the other moments of the same signal)
def loo(groups):
    errs = []
    for rs in groups:
        for i, x in enumerate(rs):
            rest = [y['r'] for j, y in enumerate(rs) if j != i]
            errs.append(abs(x['r'] - (st.median(rest) if rest else 0.5)))
    return st.mean(errs)
if n >= 5:
    fixed = st.mean(abs(x['r'] - 0.5) for x in rows)
    print(f'\n== learned return coefficient (leave-one-out): per signal {loo(byk.values()):.2f}, one for all {loo([rows]):.2f}, '
          f'fixed 0.5 {fixed:.2f}, Mean {st.mean(abs(x["r"]) for x in rows):.2f}, Persistence {st.mean(abs(x["r"] - 1) for x in rows):.2f}')

print('\n== by moment (time, signal, spike, expected, forecast, actual, r, z, true by v0.5)')
for x in rows:
    print(f"  {x['when'][11:]} {x['k']:<11} v={x['v']:<8g} e={x['e']:<8g} pred={x['pred']:<8g} real={x['real']:<8g} r={x['r']:+.2f} z={x['z']:.1f} {'yes' if x['ok'] else 'no'}{' recalled' if x['recall'] else ''}")
print(f"\nrecognition of a past state worked in {sum(x['recall'] for x in rows)} of {n}; reflexes fired: {sum(x['reflex'] for x in rows)}")
