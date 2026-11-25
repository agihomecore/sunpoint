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
from parts import Senses, SelfModel, Forecast, Memory, Report, Z_SPIKE     # noqa: E402


class Core:
    def __init__(self, d):
        self.ws = Workspace(d)
        self.senses = Senses()
        self.me = SelfModel()
        self.fc = Forecast(self.senses)
        self.mem = Memory(self.senses)
        self.started = time.time()
        self.rep = Report(self.ws, self.senses, self.fc, self.started)
        self.ws.modulate(self.me.modulate)
        self.ws.subscribe(self.me)
        self.ws.subscribe(self.mem)
        self.ws.subscribe(self.fc)
        self.restored = self.restore()

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
        self.me.beat(t)
        for k, v, e, z in self.senses.feel(vals, t):
            self.ws.post('senses', 'spike', abs(z) / Z_SPIKE, {'focus': k, 'v': round(v, 3), 'e': round(e, 3),
                                                               'z': round(z, 2)})
        return self.ws.tick(t)

    def beat(self, t):
        s = self.rep.state(t)
        s['restored'] = self.restored
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
        ws.post('senses', 'spike', abs(z) / Z_SPIKE, {'focus': focus, 'v': v, 'e': e, 'z': z})

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
    # 5. the report speaks from the workspace
    w = core.rep.words(t + 11)
    assert 'cause: operator' in w and 'sure' in w, w
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
