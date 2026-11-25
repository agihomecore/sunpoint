"""SunPoint core 1.0 - the parts that write to the workspace and read from it.

Senses     numbers of the body, one reading per second, a generator per signal
SelfModel  whose doing is this: self, body, operator or unknown (by process and cgroup)
Forecast   10 s ahead, a learned return coefficient per signal, a stated confidence
Memory     state vectors of past moments, recognition, survives a restart
Report     who I am, what I noticed, what I expect - from the workspace, in words

Stdlib only.
"""
import math
import os
import time

# The surface of the sphere: numbers the system may change by itself (core/grow.py), inside these bounds.
G = {'z_spike': 4.0,        # a reading this many sigmas away is offered to the workspace
     'refractory': 30.0,    # seconds a signal stays quiet after speaking
     'alpha': 1 / 120,      # how fast the expectation follows the signal
     'r_keep': 60,          # past checks kept per signal
     'w_self': 0.2,         # salience of own work
     'w_body': 0.5,         # salience of the body's work
     'ignite': 1.0}         # salience needed to enter the field
BOUNDS = {'z_spike': (3.0, 8.0), 'refractory': (10.0, 120.0), 'alpha': (1 / 600, 1 / 30), 'r_keep': (10, 200),
          'w_self': (0.05, 0.5), 'w_body': (0.2, 1.0), 'ignite': (0.8, 2.0)}
# The centre of the sphere: not changed by the system.
WARMUP = 60            # readings before a signal may speak
STRICT = 0.25          # a forecast "came true" if its error is within this share of the spike
Z_UNIT = 4.0           # salience 1.0 = four sigmas


def weight(who):
    return {'self': G['w_self'], 'body': G['w_body']}.get(who, 1.0)

FLOOR = {'load1': 0.05, 'cpu': 1.0, 'mem_avail': 20.0, 'net_rx': 2000.0, 'net_tx': 2000.0,
         'ctxt': 200.0, 'running': 0.5}


def median(xs):
    s = sorted(xs)
    n = len(s)
    return 0.0 if not n else (s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2)


class Gen:
    """Expected value and spread of one signal, updated continuously."""

    def __init__(self, floor):
        self.m = None
        self.v = 0.0
        self.n = 0
        self.floor = floor

    def step(self, x):
        alpha = G['alpha']
        if self.m is None:
            self.m, self.n = x, 1
            return 0.0, x
        m = self.m
        sd = max(math.sqrt(self.v), self.floor, 0.02 * abs(m))
        z = (x - m) / sd
        a = alpha / 4 if abs(z) > G['z_spike'] else alpha      # a spike moves the expectation slowly
        if self.n < WARMUP:
            a = max(a, 1 / (self.n + 1))
        self.m = m + a * (x - m)
        self.v = (1 - a) * (self.v + a * (x - m) ** 2)
        self.n += 1
        return z, m


class Senses:
    def __init__(self):
        self.gen = {k: Gen(f) for k, f in FLOOR.items()}
        self.last = {}
        self.z = {}
        self.exp = {}
        self.quiet = {}
        self.prev = None

    @staticmethod
    def raw():
        r = {}
        with open('/proc/loadavg') as f:
            r['load1'] = float(f.read().split()[0])
        with open('/proc/stat') as f:
            for line in f:
                p = line.split()
                if p[0] == 'cpu':
                    v = [int(x) for x in p[1:9]]
                    r['_idle'], r['_all'] = v[3] + v[4], sum(v)
                elif p[0] == 'ctxt':
                    r['_ctxt'] = int(p[1])
                elif p[0] == 'procs_running':
                    r['running'] = float(p[1])
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith('MemAvailable'):
                    r['mem_avail'] = int(line.split()[1]) / 1024
                    break
        rx = tx = 0
        with open('/proc/net/dev') as f:
            for line in f.readlines()[2:]:
                name, rest = line.split(':', 1)
                if name.strip() == 'lo':
                    continue
                p = rest.split()
                rx += int(p[0])
                tx += int(p[8])
        r['_rx'], r['_tx'], r['_t'] = rx, tx, time.time()
        return r

    def read(self):
        """One reading. Returns {signal: value}; rates need two readings."""
        r = self.raw()
        p, self.prev = self.prev, r
        if p is None:
            return {}
        dt = max(r['_t'] - p['_t'], 1e-3)
        da = max(r['_all'] - p['_all'], 1)
        return {'load1': r['load1'], 'cpu': 100.0 * (1 - (r['_idle'] - p['_idle']) / da),
                'mem_avail': r['mem_avail'], 'net_rx': (r['_rx'] - p['_rx']) / dt,
                'net_tx': (r['_tx'] - p['_tx']) / dt, 'ctxt': (r['_ctxt'] - p['_ctxt']) / dt,
                'running': r['running']}

    def feel(self, vals, t):
        """Update the generators. Returns the spikes worth offering: [(focus, value, expected, z)]."""
        out = []
        for k, x in vals.items():
            g = self.gen[k]
            z, e = g.step(x)
            self.last[k], self.z[k], self.exp[k] = x, z, e
            if g.n > WARMUP and abs(z) >= G['z_spike'] and t >= self.quiet.get(k, 0):
                self.quiet[k] = t + G['refractory']
                out.append((k, x, e, z))
        return out

    def vec(self):
        return [round(max(-9.0, min(9.0, self.z.get(k, 0.0))), 2) for k in FLOOR]


