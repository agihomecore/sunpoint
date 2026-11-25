"""SunPoint core 1.0 - the loop.

  python3 -I core/run.py              run until stopped (SUNPOINT_CORE_DIR sets the folder)
  python3 -I core/run.py --test 120   live run for N seconds with one self-made load in the middle
  python3 -I core/run.py --selftest   synthetic checks of every part, no /proc needed for most

Stdlib only.
"""
import json
import os
import signal
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from workspace import Workspace                                            # noqa: E402
import parts                                                               # noqa: E402
from parts import Senses, SelfModel, Forecast, Memory, Report, Reserve, Z_UNIT      # noqa: E402


class Core:
    def __init__(self, d):
        self.ws = Workspace(d)
        self.senses = Senses()
        self.me = SelfModel()
        self.fc = Forecast(self.senses)
        self.mem = Memory(self.senses)
        self.reserve = Reserve(d)
        self.started = time.time()
        self.rep = Report(self.ws, self.senses, self.fc, self.started)
        self.ws.modulate(self.me.modulate)
        self.ws.subscribe(self.me)
        self.ws.subscribe(self.mem)
        self.ws.subscribe(self.fc)
        self.genome_m = None
        self.genome()
        self.restored = self.restore()

    def genome(self):
        """Take up the numbers the system has grown for itself (core/grow.py)."""
        p = os.path.join(self.ws.d, 'genome.json')
        try:
            m = os.path.getmtime(p)
            if m == self.genome_m:
                return
            with open(p, encoding='utf-8') as f:
                g = json.load(f)
        except (OSError, ValueError):
            return
        for k, (lo, hi) in parts.BOUNDS.items():
            if k in g.get('g', {}):
                parts.G[k] = min(hi, max(lo, g['g'][k]))
        self.ws.ignite = parts.G['ignite']
        self.genome_m = m
        self.ws.log('life.jsonl', {'t': round(time.time(), 1), 'event': 'genome', 'version': g.get('version'),
                                   'g': parts.G})

    def restore(self):
        """Continuity: what was learned before a restart is learned still."""
        p, n = os.path.join(self.ws.d, 'moments.jsonl'), 0
        if not os.path.exists(p):
            return 0
        with open(p, encoding='utf-8') as f:
            for line in f:
                try:
                    m = json.loads(line)
                except ValueError:
                    continue
                self.fc.learn(m)
                self.mem.add(m)
                self.ws.seq = max(self.ws.seq, m.get('id', 0))
                n += 1
        self.fc.n = 0                      # counters of this life start at zero; the lessons stay
        self.fc.e_model = self.fc.e_mean = self.fc.e_pers = self.fc.e_pick = 0.0
        return n

    def step(self, t):
        vals = self.senses.read()
        if vals:                                          # the raw stream, for replay by core/grow.py
            self.ws.log('raw-' + time.strftime('%Y%m%d', time.gmtime(t)) + '.jsonl',
                        [round(t, 1)] + [round(vals[k], 2) for k in parts.FLOOR])
        self.me.beat(t)
        for k, v, e, z in self.senses.feel(vals, t):
            self.ws.post('senses', 'spike', abs(z) / Z_UNIT, {'focus': k, 'v': round(v, 3), 'e': round(e, 3),
                                                               'z': round(z, 2)})
        self.reserve.look(self.ws, t)
        return self.ws.tick(t)

    def beat(self, t):
        s = self.rep.state(t)
        s['restored'] = self.restored
        s['reserve'] = self.reserve.state
        tmp = os.path.join(self.ws.d, 'state.json.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(s, f, ensure_ascii=False)
        os.replace(tmp, os.path.join(self.ws.d, 'state.json'))
        return s


def run(d, seconds=None, burn_at=None):
    core = Core(d)
    stop = []
    signal.signal(signal.SIGTERM, lambda *_: stop.append(1))
    core.ws.log('life.jsonl', {'t': round(core.started, 1), 'event': 'start', 'restored': core.restored})
    burn = None
    i = 0
    try:
        while not stop and (seconds is None or i < seconds):
            t = time.time()
            if burn_at is not None and i == burn_at:
                burn = subprocess.Popen([sys.executable, '-I', '-c',
                                         'import time\nt=time.time()\nwhile time.time()-t<4: pass'])
                core.ws.log('probe.jsonl', {'t': round(t, 1), 'expected': 'self', 'by': 'run --test'})
            m = core.step(t)
            if m and seconds is not None:
                print(f"moment {m['id']}: {m['focus']} v={m['v']} e={m['e']} z={m['z']} who={m['cause']['who']}")
            if i % 10 == 0:
                core.beat(t)
            if i % 60 == 0:
                core.ws.log('hb.jsonl', core.rep.state(t))
                core.genome()
            i += 1
            time.sleep(max(0.0, 1.0 - (time.time() - t)))
    except KeyboardInterrupt:
        pass
    t = time.time()
    core.ws.close(t)
    core.beat(t)
    core.ws.log('hb.jsonl', core.rep.state(t))
    core.ws.log('life.jsonl', {'t': round(t, 1), 'event': 'stop'})
    if burn:
        burn.wait()
    return core


def selftest():
    d = tempfile.mkdtemp(prefix='spcore_')
    core = Core(d)
    ws, se, fc = core.ws, core.senses, core.fc
    core.me.cause = lambda t: who[0]                      # the self-model's verdict is given by the test
    who = [{'who': 'operator'}]
    for k in se.gen:                                      # a quiet body
        se.last[k], se.z[k] = 1.0, 0.0
    t = 1000.0

    def spike(focus, z, v=10.0, e=2.0):
        ws.post('senses', 'spike', abs(z) / Z_UNIT, {'focus': focus, 'v': v, 'e': e, 'z': z})

    # 1. attention: own work needs a far stronger spike than the outside to enter the field
    who[0] = {'who': 'self'}
    spike('cpu', 6.0)
    assert ws.tick(t) is None and ws.n_below == 1, 'own work at 6 sigma must stay below'
    who[0] = {'who': 'operator'}
    spike('cpu', 6.0)
    m = ws.tick(t + 1)
    assert m and m['cause']['who'] == 'operator' and 'forecast' in m and 'vec' in m, 'an outside spike must ignite'
    # 2. one content holds the field: a second spike joins it as context
    spike('net_rx', 8.0)
    assert ws.tick(t + 2) is None and len(ws.open['also']) == 1, 'the field holds one moment'
    # 3. forecast learns: the signal always returns to 30 % of the spike
    for i in range(12):
        t += 20
        se.z['cpu'] = 5.0 + i * 0.01
        spike('cpu', 6.0)
        ws.tick(t)                                        # closes the previous moment, opens a new one
        se.last['cpu'] = 2.0 + 0.3 * 8.0
    ws.close(t + 10)
    assert abs(fc.r_hat('cpu') - 0.3) < 0.05, f"r_hat should approach 0.3, got {fc.r_hat('cpu')}"
    assert fc.skill() is None and fc.n == 13 and fc.p_hit('cpu') > 0.5, 'confidence must exist; skill waits for 20 checks'
    # 4. memory recognises a repeated state and survives a restart
    assert ws.last['seen']['known'] == 1, 'a repeated state must be recognised'
    again = Core(d)
    assert again.restored == ws.n_moments and abs(again.fc.r_hat('cpu') - 0.3) < 0.05, 'lessons must survive'
    assert len(again.mem.past) == ws.n_moments and again.ws.seq == ws.seq, 'memory must survive'
    # 5. the reserve: a thin pool and a late duty reach the field before anything is missed
    for i in range(3):
        open(os.path.join(d, f'ready_{i}.x'), 'w').close()
    with open(os.path.join(d, 'reserve.json'), 'w') as f:
        json.dump({'pools': [{'name': 'ready', 'glob': os.path.join(d, 'ready_*.x'), 'target': 8}],
                   'duties': [{'name': 'beat', 'file': os.path.join(d, 'no_such_file'), 'every_s': 60}]}, f)
    core.reserve.look(ws, t + 100)
    m = ws.tick(t + 100)
    assert m and m['kind'] == 'reserve' and m['focus'] == 'duty:beat', m
    assert core.reserve.state['ready'] == {'ready': 3, 'target': 8, 'ok': False}, core.reserve.state
    ws.close(t + 111)
    # 6. the report speaks from the workspace
    w = core.rep.words(t + 120)
    assert 'duty:beat' in w and 'cause: self' in w, w
    print('selftest ok:', w)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['--selftest']:
        selftest()
    elif a[:1] == ['--test']:
        n = int(a[1]) if len(a) > 1 else 120
        d = tempfile.mkdtemp(prefix='spcore_')
        c = run(d, seconds=n, burn_at=max(70, n * 2 // 3))
        print(c.rep.words(time.time()))
        print('folder:', d)
    else:
        run(os.environ.get('SUNPOINT_CORE_DIR', os.path.join(os.getcwd(), 'core_window')))
