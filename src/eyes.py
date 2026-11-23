#!/usr/bin/env python3
"""eyes.py - the eyes of SunPoint, v0.2.1.  A separate service: the stream is not consciousness.

Model of consciousness: Khamzin Bauyrzhan Galymzhanovich.   Code: AISun.   MIT licence.

What it does
  * reads live video streams with ffmpeg at 2 frames per second (224 px centre crop);
  * turns every frame into a 512-d vector (CLIP ViT-B/32, fp16 on the GPU) -> NATS subject sp.frames.<cam> (~1.5 KB);
  * once a minute writes a description -> sp.desc.<cam>: zero-shot labels, amount of change, brightness, recognition;
  * once a second: a 64x64 pixel sketch (sp.pix.<cam>, ~1.4 KB) and a contour "lasso" (sp.lasso.<cam>, 512 bytes);
  * keyframe memory: vectors and labels only, no images; every frame looks for a similar keyframe older than
    10 minutes - "I have seen this before" (cross-cutting recognition).

Streams come from the environment, never from the code:
    EYES_STREAMS='cam1|Base station|https://example.org/live/cam1.m3u8;cam2|Summit|https://example.org/live/cam2.m3u8'
Use only streams you are allowed to watch. Nobody is identified: no face recognition, no matching of people.
This module keeps frames in RAM only; vectors, labels and 64x64 sketches go to the stream cache.
NATS is spoken with the raw text protocol (PUB), no client library.  Needs: ffmpeg, torch, transformers, numpy, pillow.
"""
import os, sys, time, json, base64, socket, subprocess, threading, signal, io
from collections import deque
import numpy as np, torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

STREAMS = [x.split('|') for x in os.environ.get('EYES_STREAMS', '').split(';') if x.count('|') == 2]
CAMS = {n: label for n, label, _ in STREAMS}        # camera -> human label of the place
URLS = {n: url for n, _, url in STREAMS}
if not CAMS: sys.exit("eyes.py: set EYES_STREAMS='name|label|url;name|label|url' (see the docstring)")
FPS = 2; SIDE = 224; WINDOW_S = 180; PIX = 64
NATS = ('127.0.0.1', 4222)
BASE = os.environ.get('EYES_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'eyes_data'))
os.makedirs(BASE, exist_ok=True)
LOG = os.path.join(BASE, 'log.txt')
LABELS = ['снежный склон с лыжниками', 'пустой склон', 'кресельный подъёмник', 'толпа людей', 'несколько людей',
          'ратрак или техника', 'туман или облака', 'снегопад', 'ясное небо и солнце', 'закат или рассвет',
          'ночь, темно', 'фонари и освещение', 'горы и скалы', 'город вдали', 'камера закрыта или нет сигнала']
LABELS_EN = ['a snowy ski slope with skiers', 'an empty ski slope', 'a chairlift', 'a crowd of people', 'a few people',
             'a snowcat or machinery', 'fog or clouds', 'snowfall', 'clear sky and sunshine', 'sunset or sunrise',
             'night, dark', 'street lights at night', 'mountains and rocks', 'a city in the distance', 'a blank or broken camera image']

def F(x):
    """transformers 4.x отдаёт тензор, 5.x — объект с pooler_output (проекция)."""
    return x if torch.is_tensor(x) else getattr(x, 'pooler_output', None) if getattr(x, 'pooler_output', None) is not None else x[0]

if os.environ.get('TZ'): time.tzset()        # log times follow $TZ when it is set
KF_PATH = os.path.join(BASE, 'keyframes.npz')
KF_MIN_AGE = 600; KF_MAX = 50000; REC_SIM = 0.93

class Memory:
    """Индекс узнавания: ключевые кадры (вектор 512 + время + камера + метка), без картинок."""
    def __init__(self):
        self.V = np.zeros((0, 512), np.float32); self.T = np.zeros(0, np.float64); self.C = []; self.L = []
        try:
            z = np.load(KF_PATH, allow_pickle=False)
            self.V, self.T = z['V'].astype(np.float32), z['T']; self.C = list(z['C']); self.L = list(z['L'])
        except Exception: pass
    def add(self, vec, t, cam, label):
        self.V = np.vstack([self.V, vec[None].astype(np.float32)])[-KF_MAX:]; self.T = np.append(self.T, t)[-KF_MAX:]
        self.C = (self.C + [cam])[-KF_MAX:]; self.L = (self.L + [label])[-KF_MAX:]
    def recall(self, vec, t, cam):
        if not len(self.T): return None
        mask = (self.T < t - KF_MIN_AGE) & (np.array(self.C) == cam)
        if not mask.any(): return None
        idx = np.where(mask)[0]; sims = self.V[idx] @ vec
        j = int(np.argmax(sims)); s = float(sims[j])
        if s < REC_SIM: return None
        k = idx[j]
        return dict(sim=round(s, 3), when=time.strftime('%d.%m %H:%M', time.localtime(self.T[k])),
                    ago_min=int((t - self.T[k]) / 60), then=self.L[k])
    def save(self):
        try:
            np.savez(KF_PATH + '.tmp.npz', V=self.V, T=self.T, C=np.array(self.C), L=np.array(self.L))
            os.replace(KF_PATH + '.tmp.npz', KF_PATH)
        except Exception as e: log(f'kf save err {e}')

def ts(): return time.strftime('%Y-%m-%d %H:%M:%S')
def log(m):
    with open(LOG, 'a', encoding='utf-8') as f: f.write(f'{ts()} {m}\n')

class Nats:
    def __init__(self): self.s = None; self.lock = threading.Lock()
    def _connect(self):
        s = socket.create_connection(NATS, timeout=5); s.recv(4096)
        s.sendall(b'CONNECT {"verbose":false,"pedantic":false,"name":"eyes_v01"}\r\n'); self.s = s
    def pub(self, subj, obj):
        data = json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode()
        with self.lock:
            for _ in range(2):
                try:
                    if self.s is None: self._connect()
                    import select
                    if select.select([self.s], [], [], 0)[0]:
                        inc = self.s.recv(4096)
                        if not inc: raise ConnectionError('closed')
                        if b'PING' in inc: self.s.sendall(b'PONG\r\n')
                    self.s.sendall(f'PUB {subj} {len(data)}\r\n'.encode() + data + b'\r\n'); return len(data)
                except Exception as e:
                    log(f'nats err {e}'); self.s = None; time.sleep(1)
        return 0

class Eye:
    def __init__(self, cam):
        self.cam = cam; self.win = deque(); self.mean = None; self.n = 0; self.frames = 0; self.last_err = None
        self.minute_vecs = []; self.minute_t = time.time(); self.p = None; self.kf_vec = None; self.kf_t = 0; self.recs = []
    def reader(self, q):
        vf = f'fps={FPS},scale=-2:{SIDE},crop={SIDE}:{SIDE}'
        while RUN[0]:
            try:
                self.p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-i', URLS[self.cam], '-vf', vf,
                                           '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
                sz = SIDE * SIDE * 3
                while RUN[0]:
                    buf = self.p.stdout.read(sz)
                    if len(buf) < sz: break
                    q.append((self.cam, time.time(), buf))
            except Exception as e:
                self.last_err = str(e)
            finally:
                try: self.p.kill()
                except Exception: pass
            if RUN[0]: log(f'{self.cam} поток прервался, переподключение через 10 с'); time.sleep(10)

RUN = [True]
def stop(*_): RUN[0] = False
signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)

