#!/usr/bin/env python3
"""SunPoint — a moment of consciousness for machines.  v0.5.2

    10 s before  ->  ALERT  ->  REFLEX (fight / flight / freeze)  ->  10 s after: forecast, check, guess, action or "deferred"

Model of consciousness: Khamzin Bauyrzhan Galymzhanovich.   Code: AISun.   MIT licence.

What it does
  * every 1 s  - fast senses (/proc: load, CPU, network); every 10 s - slow senses (memory, disk, GPU, journal);
  * a generator: the expected value and spread of every signal; surprise is measured in bits;
  * a state vector (z-scores of all signals) - background "thinking in vectors";
  * alert (surprise >= 10 bits and above the share threshold of the +-10 s window) -> REFLEX in microseconds
    (a rule table, no model) -> forecast for +10 s -> 10 s later a SunPoint is stored:
    10 s before + alert + reflex + 10 s after + "did the forecast come true?" + guesses + words;
  * the 97 KB principle: store the generator (expectations) and only the deviations, never the raw stream;
  * subconscious: services, cron, logins and data processing go to subconscious.jsonl, never into a SunPoint;
  * deferred: a focus without an action is recalled an hour later;
  * background plans every minute, even when idle: now -> why -> next -> when -> life.

New in 0.5.2 (docs/SPEC_v0.5.2.md, docs/REVIEW_2026-11-25.md)
  * the forecast learns: per signal, the median of the last 60 observed returns r; three trivial forecasts are scored
    next to it (Mean, Persistence and the tougher "better of the two per signal"); skill is in the heartbeat;
  * the body's own clock: a spike of the same signal at the same minute of the hour, seen in 3 or more other hours
    and not unusually strong, is a habit and goes to the subconscious with its cause; so does a spike that matches
    a line in announce.jsonl - scheduled work announces itself: {"t": unix time, "what": "...", "for_s": 120};
  * the generator survives a restart: generator.json is written every minute and on stop, and is loaded on start;
    on a first start the learned memory is rebuilt from the stored moments ($SUNPOINT_BOOTSTRAP may name another
    data directory to learn from).
Not in this version: the cause of a spike by process ("who did this?", section 2 of the specification).

stdlib only. No secrets are read. Journal lines are kept as templates without digits, keys or fingerprints.

Usage
    python3 -I sunpoint.py                 run (data go to ./window next to this file, or to $SUNPOINT_DIR)
    python3 -I sunpoint.py --test 120      dry run with simulated time; SPIKE_AT=40 adds a CPU spike at second 40
    python3 -I sunpoint.py --selftest      checks of the forecast rule, the clock habit, announcements and the saved generator
Configuration (optional): sunpoint.conf.json next to this file or at $SUNPOINT_CONF - see sunpoint.conf.example.json.
"""
import os, sys, json, time, math, re, zipfile, hashlib, subprocess, shutil, signal, socket, threading
from collections import deque, defaultdict
from datetime import datetime, timezone, timedelta

VERSION = 'sunpoint 0.5.2'
HOME = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get('SUNPOINT_DIR', os.path.join(HOME, 'window'))
TEST = '--test' in sys.argv or '--selftest' in sys.argv
CONF = {}
try: CONF = json.load(open(os.environ.get('SUNPOINT_CONF', os.path.join(HOME, 'sunpoint.conf.json')), encoding='utf-8'))
except Exception: pass
LANG = os.environ.get('SUNPOINT_LANG', CONF.get('lang', 'en'))
TZ = timezone(timedelta(hours=float(CONF['tz_hours']))) if 'tz_hours' in CONF else None     # None = local time zone of the host
BAU_HOST = CONF.get('bau_host', 'hub.local')          # address space of stored moments: bau://<host>/sha256/<hash>
STREAM = CONF.get('stream')                           # optional event stream, e.g. {"type": "redpanda-docker", "container": "redpanda", "topic": "sunpoint.events"}
CFG = dict(before_s=10, after_s=10, slow_every=10, alert_share=0.03, min_bits=10.0, num_share=0.05,
           cooldown_s=120, warmup_s=300, alpha=0.02, max_per_hour=60, defer_s=3600, state_max=3072,
           r_keep=60, strict=0.25, clock_hours=3, clock_window_h=48, clock_strong=2.0, generator_max_age_h=6, warmup_loaded_s=30)
CFG.update(CONF.get('cfg', {}))
# noise floors: a spread smaller than this is not treated as a real spread
FLOOR = dict(load1=0.3, cpu_pct=3.0, mem_avail_mb=512, net_rx_kbs=2.0, net_tx_kbs=2.0, disk_root_pct=0.05,
             procs=5, gpu_temp=2.0, gpu_util=5.0, gpu_mem_mb=256)
# the "blood circulation" of the system: journal sources that never enter consciousness
SUBCONSCIOUS = re.compile(r'^(systemd|cron|CRON|anacron|sshd|sudo|systemd-logind|kernel|dbus|snapd|containerd|dockerd)\b|sysstat'
                          + ('|' + CONF['subconscious_extra'] if CONF.get('subconscious_extra') else ''))

