#!/usr/bin/env python3
"""proprio_probe.py - who is "breathing" on the machine: second by second, which organ of the system uses the CPU.

The question behind it: does SunPoint notice the world, or its own body (eyes, voice, memory, the operator)?
A brain cancels the sensations caused by its own actions (efference copy). This probe measures how much of the
load, and of the load peaks, is the system's own body - the part that should never reach consciousness.

Method: every second read /proc/<pid>/stat for all processes, take the CPU time used since the previous second
(children that lived for less than a second are attributed to their parent), and assign every process to an organ
by its command line (see ORGANS; a process without a rule inherits the organ of its parent).

Reads /proc only. The report contains organ names and numbers - never command lines, addresses or user data.
Usage:  python3 -I proprio_probe.py [seconds=150] [sunpoint_log]
        ORGANS can be extended with a JSON file:  PROBE_ORGANS=organs.json  ->  [["pattern", "organ name"], ...]
        PROBE_TZ_HOURS=5 if the SunPoint log is written in UTC+5 while the host clock is in another zone
"""
import os, sys, time, re, json, statistics as st
from collections import defaultdict
from datetime import datetime, timezone, timedelta

DUR = int(sys.argv[1]) if len(sys.argv) > 1 else 150
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, '..', 'src', 'window', 'log.txt')
OUT = os.environ.get('PROBE_OUT', os.path.join(HERE, 'probe')); os.makedirs(OUT, exist_ok=True)
HZ = os.sysconf('SC_CLK_TCK'); NCPU = os.cpu_count() or 1
TZH = os.environ.get('PROBE_TZ_HOURS')        # time zone of the SunPoint log, if it differs from the host's (hours from UTC)
TZI = timezone(timedelta(hours=float(TZH))) if TZH else None
def local(ts): return datetime.fromtimestamp(ts, TZI) if TZI else datetime.fromtimestamp(ts).astimezone()

ORGANS = [  # order matters: the first match on "name + command line" wins
    ('proprio_probe', 'the probe itself'),
    ('eyes_full', 'eyes: full frames'), ('eyes.py', 'eyes: vectors'), ('eyes_v', 'eyes: vectors'),
    ('voice_bridge', 'voice'), ('piper', 'voice'), ('say.sh', 'voice'), ('aplay', 'voice'),
    ('consolidate', 'memory: consolidation'),
    ('sunpoint.py', 'observer'), ('sunpoint_v', 'observer'), ('sunpoint_window', 'observer'),
    ('llama-server', 'language model'), ('ollama', 'language model'),
    ('nats-server', 'memory: streams'), ('redpanda', 'memory: streams'), ('rpk', 'memory: streams'),
    ('containerd', 'memory: streams'), ('dockerd', 'memory: streams'), ('docker', 'memory: streams'),
    ('sshd', 'operator (ssh)'), ('sftp-server', 'operator (ssh)'), ('scp', 'operator (ssh)'),
    ('tailscaled', 'network (vpn)'), ('systemd-journal', 'system journal'), ('cron', 'schedule'),
]
try: ORGANS = [tuple(x) for x in json.load(open(os.environ['PROBE_ORGANS'], encoding='utf-8'))] + ORGANS
except Exception: pass
OTHER, KERNEL = 'system and other', 'kernel'
OWN = ('observer', 'eyes: vectors', 'eyes: full frames', 'voice', 'memory: consolidation', 'memory: streams',
       'operator (ssh)', 'the probe itself')

def read_stat(pid):
    try: s = open(f'/proc/{pid}/stat').read()
    except Exception: return None
    r = s.rfind(')'); f = s[r + 2:].split()
    try: return (s[s.find('(') + 1:r], int(f[1]), int(f[11]) + int(f[12]), int(f[13]) + int(f[14]), int(f[19]))
    except Exception: return None   # (name, parent, own time, children's time, start)