def main():
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = CLIPModel.from_pretrained('openai/clip-vit-base-patch32', torch_dtype=torch.float16 if dev == 'cuda' else torch.float32).to(dev).eval()
    proc = CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32')
    with torch.no_grad():
        t = proc(text=LABELS_EN, return_tensors='pt', padding=True).to(dev)
        tvec = F(model.get_text_features(**t)); tvec = tvec / tvec.norm(dim=-1, keepdim=True)
    nats = Nats(); eyes = {c: Eye(c) for c in CAMS}; q = deque(maxlen=60)
    for e in eyes.values(): threading.Thread(target=e.reader, args=(q,), daemon=True).start()
    mem = Memory(); last_kf_save = time.time()
    log(f'start eyes_v02 keyframes={len(mem.T)} dev={dev} cams={list(CAMS)} fps={FPS} side={SIDE}')
    stats = dict(frames=0, bytes=0, desc=0, started=ts())
    last_stat = time.time()
    while RUN[0]:
        if not q: time.sleep(0.05); continue
        batch = [q.popleft() for _ in range(min(len(q), 6))]
        imgs = [Image.frombuffer('RGB', (SIDE, SIDE), b, 'raw', 'RGB', 0, 1) for _, _, b in batch]
        with torch.no_grad():
            px = proc(images=imgs, return_tensors='pt')['pixel_values'].to(dev, dtype=model.dtype)
            v = F(model.get_image_features(pixel_values=px)); v = v / v.norm(dim=-1, keepdim=True)
            sims = (v @ tvec.T).float().cpu().numpy()
        v = v.float().cpu().numpy()
        for (cam, t0, _), img, vec, sim in zip(batch, imgs, v, sims):
            e = eyes[cam]; e.frames += 1
            change = 0.0 if e.mean is None else float(1 - np.dot(vec, e.mean) / (np.linalg.norm(e.mean) + 1e-9))
            e.mean = vec.copy() if e.mean is None else 0.98 * e.mean + 0.02 * vec
            jb = io.BytesIO(); img.save(jb, 'JPEG', quality=70)
            e.win.append((t0, jb.getvalue()))                  # кадр — только RAM, окно 3 мин
            while e.win and e.win[0][0] < t0 - WINDOW_S: e.win.popleft()
            e.minute_vecs.append((vec, sim, change, float(np.asarray(img).mean())))
            top_label = LABELS[int(np.argmax(sim))]
            rec = mem.recall(vec, t0, cam) if e.frames % 2 == 0 else None       # узнавание раз в секунду
            if rec: e.recs.append(rec)
            if e.kf_vec is None or float(np.dot(vec, e.kf_vec)) < 0.97 or t0 - e.kf_t >= 60:   # ключевой кадр
                mem.add(vec, t0, cam, top_label); e.kf_vec = vec.copy(); e.kf_t = t0
            msg = dict(t=round(t0, 2), cam=cam, model='clip-vit-b32', dim=512, change=round(change, 4),
                       v=base64.b64encode(vec.astype(np.float16).tobytes()).decode())
            stats['bytes'] += nats.pub(f'sp.frames.{cam}', msg); stats['frames'] += 1
            if e.frames % FPS == 0:   # a 64x64 pixel sketch once a second (~2 KB): faces cannot be told apart
                pb = io.BytesIO(); img.resize((PIX, PIX), Image.BILINEAR).save(pb, 'JPEG', quality=60)
                stats['bytes'] += nats.pub(f'sp.pix.{cam}', dict(t=round(t0, 2), cam=cam, w=PIX, h=PIX, fmt='jpeg',
                                                                 jpg=base64.b64encode(pb.getvalue()).decode()))
                stats['pix'] = stats.get('pix', 0) + 1
                # «лассо»: контурный рисунок 64×64 (Собель + порог по верхним 15 % перепадов) → 512 байт
                g = np.asarray(img.resize((PIX, PIX), Image.BILINEAR).convert('L'), dtype=np.float32)
                gx = np.zeros_like(g); gy = np.zeros_like(g)
                gx[1:-1, 1:-1] = (g[:-2, 2:] + 2 * g[1:-1, 2:] + g[2:, 2:]) - (g[:-2, :-2] + 2 * g[1:-1, :-2] + g[2:, :-2])
                gy[1:-1, 1:-1] = (g[2:, :-2] + 2 * g[2:, 1:-1] + g[2:, 2:]) - (g[:-2, :-2] + 2 * g[:-2, 1:-1] + g[:-2, 2:])
                mag = np.hypot(gx, gy); mask = mag > max(np.percentile(mag, 85), 20.0)
                stats['bytes'] += nats.pub(f'sp.lasso.{cam}', dict(t=round(t0, 2), cam=cam, w=PIX, h=PIX, fmt='bits',
                                                                   edges=round(float(mask.mean()), 3),
                                                                   bits=base64.b64encode(np.packbits(mask).tobytes()).decode()))
            if t0 - e.minute_t >= 60 and e.minute_vecs:      # описательный файл раз в минуту
                S = np.mean([s for _, s, _, _ in e.minute_vecs], axis=0)
                top = np.argsort(-S)[:4]
                d = dict(t=round(t0, 1), cam=cam, place=CAMS[cam], frames=len(e.minute_vecs),
                         labels=[dict(ru=LABELS[i], score=round(float(S[i]), 3)) for i in top],
                         change_max=round(max(c for _, _, c, _ in e.minute_vecs), 4),
                         change_mean=round(float(np.mean([c for _, _, c, _ in e.minute_vecs])), 4),
                         brightness=round(float(np.mean([b for *_, b in e.minute_vecs])), 1),
                         ram_window_frames=len(e.win),
                         recognized=(max(e.recs, key=lambda r: r['sim']) if e.recs else None),
                         recognized_count=len(e.recs),
                         memory_keyframes=int((np.array(mem.C) == cam).sum()) if mem.C else 0)
                e.recs = []
                stats['bytes'] += nats.pub(f'sp.desc.{cam}', d); stats['desc'] += 1
                e.minute_vecs = []; e.minute_t = t0
        if time.time() - last_kf_save > 600: mem.save(); last_kf_save = time.time()
        if time.time() - last_stat > 300:
            last_stat = time.time()
            ram = sum(len(b) for e in eyes.values() for _, b in e.win)
            log(f'stats {stats} ram_window={ram // 1024} KB per_cam={{{", ".join(f"{c}:{e.frames}" for c, e in eyes.items())}}}')
    mem.save(); log(f'stop clean {stats} keyframes={len(mem.T)}')

if __name__ == '__main__':
    main()