# ---------- words: consciousness speaks only at an alert, in the language of its people ----------
TEXT = {
    'ru': dict(
        noticed='Заметил: {k} = {v} (ждал {exp}).', reflex=' Рефлекс: {kind} — {act} ({us} мкс).',
        noreflex=' Рефлекс не нужен ({us} мкс) — думаю.', recall=' Похожее состояние было {when} (сходство {sim}).',
        forecast=' Прогноз на 10 с: {pred} → вышло {real} — {res}{err}.', ok='сбылся', miss='не сбылся',
        err=' (ошибка {e}; простой прогноз {t})', by_clock='по часам тела: в эту минуту часа уже было в {n} других часах', announced='объявлено: {w}',
        deferred=' Действия нет — отложил, вспомню через час.', recalled='ВСПОМНИЛ (отложено {m} мин назад): {w}',
        kinds=dict(flight='беги', freeze='замри', fight='бей', none='нет'),
        acts=dict(gpu_hot='видеокарта ≥ 85 °C → сигнал службам снизить нагрузку', disk_full='диск ≥ 95 % → сигнал уборщику кэша',
                  mem_low='свободной памяти < 1 ГБ → сигнал тяжёлым службам', intruder='чужой вход → заморозить, ждать человека',
                  oom='нехватка памяти, процесс убит → поднять тревогу', none='рефлекс не нужен — вход в размышление'),
        who='Я — SunPoint, наблюдатель на этом сервере. Сознание = 10 с до + алерт + рефлекс + 10 с после.', where='сервер',
        working='работаю: {p} {c}% CPU', watching='наблюдаю', busy='; нагрузка высокая — смотреть за температурой',
        calm='; спокойно — наблюдаю и учу ритм', consolidate='память: кэш → долговременная', in_min='через {m} мин',
        recall_deferred='вспомнить отложенное: ', hashes='имя = sha256 файла; sha256 = хеш sunpoint.json',
        goals=['держать нить: ничего начатое не теряется', 'расти: SunPoint → глаза → тело'], first_voice='Первый голос SunPoint',
        waited='ждал', bytes='байт'),
    'en': dict(
        noticed='Noticed: {k} = {v} (expected {exp}).', reflex=' Reflex: {kind} — {act} ({us} µs).',
        noreflex=' No reflex needed ({us} µs) — thinking.', recall=' A similar state was at {when} (similarity {sim}).',
        forecast=' Forecast for 10 s: {pred} → got {real} — {res}{err}.', ok='came true', miss='did not come true',
        err=' (error {e}; trivial forecast {t})', by_clock="the body's clock: seen at this minute of the hour in {n} other hours", announced='announced: {w}',
        deferred=' No action — deferred, will recall in an hour.', recalled='RECALLED (deferred {m} min ago): {w}',
        kinds=dict(flight='flight', freeze='freeze', fight='fight', none='none'),
        acts=dict(gpu_hot='GPU ≥ 85 °C → signal services to reduce load', disk_full='disk ≥ 95 % → signal the cache cleaner',
                  mem_low='free memory < 1 GB → signal heavy services', intruder='foreign login → freeze, wait for a human',
                  oom='out of memory, a process was killed → raise the alarm', none='no reflex needed — entering thought'),
        who='I am SunPoint, the observer on this server. Consciousness = 10 s before + alert + reflex + 10 s after.', where='server',
        working='working: {p} {c}% CPU', watching='watching', busy='; load is high — watch the temperature',
        calm='; calm — watching and learning the rhythm', consolidate='memory: cache → long-term', in_min='in {m} min',
        recall_deferred='recall deferred: ', hashes='file name = sha256 of the file; sha256 = hash of sunpoint.json',
        goals=['keep the thread: nothing started is lost', 'grow: SunPoint → eyes → body'], first_voice='First voice of SunPoint',
        waited='expected', bytes='bytes'),
}
L = TEXT.get(LANG, TEXT['en'])
GOALS = CONF.get('goals', L['goals'])

for d in ('sunpoints', 'crash'): os.makedirs(os.path.join(BASE, d), exist_ok=True)
P = lambda n: os.path.join(BASE, n)
LIFE, PLANS = P('life.json'), P('plans.jsonl')
LOG, HB, STATE_NOW, SUBC, DEFER, VOICE = P('log.txt'), P('heartbeat.json'), P('state_now.json'), P('subconscious.jsonl'), P('deferred.json'), P('first_voice.md')
GEN = P('generator.json'); ANNOUNCE = os.environ.get('SUNPOINT_ANNOUNCE', P('announce.jsonl'))

def now(): return datetime.now(TZ) if TZ else datetime.now().astimezone()
def ts(): return now().strftime('%Y-%m-%d %H:%M:%S')
def log(m):
    with open(LOG, 'a', encoding='utf-8') as f: f.write(f'{ts()} {m}\n')
def sh(cmd, t=6):
    try: return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t).stdout
    except Exception: return ''
def aw(path, data):
    """Atomic write."""
    with open(path + '.tmp', 'w', encoding='utf-8') as f: f.write(data)
    os.replace(path + '.tmp', path)

# ---------- senses ----------
_prev = {}
def fast():
    """Every second: load, CPU and network from /proc."""
    s = {}
    try: s['load1'] = float(open('/proc/loadavg').read().split()[0])
    except Exception: pass
    try:
        p = [int(x) for x in open('/proc/stat').readline().split()[1:]]; idle, tot = p[3] + p[4], sum(p)
        if 'cpu' in _prev:
            di, dt = idle - _prev['cpu'][0], tot - _prev['cpu'][1]
            if dt > 0: s['cpu_pct'] = round(100 * (1 - di / dt), 1)
        _prev['cpu'] = (idle, tot)
    except Exception: pass
    try:
        rx = tx = 0
        for l in open('/proc/net/dev').readlines()[2:]:
            n, r = l.split(':', 1)
            if n.strip() == 'lo': continue
            f = r.split(); rx += int(f[0]); tx += int(f[8])
        t = time.time()
        if 'net' in _prev:
            dt = max(1e-3, t - _prev['net'][2])
            s['net_rx_kbs'] = round((rx - _prev['net'][0]) / 1024 / dt, 1); s['net_tx_kbs'] = round((tx - _prev['net'][1]) / 1024 / dt, 1)
        _prev['net'] = (rx, tx, t)
    except Exception: pass
    if TEST and os.environ.get('SPIKE_AT') and int(os.environ['SPIKE_AT']) <= SEC < int(os.environ['SPIKE_AT']) + 3:
        s['cpu_pct'] = 99.0; s['load1'] = s.get('load1', 0) + 8
    return s

