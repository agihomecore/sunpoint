"""SunPoint core 1.0 - the shared workspace (the field).

Parts post candidates. Modulators (the self-model) annotate them and scale their
salience. One content at a time ignites, occupies the field for `span` seconds and is
broadcast to every subscriber. Everything else stays below: counted and logged briefly.

Stdlib only. No host names or addresses are written by this module.
"""
import json
import os


class Workspace:
    def __init__(self, d, ignite=1.0, span=10.0):
        self.d = d
        os.makedirs(d, exist_ok=True)
        self.ignite = ignite      # salience needed to enter the field
        self.span = span          # seconds a moment holds the field
        self.cands = []
        self.mods = []            # fn(candidate, t): annotate, scale salience
        self.subs = []            # objects with on_open(m, t) / on_close(m, t)
        self.open = None          # the moment now in the field
        self.last = None          # the last closed moment
        self.seq = 0
        self.n_posted = 0
        self.n_moments = 0
        self.n_below = 0

    def post(self, src, kind, sal, data):
        self.cands.append({'src': src, 'kind': kind, 'sal': float(sal), 'raw': float(sal), 'data': data})

    def modulate(self, fn):
        self.mods.append(fn)

    def subscribe(self, part):
        self.subs.append(part)

    def log(self, name, rec):
        with open(os.path.join(self.d, name), 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False, separators=(',', ':')) + '\n')

    @staticmethod
    def brief(c, t):
        d = c['data']
        return {'t': round(t, 1), 'focus': d.get('focus'), 'z': d.get('z'), 'sal': round(c['sal'], 2),
                'raw': round(c['raw'], 2), 'who': (d.get('cause') or {}).get('who'),
                'level': d.get('level'), 'gate': d.get('gate')}

    def tick(self, t):
        """One step of the competition. Returns the moment opened on this tick, or None."""
        cands, self.cands = self.cands, []
        self.n_posted += len(cands)
        for c in cands:
            for m in self.mods:
                m(c, t)
        if self.open and t - self.open['t'] >= self.span:
            self.close(t)
        cands.sort(key=lambda c: -c['sal'])
        opened = None
        for c in cands:
            if c['sal'] < self.ignite:
                self.n_below += 1
                self.log('below.jsonl', self.brief(c, t))
            elif self.open is None:
                self.seq += 1
                self.n_moments += 1
                m = {'id': self.seq, 't': round(t, 1), 'src': c['src'], 'kind': c['kind'],
                     'sal': round(c['sal'], 2), 'raw': round(c['raw'], 2), 'also': []}
                m.update(c['data'])
                self.open = opened = m
                for s in self.subs:
                    if hasattr(s, 'on_open'):
                        s.on_open(m, t)
            else:
                self.open['also'].append(self.brief(c, t))   # joins the moment as context
        return opened

    def close(self, t):
        m, self.open = self.open, None
        if m is None:
            return None
        for s in self.subs:
            if hasattr(s, 'on_close'):
                s.on_close(m, t)
        self.log('moments.jsonl', m)
        self.last = m
        return m