class SelfModel:
    """Tells its own from the other by asking which process did the work."""

    def __init__(self):
        self.me = os.getpid()
        self.snap = {}
        self.snap_t = 0.0
        self.cache = (None, None)

    @staticmethod
    def snapshot():
        s = {}
        for name in os.listdir('/proc'):
            if not name.isdigit():
                continue
            try:
                with open(f'/proc/{name}/stat') as f:
                    txt = f.read()
                a, b = txt.index('('), txt.rindex(')')
                p = txt[b + 2:].split()
                s[int(name)] = (int(p[11]) + int(p[12]), txt[a + 1:b], int(p[1]))
            except (OSError, ValueError, IndexError):
                continue
        return s

    def beat(self, t):
        if t - self.snap_t >= 2.0:
            self.snap, self.snap_t = self.snapshot(), t

    def who(self, pid, snap):
        p, hops = pid, 0
        while p and hops < 40:
            if p == self.me:
                return 'self'
            p = snap.get(p, (0, '', 0))[2]
            hops += 1
        try:
            with open(f'/proc/{pid}/cgroup') as f:
                cg = f.read()
        except OSError:
            return 'unknown'
        if 'user.slice' in cg or 'session-' in cg:
            return 'operator'
        if 'system.slice' in cg or 'init.scope' in cg or cg.strip() in ('', '0::/'):
            return 'body'
        return 'unknown'

    def cause(self, t):
        if self.cache[0] == t:
            return self.cache[1]
        cur = self.snapshot()
        best, top, total = None, 0, 0
        for pid, (ticks, _, _) in cur.items():
            d = ticks - self.snap.get(pid, (ticks, '', 0))[0]
            if d > 0:
                total += d
                if d > top:
                    best, top = pid, d
        if best is None or top < 5:
            born = [(v[0], p) for p, v in cur.items() if p not in self.snap and p != self.me]
            if born:                                      # nothing has worked yet, but something was just born
                _, p = max(born)
                c = {'who': self.who(p, cur), 'comm': cur[p][1], 'why': 'just started'}
            else:
                c = {'who': 'unknown', 'why': 'no local process did the work'}
        else:
            c = {'who': self.who(best, cur), 'comm': cur[best][1], 'share': round(top / total, 2)}
        self.cache = (t, c)
        return c

    def on_open(self, m, t):
        self.at_open = self.snapshot()

    def on_close(self, m, t):
        """The second look: who did the most work while the moment lasted."""
        cur, old = self.snapshot(), getattr(self, 'at_open', {})
        work = [(v[0] - old.get(p, (0, '', 0))[0], p) for p, v in cur.items()]
        if work:
            top, p = max(work)
            if top >= 20:
                m['cause_after'] = {'who': self.who(p, cur), 'comm': cur[p][1],
                                    'share': round(top / max(1, sum(w for w, _ in work if w > 0)), 2)}

    def modulate(self, c, t):
        if c['kind'] != 'spike':
            return
        cause = self.cause(t)
        c['data']['cause'] = cause
        c['sal'] *= weight(cause['who'])