def slow():
    """Every 10 seconds: memory, disk, number of processes, GPU."""
    s = {}
    try:
        mi = {l.split(':')[0]: int(l.split()[1]) for l in open('/proc/meminfo')}; s['mem_avail_mb'] = mi.get('MemAvailable', 0) // 1024
    except Exception: pass
    try: st = os.statvfs('/'); s['disk_root_pct'] = round(100 * (1 - st.f_bavail / st.f_blocks), 2)
    except Exception: pass
    try: s['procs'] = sum(1 for d in os.listdir('/proc') if d.isdigit())
    except Exception: pass
    if shutil.which('nvidia-smi') and not TEST:
        try:
            a = [float(x) for x in sh('nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,memory.used --format=csv,noheader,nounits', 4).split('\n')[0].split(',')]
            s['gpu_temp'], s['gpu_util'], s['gpu_mem_mb'] = a
        except Exception: pass
    return s

# journal lines become templates: no digits, keys, hashes or fingerprints ever leave the machine
_rx = [(re.compile(r'(sha256|md5):\S+', re.I), 'fp:§'), (re.compile(r'[A-Za-z0-9+/=_-]{12,}'), '§'),
       (re.compile(r'\b[0-9a-fA-F]{6,}\b'), '#'), (re.compile(r'\d+'), '#'), (re.compile(r'\s+'), ' ')]
def tpl(m):
    m = str(m)
    for r, rep in _rx: m = r.sub(rep, m)
    return m.lower().strip()[:120]
_lj = [time.time()]
def journal():
    if TEST or not shutil.which('journalctl'): return []
    since = _lj[0]; _lj[0] = time.time()
    out = sh(f'journalctl --since "@{since:.0f}" -q --no-pager -n 300 -o json --output-fields=SYSLOG_IDENTIFIER,MESSAGE', 6)
    items = defaultdict(int)
    for line in out.splitlines():
        try: j = json.loads(line)
        except Exception: continue
        msg = j.get('MESSAGE', ''); msg = '' if isinstance(msg, list) else msg
        items[(str(j.get('SYSLOG_IDENTIFIER', '?'))[:40], tpl(msg))] += 1
    return list(items.items())

# ---------- the generator: expectation and surprise ----------
class Num:
    """Expected value and spread of one numeric signal (exponential averages) and the surprise of a new value in bits."""
    __slots__ = ('m', 'v', 'floor', 'mag')
    def __init__(self, floor): self.m, self.v, self.floor, self.mag = None, 0.0, floor, deque(maxlen=400)
    def sd(self): return max(math.sqrt(self.v), 0.02 * abs(self.m or 0), self.floor)
    def z(self, x): return 0.0 if self.m is None else (x - self.m) / self.sd()
    def step(self, x, alpha):
        if self.m is None: self.m = x; return 0.0, x, 0.0
        exp, sd = self.m, self.sd(); z = abs(x - exp) / sd
        bits = -math.log2(max(math.erfc(z / math.sqrt(2)), 1e-300)) if z < 7 else (z * z / 2 + math.log(z * 1.2533)) / math.log(2)
        bits = min(60.0, bits)
        # habit memory: a spike strength seen >= 3 times in the last day is automatism - its surprise is damped
        if z >= 3:
            band = round(math.log2(z), 1); seen = sum(1 for b, t in self.mag if b == band and time.time() - t < 86400)
            self.mag.append((band, time.time()))
            if seen >= 3: bits *= 0.25
        d = x - self.m; self.m += alpha * d; self.v = (1 - alpha) * (self.v + alpha * d * d)
        return bits, exp, z

class Cat:
    """Surprise of a journal line: how rare is its source, and how rare is this template within the source."""
    def __init__(self): self.src = defaultdict(int); self.tpl = defaultdict(lambda: defaultdict(int)); self.N = 0
    def bits(self, who, t, k=1):
        b1 = -math.log2((self.src[who] + 1) / (self.N + len(self.src) + 1)); T = self.tpl[who]
        b2 = -math.log2((T[t] + 1) / (self.src[who] + len(T) + 1))
        self.src[who] += k; T[t] += k; self.N += k
        return min(60.0, b1 + 0.5 * b2)

NUM = {}; CAT = Cat()
def num(k):
    if k not in NUM: NUM[k] = Num(FLOOR.get(k, 1e-3))
    return NUM[k]
KEYS = ['load1', 'cpu_pct', 'net_rx_kbs', 'net_tx_kbs', 'mem_avail_mb', 'disk_root_pct', 'procs', 'gpu_temp', 'gpu_util', 'gpu_mem_mb']

def state_vec(sig):
    """State vector: the z-score of every signal, clipped to +-8 and packed into int8 (x16) - thinking in vectors."""
    return [max(-127, min(127, int(round(max(-8, min(8, num(k).z(sig[k]) if k in sig else 0)) * 16)))) for k in KEYS]

def cos(a, b):
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(x * x for x in b))
    return 0.0 if not na or not nb else sum(x * y for x, y in zip(a, b)) / (na * nb)