CLS = {}
def organ(pid, cur, depth=0):
    info = cur.get(pid)
    if not info: return OTHER
    key = (pid, info[4])
    if key in CLS: return CLS[key]
    try: cl = open(f'/proc/{pid}/cmdline', 'rb').read().replace(b'\0', b' ').decode('utf-8', 'replace')
    except Exception: cl = ''
    text = info[0] + ' ' + cl; o = None
    for pat, name in ORGANS:
        if pat in text: o = name; break
    if o is None:
        if pid == 2 or info[1] == 2: o = KERNEL
        elif info[1] > 1 and depth < 8: o = organ(info[1], cur, depth + 1)
        else: o = OTHER
    CLS[key] = o
    return o

def cpu_total():
    p = [int(x) for x in open('/proc/stat').readline().split()[1:]]
    return p[3] + p[4], sum(p)
def net_total():
    rx = tx = 0
    for l in open('/proc/net/dev').readlines()[2:]:
        n, r = l.split(':', 1)
        if n.strip() == 'lo': continue
        f = r.split(); rx += int(f[0]); tx += int(f[8])
    return rx, tx
def scan():
    cur = {}
    for d in os.listdir('/proc'):
        if d.isdigit():
            r = read_stat(d)
            if r: cur[int(d)] = r
    return cur

rows = []; prev = scan(); pc = cpu_total(); pn = net_total(); pt = time.time(); t0 = pt
while time.time() - t0 < DUR:
    time.sleep(max(0.0, 1.0 - (time.time() - pt)))
    cur = scan(); c = cpu_total(); n = net_total(); t = time.time(); dt = max(1e-3, t - pt)
    by = defaultdict(float)
    gone = defaultdict(int)                                    # time of vanished children that was already counted
    for pid, pv in prev.items():
        cv = cur.get(pid)
        if cv is None or cv[4] != pv[4]: gone[pv[1]] += pv[2] + pv[3]
    for pid, (comm, ppid, own, ct, stt) in cur.items():
        pv = prev.get(pid); same = pv is not None and pv[4] == stt
        d = own - pv[2] if same else own                       # a new process: all of its time belongs to this second
        dc = (ct - pv[3]) - gone.get(pid, 0) if same else ct   # children the probe never saw (they lived < 1 s)
        if d > 0 or dc > 0: by[organ(pid, cur)] += max(0, d) + max(0, dc)
    di, dtot = c[0] - pc[0], c[1] - pc[1]
    rows.append(dict(t=local(t), ts=t, cpu=100 * (1 - di / dtot) if dtot > 0 else 0.0,
                     rx=(n[0] - pn[0]) / 1024 / dt, tx=(n[1] - pn[1]) / 1024 / dt,
                     by={k: 100 * v / HZ / NCPU / dt for k, v in by.items()}))
    prev, pc, pn, pt = cur, c, n, t

# ---------- report ----------
Lines = []
def P(s=''): Lines.append(s)
cpu = [r['cpu'] for r in rows]; rx = [r['rx'] for r in rows]; N = len(rows)
q = lambda xs, p: sorted(xs)[min(len(xs) - 1, int(p * len(xs)))]
P(f'# Probe "who is breathing" · {rows[0]["t"]:%Y-%m-%d %H:%M:%S} – {rows[-1]["t"]:%H:%M:%S} · {N} s · {NCPU} cores')
P(f'Machine CPU, %: mean {st.mean(cpu):.1f}, median {st.median(cpu):.1f}, 95th {q(cpu, .95):.1f}, max {max(cpu):.1f}')
att = [sum(r['by'].values()) for r in rows]
P(f'Attributed to organs: {st.mean(att):.1f} % of the machine on average (check: {100 * st.mean(att) / max(1e-9, st.mean(cpu)):.0f} % of the measured load)')
tot = defaultdict(float)
for r in rows:
    for k, v in r['by'].items(): tot[k] += v
hot_thr = q(cpu, .90); hot = [r for r in rows if r['cpu'] >= hot_thr]
hot_tot = defaultdict(float)
for r in hot:
    for k, v in r['by'].items(): hot_tot[k] += v
