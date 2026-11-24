#!/usr/bin/env python3
"""consolidate.py - memory consolidation for SunPoint ("sleep").

Model of consciousness: Khamzin Bauyrzhan Galymzhanovich.   Code: AISun.   MIT licence.

Memory tiers (NATS JetStream streams):
    SP_CACHE  everything the eyes saw in the last hours (frame vectors, minute descriptions, pixel sketches)
    SP_LTM    long-term memory   <- "hour": the last hour of the cache -> keyframes, top labels, a short summary
    SP_SUB    subconscious       <- "sub":  the last 4 hours of long-term memory -> 8 centres of meaning (k-means)

Rule of the model: cache -> long-term at least once an hour; long-term -> subconscious at least every 4 hours.
Vectors and labels only. Background work is done in vectors; words appear only as a short summary for other services.

Usage:  python consolidate.py hour      (cron: 7 * * * *)
        python consolidate.py sub       (cron: 17 */4 * * *)
Needs: nats-py, numpy; a NATS server with JetStream on 127.0.0.1:4222.
"""
import asyncio, json, base64, sys, time, os
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict
import numpy as np
import nats
from nats.js.api import ConsumerConfig, DeliverPolicy

TZ = timezone(timedelta(hours=float(os.environ.get('SUNPOINT_TZ_HOURS', '0'))))
LOG = os.environ.get('CONSOLIDATE_LOG', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'consolidate.log'))
def log(m):
    with open(LOG, 'a', encoding='utf-8') as f: f.write(f'{datetime.now(TZ):%Y-%m-%d %H:%M:%S} {m}\n')

def vec(b64): return np.frombuffer(base64.b64decode(b64), dtype=np.float16).astype(np.float32)
def enc(v): return base64.b64encode(np.asarray(v, np.float16).tobytes()).decode()

async def read(js, stream, subject, since_s, limit=200000):
    start = datetime.now(timezone.utc) - timedelta(seconds=since_s)
    sub = await js.pull_subscribe(subject, durable=None, stream=stream,
                                  config=ConsumerConfig(deliver_policy=DeliverPolicy.BY_START_TIME, opt_start_time=start.isoformat()))
    out = []
    while len(out) < limit:
        try: msgs = await sub.fetch(500, timeout=2)
        except Exception: break
        for m in msgs:
            out.append((m.subject, json.loads(m.data))); await m.ack()
        if len(msgs) < 500: break
    await sub.unsubscribe()
    return out

def keyframes(items, thr=0.97):
    """Ключевые кадры: оставляем кадр, если он заметно отличается от последнего оставленного."""
    kept = []; last = None
    for d in items:
        v = vec(d['v'])
        if last is None or float(v @ last) < thr:
            kept.append((d['t'], v)); last = v
    return kept

def nearest_pix(pl, times):
    """Пиксельный рисунок 64×64, ближайший к каждому ключевому кадру (не больше 120 в час на камеру)."""
    if not pl: return []
    pl = sorted(pl); ts_ = np.array([t for t, _ in pl]); out = []
    for t in times:
        i = int(np.argmin(np.abs(ts_ - t)))
        if abs(ts_[i] - t) <= 2: out.append([round(t, 1), pl[i][1]])
    return out