# ---------- the forecast learns: where does a signal go in the 10 s after a spike? ----------
#   r = (actual - expected) / (spike - expected)      0 = back at the expected value, 1 = still at the spike
R = defaultdict(lambda: deque(maxlen=CFG['r_keep'])); RALL = deque(maxlen=CFG['r_keep'])
TRIV = defaultdict(lambda: [0.0, 0.0])            # per signal: total error of Mean and of Persistence so far
def median(a):
    a = sorted(a); n = len(a)
    return a[n // 2] if n % 2 else (a[n // 2 - 1] + a[n // 2]) / 2
def r_hat(k):
    """Return coefficient for signal k: its own median when it has 3 values; else the median over all signals when there are 5; else 0.5."""
    h = R[k] if k in R else ()
    r = median(h) if len(h) >= 3 else (median(RALL) if len(RALL) >= 5 else 0.5)
    return max(-0.5, min(2.0, r))
def pick(k):
    """The tougher trivial forecast: for this signal, Mean (r = 0) or Persistence (r = 1) - whichever was better so far."""
    return 0.0 if TRIV[k][0] <= TRIV[k][1] else 1.0
def learn(k, r, rh=None, pk=None):
    """Score one check and remember r. Returns (model error, tougher trivial error); both None when only learning."""
    out = (None, None)
    if rh is not None:
        em, et = abs(r - rh), abs(r - pk)
        STATS['checks'] += 1; STATS['e_model'] += em; STATS['e_mean'] += abs(r); STATS['e_pers'] += abs(r - 1); STATS['e_pick'] += et
        if STATS['e_pick'] > 0: STATS['skill'] = round(1 - STATS['e_model'] / STATS['e_pick'], 3)
        best = min(STATS['e_mean'], STATS['e_pers'])
        if best > 0: STATS['skill_fixed'] = round(1 - STATS['e_model'] / best, 3)
        out = (round(em, 2), round(et, 2))
    R[k].append(r); RALL.append(r); TRIV[k][0] += abs(r); TRIV[k][1] += abs(r - 1)
    return out

# ---------- the body's own clock: the same signal at the same minute of the hour ----------
SLOT = defaultdict(list)                          # (signal, minute of the hour) -> [(hour number, z), ...]
def clock_seen(k, t, z, remember=True):
    """In how many other hours did signal k spike at this minute (+-1)? Returns (hours, habitual)."""
    hour, minute = int(t // 3600), int(t // 60) % 60
    seen = {}
    for m in ((minute - 1) % 60, minute, (minute + 1) % 60):
        for h, zz in SLOT.get((k, m), ()):
            if h != hour and hour - h <= CFG['clock_window_h']: seen[h] = max(seen.get(h, 0), zz)
    if remember:
        a = SLOT[(k, minute)]; a.append((hour, round(z, 1)))
        SLOT[(k, minute)] = [x for x in a if hour - x[0] <= CFG['clock_window_h']][-60:]
    habitual = len(seen) >= CFG['clock_hours'] and z <= CFG['clock_strong'] * max(seen.values())
    return len(seen), habitual

def announced(t):
    """Scheduled work announces itself in announce.jsonl. Returns what is running at time t, or None."""
    try:
        if not os.path.exists(ANNOUNCE): return None
        with open(ANNOUNCE, encoding='utf-8') as f: lines = f.readlines()[-50:]
        for l in reversed(lines):
            a = json.loads(l)
            if a['t'] - 5 <= t <= a['t'] + float(a.get('for_s', 120)): return str(a.get('what', '?'))[:60]
    except Exception: pass
    return None

# ---------- the generator survives a restart ----------
def gen_save():
    """Expectations, spreads, habit memory (counts per strength band), journal habits, r histories, clock slots, past states."""
    num_ = {}
    for k, v in NUM.items():
        if v.m is None: continue
        bands = {}
        for b, tt in v.mag:
            if time.time() - tt < 86400: c = bands.setdefault(str(b), [0, 0]); c[0] += 1; c[1] = max(c[1], round(tt))
        num_[k] = dict(m=round(v.m, 4), v=round(v.v, 6), mag=bands)
    cat = dict(N=CAT.N, src=dict(CAT.src), tpl={w: dict(sorted(T.items(), key=lambda kv: -kv[1])[:200]) for w, T in CAT.tpl.items()})
    g = dict(v=VERSION, t=time.time(), saved=ts(), num=num_, cat=cat, r={k: [round(x, 3) for x in h] for k, h in R.items()},
             rall=[round(x, 3) for x in RALL], triv={k: [round(a, 3), round(b, 3)] for k, (a, b) in TRIV.items()},
             slot=[[k, m, v] for (k, m), v in SLOT.items() if v], past=[[sv, round(tt)] for sv, tt in list(PAST)[-500:]])
    aw(GEN, json.dumps(g, ensure_ascii=False, separators=(',', ':')))

def gen_load():
    """Load generator.json if it is fresh enough. Returns True when the expectations were restored."""
    try: g = json.load(open(GEN, encoding='utf-8'))
    except Exception: return False
    fresh = time.time() - g.get('t', 0) < CFG['generator_max_age_h'] * 3600
    for k, h in g.get('r', {}).items(): R[k].extend(h)             # what was learned does not expire with the expectations
    RALL.extend(g.get('rall', []))
    for k, ab in g.get('triv', {}).items(): TRIV[k] = list(ab)
    for k, m, v in g.get('slot', []): SLOT[(k, int(m))] = [tuple(x) for x in v]
    for sv, tt in g.get('past', []): PAST.append((sv, tt))
    c = g.get('cat', {}); CAT.N = c.get('N', 0)
    for w, n in c.get('src', {}).items(): CAT.src[w] = n
    for w, T in c.get('tpl', {}).items():
        for tp, n in T.items(): CAT.tpl[w][tp] = n
    if not fresh: return False
    for k, d in g.get('num', {}).items():
        x = num(k); x.m, x.v = d['m'], d['v']
        for b, (cnt, last) in d.get('mag', {}).items():
            for _ in range(min(int(cnt), 40)): x.mag.append((float(b), last))
    return True

def bootstrap(dirs):
    """First start without generator.json: rebuild the learned memory from stored moments (r, clock slots, strengths, past states)."""
    import glob
    rows = []
    for d in dirs:
        for f in glob.glob(os.path.join(d, 'sunpoints', '*', '*.bau')):
            try:
                with zipfile.ZipFile(f) as z: sp = json.loads(z.read('sunpoint.json'))
                rows.append(sp)
            except Exception: continue
    rows.sort(key=lambda sp: sp.get('t', 0)); n = 0
    for sp in rows:
        fo, fc, fx, t0 = sp.get('focus') or {}, sp.get('forecast_check'), sp.get('forecast') or {}, sp.get('t', 0)
        if sp.get('state') and t0: PAST.append((sp['state'], t0))
        if fo.get('src') != 'num' or fo.get('exp') is None: continue
        k, v, e = fo['k'], float(fo['v']), float(fo['exp']); sd = fx.get('sd') or 0
        z = abs(v - e) / sd if sd else 0
        if z:
            clock_seen(k, t0, z)
            if z >= 3 and time.time() - t0 < 86400: num(k).mag.append((round(math.log2(z), 1), t0))
        if fc and fc.get('real') is not None and abs(v - e) > 1e-9: learn(k, (float(fc['real']) - e) / (v - e)); n += 1
    return len(rows), n

# ---------- reflexes: fight / flight / freeze (a rule table, no model, no thinking) ----------
REFLEX = [
    ('flight', lambda s, e: s.get('gpu_temp', 0) >= 85, 'gpu_hot'),
    ('flight', lambda s, e: s.get('disk_root_pct', 0) >= 95, 'disk_full'),
    ('flight', lambda s, e: 0 < s.get('mem_avail_mb', 99999) < 1024, 'mem_low'),
    ('freeze', lambda s, e: e and e.get('src') == 'log' and re.search(r'failed password|invalid user|authentication failure', e.get('key', '')), 'intruder'),
    ('fight', lambda s, e: e and e.get('src') == 'log' and re.search(r'out of memory|killed process', e.get('key', '')), 'oom'),
]
def reflex(sig, ev):
    t0 = time.perf_counter()
    for code, cond, act in REFLEX:
        try:
            if cond(sig, ev): return dict(code=code, kind=L['kinds'][code], act=L['acts'][act], us=round((time.perf_counter() - t0) * 1e6, 1))
        except Exception: pass
    return dict(code='none', kind=L['kinds']['none'], act=L['acts']['none'], us=round((time.perf_counter() - t0) * 1e6, 1))

# ---------- output: optional event stream ----------
STATS = dict(alerts=0, sunpoints=0, reflex=0, forecast_ok=0, forecast_n=0, subconscious=0, deferred=0, recalled=0,
             rp_ok=0, rp_err=0, started=ts(), bytes_saved=0,
             checks=0, e_model=0.0, e_mean=0.0, e_pers=0.0, e_pick=0.0, skill=None, skill_fixed=None, by_clock=0, announced=0)
def produce(obj):
    if not STREAM or TEST: return
    line = json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + '\n'
    def run():
        try:
            r = subprocess.run(['docker', 'exec', '-i', STREAM.get('container', 'redpanda'), 'rpk', 'topic', 'produce', STREAM.get('topic', 'sunpoint.events')],
                               input=line, capture_output=True, text=True, timeout=15)
            STATS['rp_ok' if r.returncode == 0 else 'rp_err'] += 1
        except Exception: STATS['rp_err'] += 1
    threading.Thread(target=run, daemon=True).start()

# ---------- SunPoint: generator + deviations (the 97 KB principle) ----------
def compress(seconds):
    """Every second keeps only the signals that deviate from the expectation by more than 1 sd -> [(key, z)]."""
    out = []
    for t, z in seconds:
        dev = [[k, round(v / 16, 1)] for k, v in zip(KEYS, z) if abs(v) >= 16]   # the vector stores z x16 -> keep |z| >= 1
        out.append([round(t, 1), dev])
    return out

def words(sp):
    f = sp['focus']; r = sp['reflex']; fc = sp.get('forecast_check')
    w = L['noticed'].format(k=f['k'], v=f['v'], exp=f['exp'])
    w += L['reflex'].format(kind=r['kind'], act=r['act'], us=r['us']) if r['code'] != 'none' else L['noreflex'].format(us=r['us'])
    if sp.get('recall'): w += L['recall'].format(when=sp['recall']['when'], sim=sp['recall']['sim'])
    if fc: w += L['forecast'].format(pred=fc['pred'], real=fc['real'], res=L['ok'] if fc['ok'] else L['miss'],
                                     err=L['err'].format(e=fc['err'], t=fc['triv']) if fc.get('err') is not None else '')
    if sp.get('deferred'): w += L['deferred']
    return w

PAST = deque(maxlen=2000)   # state vectors of past SunPoints - recognition of situations
def save(sp):
    """A SunPoint is a small .bau container: manifest.json + sunpoint.json; the file name is the sha256 of the file."""
    body = json.dumps(sp, ensure_ascii=False, separators=(',', ':')).encode()
    d = os.path.join(BASE, 'sunpoints', now().strftime('%Y-%m-%d')); os.makedirs(d, exist_ok=True)
    man = dict(format='bau/0.1', kind='sunpoint', model=VERSION, author=f'sunpoint@{socket.gethostname()}', created=ts(),
               keep_days=90, sha256=hashlib.sha256(body).hexdigest(), hashes=L['hashes'], words=sp['words'], links=[])
    tmp = os.path.join(d, '.tmp.bau')
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json', json.dumps(man, ensure_ascii=False, indent=1)); z.writestr('sunpoint.json', body)
    sha = hashlib.sha256(open(tmp, 'rb').read()).hexdigest(); dst = os.path.join(d, f'{sha}.bau'); os.replace(tmp, dst)
    STATS['sunpoints'] += 1; STATS['bytes_saved'] += os.path.getsize(dst)
    return sha, os.path.getsize(dst)

def state_now(sp):
    """The 3 KB state: who I am, where, what I just noticed, what I expect, what I plan."""
    st = dict(v=VERSION, who=CONF.get('who', L['who']), where=f"{socket.gethostname()} · {CONF.get('where', L['where'])}", now=ts(),
              last=dict(words=sp['words'], focus=sp['focus'], reflex=sp['reflex']['kind']),
              expect={k: round(v.m, 1) for k, v in NUM.items() if v.m is not None}, plan=PLAN[0], stats=STATS)
    aw(STATE_NOW, json.dumps(st, ensure_ascii=False, separators=(',', ':'))[:CFG['state_max'] * 2])

# ---------- background plans, even when idle: a pyramid ----------
#   1 what I am doing now  2 why  3 what next  4 when  5 life (dates that matter to my people)
def plan_stack(sig, deferred, t):
    top = sh("ps -eo comm,pcpu --sort=-pcpu --no-headers | head -2", 3).split('\n')[0].split()
    busy = sig.get('cpu_pct', 0) > 50 or sig.get('gpu_util', 0) > 50
    now_ = (L['working'].format(p=top[0], c=top[1]) if len(top) >= 2 else L['watching']) + (L['busy'] if busy else L['calm'])
    nxt = []
    tm = sh('LC_ALL=C systemctl list-timers --no-pager --no-legend 2>/dev/null | head -2', 4).strip().splitlines()
    for l in tm:
        f = l.split(); unit = next((x for x in f if x.endswith('.timer')), None)
        if unit: nxt.append(dict(what=unit.replace('.timer', ''), when=' '.join(f[1:3])))
    if 'consolidate_minute' in CONF:
        nxt.append(dict(what=L['consolidate'], when=L['in_min'].format(m=(int(CONF['consolidate_minute']) - now().minute) % 60)))
    for d in sorted(deferred, key=lambda d: d['due'])[:2]:
        nxt.append(dict(what=L['recall_deferred'] + d['words'][:60], when=L['in_min'].format(m=max(0, int((d['due'] - t) / 60)))))
    life = []
    try:
        today = now().date()
        for e in json.load(open(LIFE, encoding='utf-8')):
            mm, dd = map(int, e['date'].split('-')); d0 = today.replace(month=mm, day=dd)
            if d0 < today: d0 = d0.replace(year=today.year + 1)
            days = (d0 - today).days
            if days <= e.get('remind_days', 30): life.append(dict(what=e['what'], in_days=days, todo=e.get('todo', '')))
    except Exception: pass
    return dict(t=ts(), now=now_, why=GOALS, next=nxt[:4], when=(nxt[0]['when'] if nxt else '—'), life=sorted(life, key=lambda x: x['in_days']))

# ---------- main loop ----------
RUN = [True]; PLAN = [None]
def stop(*_): RUN[0] = False
signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)
SEC = 0

def main():
    global SEC
    log(f'start {VERSION} pid={os.getpid()} base={BASE} test={TEST} lang={LANG} cfg={CFG}')
    ring = deque(maxlen=CFG['before_s'] + 1)       # 10 s BEFORE - one entry per second: (t, state vector)
    sig = {}; pending = []; last_alert = {}; times = deque(); deferred = []
    try: deferred = json.load(open(DEFER, encoding='utf-8'))
    except Exception: pass
    first_voice = not os.path.exists(VOICE)
    n_test = int(sys.argv[sys.argv.index('--test') + 1]) if TEST else 0
    t_start = time.time(); shadow = []             # forecasts of spikes that went to the subconscious: checked too, the forecast learns from them
    loaded = False
    if not TEST:
        had = os.path.exists(GEN); loaded = gen_load()
        if not had:
            extra = [d for d in os.environ.get('SUNPOINT_BOOTSTRAP', '').split(os.pathsep) if d]
            log('bootstrap from stored moments: %d moments, %d checked forecasts' % bootstrap([BASE] + extra))
        log(f'generator: loaded={loaded} r_signals={len(R)} clock_slots={len(SLOT)} past={len(PAST)}')
    warmup = CFG['warmup_loaded_s'] if loaded else CFG['warmup_s']
    while RUN[0]:
        t = time.time() if not TEST else t_start + SEC; new = []
        f = fast(); sig.update(f)
        if SEC % CFG['slow_every'] == 0:
            sig.update(slow())
            for (who, tp), cnt in journal():
                key = f'{who}: {tp}'
                if SUBCONSCIOUS.search(who) or SUBCONSCIOUS.search(key):           # subconscious: never enters consciousness
                    with open(SUBC, 'a', encoding='utf-8') as fo: fo.write(json.dumps(dict(t=round(t, 1), k=key, n=cnt), ensure_ascii=False) + '\n')
                    STATS['subconscious'] += 1; continue
                new.append(dict(src='log', key=key, val=cnt, exp=None, bits=round(CAT.bits(who, tp, cnt), 2)))
        keys_now = f.keys() if SEC % CFG['slow_every'] else sig.keys()
        for k in keys_now:
            b, e, z = num(k).step(sig[k], CFG['alpha'])
            new.append(dict(src='num', key=k, val=sig[k], exp=round(e, 2), bits=round(b, 2), z=round(z, 2)))
        sv = state_vec(sig); ring.append((t, sv))
        # close the pending "10 s after"
        for p in [p for p in pending if t >= p['due']]:
            pending.remove(p); sp = p['sp']
            sp['after'] = compress([(tt, vv) for tt, vv in p['after']])
            k = sp['focus']['k']; real = sig.get(k); fx = sp['forecast']; pred = fx['pred']
            if real is not None and pred is not None:
                v0, e0 = sp['focus']['v'], sp['focus']['exp']
                if abs(v0 - e0) > 1e-9:                    # strict: the forecast came true when it is within a quarter of the spike
                    r = (real - e0) / (v0 - e0); em, et = learn(k, r, fx['r_hat'], fx['pick']); ok = em <= CFG['strict']
                    sp['forecast_check'] = dict(pred=pred, real=real, ok=ok, r=round(r, 3), err=em, triv=et)
                else:
                    ok = abs(real - pred) <= max(fx['sd'] * 2, abs(pred) * 0.15); sp['forecast_check'] = dict(pred=pred, real=real, ok=ok)
                STATS['forecast_n'] += 1; STATS['forecast_ok'] += int(ok)
            sp['words'] = words(sp)
            sha, size = save(sp); state_now(sp); PAST.append((sp['state'], sp['t']))
            produce(dict(type='ALERT', model=VERSION, address=f'bau://{BAU_HOST}/sha256/{sha}', words=sp['words'],
                         focus=sp['focus'], reflex=sp['reflex']['kind']))
            log(f'SUNPOINT {sha[:12]} {size}B · {sp["words"]}')
            if first_voice:
                aw(VOICE, f'# {L["first_voice"]} · {ts()}\n\n{sp["words"]}\n\nSunPoint: bau://{BAU_HOST}/sha256/{sha} ({size} {L["bytes"]})\n')
                produce(dict(type='VOICE', model=VERSION, words=sp['words'])); first_voice = False
        for p in pending: p['after'].append((t, sv))
        for c in [c for c in shadow if t >= c['due']]:      # the subconscious learns from everything
            shadow.remove(c)
            if sig.get(c['k']) is not None: learn(c['k'], (sig[c['k']] - c['e']) / (c['v'] - c['e']), c['rh'], c['pk'])
        # deferred -> recalled
        for d in [d for d in deferred if t >= d['due']]:
            deferred.remove(d); STATS['recalled'] += 1; log(L['recalled'].format(m=int((t - d['t']) / 60), w=d['words']))
        # alert
        warm = (t - t_start) >= (warmup if not TEST else 20)
        if warm and new:
            total = sum(e['bits'] for e in new) + sum(1.0 for _ in ring) * 2.0   # the +-10 s window: background keeps the share honest
            hot = [e for e in new if e['bits'] >= CFG['min_bits'] and e['bits'] / total > (CFG['num_share'] if e['src'] == 'num' else CFG['alert_share'])
                   and t - last_alert.get(e['key'], 0) >= (CFG['cooldown_s'] if not TEST else 0)]
            while times and times[0] < t - 3600: times.popleft()
            if hot and len(times) < CFG['max_per_hour'] and not any(p['t'] > t - CFG['after_s'] for p in pending):
                ev = max(hot, key=lambda e: e['bits']); rf = reflex(sig, ev)     # reflex first: microseconds, no thinking
                for e in hot: last_alert[e['key']] = t
                # efference copy, first step: is this the body's own scheduled work? (a reflex always stays conscious)
                cause = None
                if ev['src'] == 'num' and rf['code'] == 'none':
                    hours, habit = clock_seen(ev['key'], t, abs(ev.get('z', 0)))
                    what = announced(t)
                    if what: cause = L['announced'].format(w=what); STATS['announced'] += 1
                    elif habit: cause = L['by_clock'].format(n=hours); STATS['by_clock'] += 1
                if cause:
                    kk, e0, v0 = ev['key'], ev['exp'], ev['val']
                    with open(SUBC, 'a', encoding='utf-8') as fo:
                        fo.write(json.dumps(dict(t=round(t, 1), k=kk, v=v0, exp=e0, z=ev.get('z'), cause=cause), ensure_ascii=False) + '\n')
                    STATS['subconscious'] += 1
                    if abs(v0 - e0) > 1e-9: shadow.append(dict(due=t + CFG['after_s'], k=kk, e=e0, v=v0, rh=r_hat(kk), pk=pick(kk)))
                    hot = []
            if hot and len(times) < CFG['max_per_hour'] and not any(p['t'] > t - CFG['after_s'] for p in pending):
                times.append(t); STATS['alerts'] += 1; STATS['reflex'] += int(rf['code'] != 'none')
                k = ev['key']
                rh = pk = None
                if ev['src'] == 'num' and len(ring) >= 3:                       # forecast for +10 s: the learned return of this signal
                    rh, pk = r_hat(k), pick(k); pred = round(ev['exp'] + rh * (sig[k] - ev['exp']), 2)
                else: pred = None
                best = max(((cos(sv, v), tt) for v, tt in PAST), default=(0, 0))
                sp = dict(v=VERSION, t=round(t, 2), when=ts(), host=socket.gethostname(),
                          before=compress(list(ring)[:-1]), state=sv, keys=KEYS,
                          focus=dict(k=k[:90], v=ev['val'], exp=ev['exp'], bits=ev['bits'], src=ev['src']),
                          reflex=rf, forecast=dict(k=k, pred=pred, horizon_s=CFG['after_s'], sd=round(num(k).sd(), 3) if ev['src'] == 'num' else None,
                                                   r_hat=None if rh is None else round(rh, 3), pick=pk),
                          guesses=[dict(k=e['key'][:90], b=e['bits']) for e in sorted(hot, key=lambda e: -e['bits'])[1:4]],
                          recall=(dict(sim=round(best[0], 3), when=datetime.fromtimestamp(best[1], TZ).strftime('%d.%m %H:%M') if TZ
                                       else datetime.fromtimestamp(best[1]).astimezone().strftime('%d.%m %H:%M')) if best[0] >= 0.9 else None),
                          actions=([dict(kind='reflex', act=rf['act'])] if rf['code'] != 'none' else []))
                if not sp['actions']:
                    sp['deferred'] = True; STATS['deferred'] += 1
                    deferred.append(dict(t=t, due=t + CFG['defer_s'], words=f"{k[:60]} = {ev['val']} ({L['waited']} {ev['exp']})"))
                    aw(DEFER, json.dumps(deferred[-200:], ensure_ascii=False))
                pending.append(dict(t=t, due=t + CFG['after_s'], sp=sp, after=[]))
        if SEC % 60 == 0:                                   # plans in the background - every minute, even when idle
            try:
                PLAN[0] = plan_stack(sig, deferred, t)
                if SEC % 600 == 0:
                    with open(PLANS, 'a', encoding='utf-8') as fo: fo.write(json.dumps(PLAN[0], ensure_ascii=False) + '\n')
                try: st = json.load(open(STATE_NOW, encoding='utf-8'))
                except Exception: st = dict(v=VERSION, who='SunPoint')
                st['plan'] = PLAN[0]; st['now'] = ts(); aw(STATE_NOW, json.dumps(st, ensure_ascii=False, separators=(',', ':')))
            except Exception as e: log(f'plan error {e}')
            if not TEST and SEC:
                try: gen_save()
                except Exception as e: log(f'generator save error {e}')
        if SEC % 10 == 0:
            aw(HB, json.dumps(dict(t=ts(), t_unix=t, clean=False, stats=STATS, pid=os.getpid()), ensure_ascii=False))
        SEC += 1
        if TEST and SEC >= n_test: break
        time.sleep(0 if TEST else max(0.0, 1.0 - (time.time() - t)))
    if not TEST:
        try: gen_save()
        except Exception as e: log(f'generator save error {e}')
    aw(HB, json.dumps(dict(t=ts(), t_unix=time.time(), clean=True, stats=STATS, pid=os.getpid()), ensure_ascii=False))
    log(f'stop clean {STATS}')

def selftest():
    """Checks with made-up numbers and times. No senses are read, nothing is spoken."""
    global GEN, ANNOUNCE
    assert r_hat('a') == 0.5                                              # nothing learned yet: halfway
    for r in (0.1, 0.2, 0.3, 0.0, 0.2): learn('cpu', r)
    assert abs(r_hat('cpu') - 0.2) < 1e-9 and abs(r_hat('new') - 0.2) < 1e-9    # own median; a new signal takes the common one
    for r in (1.0, 1.1, 0.9): learn('mem', r)
    assert abs(r_hat('mem') - 1.0) < 1e-9 and pick('mem') == 1.0 and pick('cpu') == 0.0
    em, et = learn('cpu', 0.25, r_hat('cpu'), pick('cpu')); assert em == 0.05 and et == 0.25 and STATS['skill'] > 0
    t0 = 1_800_000_000 - 1_800_000_000 % 3600 + 7 * 60                    # minute 7 of some hour
    for h in range(3): assert clock_seen('net', t0 + h * 3600, 6.0) == (h, False)      # the first three hours: still news
    assert clock_seen('net', t0 + 3 * 3600, 6.0, remember=False) == (3, True)          # the fourth: a habit
    assert clock_seen('net', t0 + 3 * 3600 + 60, 6.0, remember=False)[1]               # a minute later: the same habit
    assert not clock_seen('net', t0 + 3 * 3600, 13.0, remember=False)[1]               # unusually strong: conscious
    assert not clock_seen('net', t0 + 3 * 3600 + 20 * 60, 6.0, remember=False)[1]      # another minute: conscious
    assert not clock_seen('cpu', t0 + 3 * 3600, 6.0, remember=False)[1]                # another signal: conscious
    ANNOUNCE = P('.selftest_announce.jsonl'); aw(ANNOUNCE, json.dumps(dict(t=t0, what='memory consolidation', for_s=120)) + '\n')
    assert announced(t0 + 60) == 'memory consolidation' and announced(t0 + 300) is None and announced(t0 - 60) is None
    os.remove(ANNOUNCE)
    GEN = P('.selftest_generator.json'); x = num('cpu'); x.m, x.v = 12.0, 4.0; x.mag.append((2.6, time.time()))
    gen_save(); NUM.clear(); R.clear(); RALL.clear(); SLOT.clear(); TRIV.clear()
    assert gen_load() and abs(num('cpu').m - 12.0) < 1e-6 and len(num('cpu').mag) == 1
    assert abs(r_hat('mem') - 1.0) < 1e-9 and clock_seen('net', t0 + 3 * 3600, 6.0, remember=False)[1]
    os.remove(GEN); print('selftest ok')

if __name__ == '__main__':
    selftest() if '--selftest' in sys.argv else main()