class Forecast:
    """Where will the focus signal be when the moment closes, and how sure am I."""

    def __init__(self, senses):
        self.senses = senses
        self.rs = {}       # signal -> past return coefficients
        self.hits = {}     # signal -> past strict hits (0/1)
        self.errs = {}     # signal -> [(err_mean, err_pers)]
        self.n = 0
        self.e_model = self.e_mean = self.e_pers = self.e_pick = 0.0

    def r_hat(self, k):
        own = self.rs.get(k, [])
        if len(own) >= 3:
            r = median(own)
        else:
            every = [x for v in self.rs.values() for x in v]
            r = median(every) if len(every) >= 5 else 0.5
        return max(-0.5, min(2.0, r))

    def p_hit(self, k):
        h = self.hits.get(k, [])
        return (sum(h) + 1) / (len(h) + 2)

    def pick(self, k):
        e = self.errs.get(k, [])
        if len(e) < 3:
            return 0.0
        return 0.0 if sum(a for a, _ in e) <= sum(b for _, b in e) else 1.0

    def on_open(self, m, t):
        if m.get('kind') != 'spike':
            return
        k, r = m['focus'], self.r_hat(m['focus'])
        m['forecast'] = {'r_hat': round(r, 3), 'pred': round(m['e'] + r * (m['v'] - m['e']), 3),
                         'p': round(self.p_hit(k), 2), 'pick': self.pick(k)}

    def on_close(self, m, t):
        f = m.get('forecast')
        if not f or m['v'] == m['e'] or m['focus'] not in self.senses.last:
            return
        r = (self.senses.last[m['focus']] - m['e']) / (m['v'] - m['e'])
        m['check'] = {'r': round(r, 3), 'err': round(min(abs(r - f['r_hat']), 2.0), 3),
                      'mean': round(min(abs(r), 2.0), 3), 'pers': round(min(abs(r - 1), 2.0), 3),
                      'pick': round(min(abs(r - f['pick']), 2.0), 3)}
        m['check']['hit'] = int(m['check']['err'] <= STRICT)
        self.learn(m)

    def learn(self, m):
        c, k = m.get('check'), m.get('focus')
        if not c:
            return
        self.rs.setdefault(k, []).append(max(-0.5, min(2.0, c['r'])))
        self.hits.setdefault(k, []).append(c['hit'])
        self.errs.setdefault(k, []).append((c['mean'], c['pers']))
        for d in (self.rs, self.hits, self.errs):
            del d[k][:-int(G['r_keep'])]
        self.n += 1
        self.e_model += c['err']
        self.e_mean += c['mean']
        self.e_pers += c['pers']
        self.e_pick += c['pick']

    def skill(self):
        if self.n < 20 or not self.e_pick:                # too few checks to speak of skill
            return None
        return round(1 - self.e_model / self.e_pick, 3)


def cos(a, b):
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return 0.0 if not na or not nb else sum(x * y for x, y in zip(a, b)) / (na * nb)


class Memory:
    """Past moments as state vectors. Recognition is same focus and cosine >= 0.9."""

    def __init__(self, senses, keep=5000):
        self.senses = senses
        self.past = []
        self.keep = keep

    def on_open(self, m, t):
        m['vec'] = self.senses.vec()
        best, when = 0.0, None
        for focus, vec, t0 in self.past:
            if focus == m.get('focus'):
                s = cos(vec, m['vec'])
                if s > best:
                    best, when = s, t0
        m['seen'] = {'sim': round(best, 3), 'known': int(best >= 0.9), 'when': when}

    def on_close(self, m, t):
        self.add(m)

    def add(self, m):
        if 'vec' in m:
            self.past.append((m.get('focus'), m['vec'], m.get('t')))
            del self.past[:-self.keep]


class Report:
    """The system's own account, built only from what is in the workspace."""

    def __init__(self, ws, senses, forecast, started):
        self.ws, self.senses, self.fc, self.started = ws, senses, forecast, started

    def state(self, t):
        m = self.ws.open or self.ws.last
        s = {'t': round(t, 1), 'who': 'SunPoint core 1.0', 'pid': os.getpid(),
             'awake_s': int(t - self.started), 'moments': self.ws.n_moments, 'below': self.ws.n_below,
             'offered': self.ws.n_posted, 'checks': self.fc.n, 'skill': self.fc.skill(),
             'in_field': bool(self.ws.open)}
        if m:
            s['noticed'] = {'t': m['t'], 'focus': m.get('focus'), 'v': m.get('v'), 'e': m.get('e'),
                            'who': (m.get('cause') or {}).get('who'), 'known': (m.get('seen') or {}).get('known')}
            if 'forecast' in m:
                s['expect'] = m['forecast']
        return s

    def words(self, t):
        s = self.state(t)
        out = [f"I am {s['who']}, awake for {s['awake_s']} s. {s['moments']} moments reached the field, "
               f"{s['below']} stayed below."]
        n = s.get('noticed')
        if n:
            out.append(f"Last noticed: {n['focus']} at {n['v']:.4g}, expected {n['e']:.4g}; cause: {n['who']}; "
                       f"{'seen before' if n['known'] else 'new to me'}.")
        if s.get('expect'):
            out.append(f"I expect {s['expect']['pred']:.4g} when the moment closes; "
                       f"I am {int(100 * s['expect']['p'])} % sure.")
        if s['skill'] is not None:
            out.append(f"My forecast skill so far: {s['skill']:+.2f} on {s['checks']} checks.")
        return ' '.join(out)