S, HS = sum(tot.values()) or 1, sum(hot_tot.values()) or 1
P(); P(f'## CPU share by organ (whole window / the {len(hot)} busiest seconds, threshold {hot_thr:.1f} %)')
P('| Organ | share of all CPU, % | mean, % of machine | share in peaks, % |'); P('|---|---|---|---|')
for k, v in sorted(tot.items(), key=lambda kv: -kv[1]):
    if 100 * v / S < 0.3 and 100 * hot_tot.get(k, 0) / HS < 0.3: continue
    P(f'| {k} | {100 * v / S:.1f} | {v / N:.2f} | {100 * hot_tot.get(k, 0) / HS:.1f} |')
own_all = sum(v for k, v in tot.items() if k in OWN); own_hot = sum(v for k, v in hot_tot.items() if k in OWN)
P(); P(f'**Own body (observer, eyes, voice, memory, operator, probe): {100 * own_all / S:.0f} % of all CPU, {100 * own_hot / HS:.0f} % of the peaks.**')
P(f'Language model: {100 * tot.get("language model", 0) / S:.0f} % of all CPU, {100 * hot_tot.get("language model", 0) / HS:.0f} % of the peaks.')

P(); P('## Inbound network, KB/s')
P(f'mean {st.mean(rx):.0f}, median {st.median(rx):.0f}, 95th {q(rx, .95):.0f}, max {max(rx):.0f}')

P(); P('## Busiest CPU seconds')
for i in sorted(range(N), key=lambda i: -rows[i]['cpu'])[:8]:
    r = rows[i]; tp = sorted(r['by'].items(), key=lambda kv: -kv[1])[:3]
    P(f'- {r["t"]:%H:%M:%S} · {r["cpu"]:.0f} % · ' + '; '.join(f'{k} {v:.1f}' for k, v in tp))

P(); P('## Moments of consciousness inside the window (who was loading the machine at the second of the alert, ±2 s)')
RE = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) SUNPOINT \S+ \d+B · (?:Заметил|Noticed): (\S+) = ([-\d.]+) \((?:ждал|expected) ([-\d.]+)\)')
found = 0; who = defaultdict(int)
try:
    for line in open(LOG, encoding='utf-8', errors='replace'):
        m = RE.match(line)
        if not m: continue
        dt_ = datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S')
        ta = (dt_.replace(tzinfo=TZI).timestamp() if TZI else dt_.timestamp()) - 10       # the log line is written 10 s after the alert
        idx = [i for i, r in enumerate(rows) if abs(r['ts'] - ta) <= 2.5]
        if not idx: continue
        k = m.group(2); found += 1
        i = max(idx, key=lambda i: rows[i]['rx'] if k.startswith('net_rx') else rows[i]['tx'] if k.startswith('net_tx') else rows[i]['cpu'])
        r = rows[i]; tp = sorted(r['by'].items(), key=lambda kv: -kv[1])[:3]
        if tp: who[tp[0][0]] += 1
        P(f'- alert ~{local(ta):%H:%M:%S} · {k} = {m.group(3)} (expected {m.group(4)}) → second {r["t"]:%H:%M:%S}: '
          f'CPU {r["cpu"]:.0f} %, network {r["rx"]:.0f} KB/s · ' + '; '.join(f'{kk} {v:.1f}' for kk, v in tp))
except Exception as e: P(f'(log not read: {e})')
if not found: P('- no moments fell into the window')
else:
    P(); P(f'**Top organ at the second of the alert, {found} moments:** ' + ', '.join(f'{k} — {v}' for k, v in sorted(who.items(), key=lambda kv: -kv[1])))
rep = '\n'.join(Lines)
name = os.path.join(OUT, f'proprio_{rows[0]["t"]:%Y%m%d_%H%M}.md')
open(name, 'w', encoding='utf-8').write(rep + '\n')
print(rep); print(f'\nfile: {name}')