async def hour(js):
    frames = await read(js, 'SP_CACHE', 'sp.frames.>', 3600)
    descs = await read(js, 'SP_CACHE', 'sp.desc.>', 3600)
    pix = await read(js, 'SP_CACHE', 'sp.pix.>', 3600)
    pby = defaultdict(list)
    for s_, d in pix: pby[d['cam']].append((d['t'], d['jpg']))
    by = defaultdict(list); dby = defaultdict(list)
    for s, d in frames: by[d['cam']].append(d)
    for s, d in descs: dby[d['cam']].append(d)
    now = time.time(); n_pub = 0
    for cam in sorted(set(by) | set(dby)):
        kf = keyframes(sorted(by[cam], key=lambda d: d['t']))
        labels = Counter(l['ru'] for d in dby[cam] for l in d.get('labels', [])[:1])
        recs = [d['recognized'] for d in dby[cam] if d.get('recognized')]
        bright = [d.get('brightness', 0) for d in dby[cam]]
        summary = dict(kind='ltm.hour', cam=cam, place=(dby[cam][0]['place'] if dby[cam] else cam),
                       t_from=round(now - 3600), t_to=round(now), frames=len(by[cam]), minutes=len(dby[cam]),
                       keyframes=len(kf), compress=round(len(by[cam]) / max(1, len(kf)), 1),
                       top_labels=labels.most_common(4), recognized=len(recs),
                       brightness=[round(min(bright), 1), round(max(bright), 1)] if bright else None,
                       words=(f"{cam}: за час {len(dby[cam])} мин наблюдения, чаще всего «{labels.most_common(1)[0][0]}», "
                              f"{len(kf)} ключевых кадров из {len(by[cam])}, узнаваний {len(recs)}") if labels else f"{cam}: нет данных",
                       kf_t=[round(t, 1) for t, _ in kf][:400], kf_v=[enc(v) for _, v in kf][:400],
                       kf_pix=nearest_pix(pby[cam], [t for t, _ in kf][:120]))
        await js.publish(f'sp.ltm.{cam}', json.dumps(summary, ensure_ascii=False).encode()); n_pub += 1
        log(f'hour {cam}: frames={len(by[cam])} kf={len(kf)} minutes={len(dby[cam])} recognized={len(recs)}')
    return n_pub

async def sub4(js):
    items = await read(js, 'SP_LTM', 'sp.ltm.>', 4 * 3600)
    by = defaultdict(list)
    for s, d in items: by[d['cam']].append(d)
    for cam, hs in by.items():
        V = np.array([vec(v) for h in hs for v in h.get('kf_v', [])]) if hs else np.zeros((0, 512))
        cents = []
        if len(V):   # простые центры смыслов: k-means на 8 центров, 10 итераций
            k = min(8, len(V)); C = V[np.random.default_rng(0).choice(len(V), k, replace=False)]
            for _ in range(10):
                a = np.argmax(V @ C.T, 1)
                C = np.array([V[a == i].mean(0) if (a == i).any() else C[i] for i in range(k)])
                C /= np.linalg.norm(C, axis=1, keepdims=True) + 1e-9
            cnt = np.bincount(np.argmax(V @ C.T, 1), minlength=k)
            cents = [dict(weight=int(c), v=enc(C[i])) for i, c in enumerate(cnt)]
        labels = Counter()
        for h in hs:
            for l, n in h.get('top_labels', []): labels[l] += n
        rec = dict(kind='sub.4h', cam=cam, hours=len(hs), keyframes=int(len(V)), centers=cents,
                   top_labels=labels.most_common(5),
                   words=f"{cam}: за 4 часа {len(hs)} ч, привычная картина — «{labels.most_common(1)[0][0] if labels else '—'}», центров смысла {len(cents)}")
        await js.publish(f'sp.sub.{cam}', json.dumps(rec, ensure_ascii=False).encode())
        log(f'sub {cam}: hours={len(hs)} kf={len(V)} centers={len(cents)}')

async def main(mode):
    nc = await nats.connect('nats://127.0.0.1:4222', name=f'sp_consolidate_{mode}')
    js = nc.jetstream()
    try:
        if mode == 'hour': await hour(js)
        elif mode == 'sub': await sub4(js)
    finally:
        await nc.drain()

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'hour'
    ann = os.environ.get('SUNPOINT_ANNOUNCE')          # efference copy: tell the observer that scheduled work starts now
    if ann:
        try:
            with open(ann, 'a', encoding='utf-8') as f:
                f.write(json.dumps(dict(t=time.time(), what=f'memory consolidation ({mode})', for_s=120)) + '\n')
        except Exception: pass
    try: asyncio.run(main(mode))
    except Exception as e: log(f'{mode} error {e!r}'); raise
