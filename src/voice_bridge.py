#!/usr/bin/env python3
"""voice_bridge.py - SunPoint speaks: a moment of consciousness becomes one spoken sentence on the loudspeakers.

Model of consciousness: Khamzin Bauyrzhan Galymzhanovich.   Code: AISun.   MIT licence.

A sentence is written for the ear, not for the log: the signal has a plain name and a unit, numbers are rounded,
and the generator's expectation is called "usually". A moment about a journal line names only its source - never
addresses, numbers or the line itself.

    log:     Noticed: gpu_mem_mb = 708 (expected 11091). ... the forecast did not come true
    spoken:  Noticed: GPU memory - 708 megabytes, usually 11 gigabytes. The forecast did not come true.

Rules (so that the voice does not become a chatterbox):
  * only moments of consciousness (SUNPOINT lines of the observer log) and reflexes are spoken;
  * an ordinary moment - at most once per VOICE_GAP seconds; with a long gap the sentence also carries the number
    of moments since the last spoken one;
  * a reflex (fight / flight / freeze) - at once, outside the limit;
  * quiet hours: silence, everything is still written to bridge.log.

Environment
    SUNPOINT_LOG     path to the observer's log.txt            (default ./window/log.txt)
    SUNPOINT_SSH     ssh host alias if the log lives on another machine (optional)
    SUNPOINT_OWNER   the name to call, e.g. "Bauyrzhan"        (optional; said at most once per VOICE_NAME_EVERY s)
    SUNPOINT_LANG    ru | en                                   (default en)
    VOICE_TZ         IANA time zone for the quiet hours        (default: local time)
    VOICE_QUIET      "21-10" = silent from 21:00 to 10:00; "none" = no quiet hours   (default 21-10)
    VOICE_GAP        seconds between ordinary sentences        (default 3600; the reference server now runs 150)
    VOICE_NAME_EVERY seconds between calls by name             (default 1800)
Speech is produced by ./say.sh (Piper or espeak-ng, see that file).
"""
import os, re, subprocess, time, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
LOGF = os.environ.get('SUNPOINT_LOG', os.path.join(HERE, 'window', 'log.txt'))
SSH = os.environ.get('SUNPOINT_SSH'); OWNER = os.environ.get('SUNPOINT_OWNER', ''); LANG = os.environ.get('SUNPOINT_LANG', 'en')
SAY = os.path.join(HERE, 'say.sh'); OUT = os.path.join(HERE, 'bridge.log')
_q = os.environ.get('VOICE_QUIET', '21-10')
QUIET = None if _q.lower() in ('none', 'off', '') else tuple(int(x) for x in _q.split('-'))
GAP = int(os.environ.get('VOICE_GAP', '3600')); NAME_EVERY = int(os.environ.get('VOICE_NAME_EVERY', '1800'))
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo(os.environ['VOICE_TZ']) if os.environ.get('VOICE_TZ') else None
except Exception: TZ = None
TAIL = f'tail -n 0 -F {LOGF}'
SRC = ['ssh', '-o', 'BatchMode=yes', '-o', 'ServerAliveInterval=30', SSH, TAIL] if SSH else ['bash', '-c', TAIL]

# signal -> unit: pct, deg, mb (megabytes), kbs (kilobytes per second), '' (a bare number)
UNITS = {'cpu_pct': 'pct', 'gpu_util': 'pct', 'gpu_temp': 'deg', 'gpu_mem_mb': 'mb', 'mem_avail_mb': 'mb', 'mem_free_mb': 'mb',
         'net_rx_kbs': 'kbs', 'net_tx_kbs': 'kbs', 'disk_root_pct': 'pct', 'disk_pct': 'pct', 'load1': '', 'procs': '', 'journal_rate': ''}
T = {'ru': dict(noticed='Заметил: {n} — {v}{per}, обычно {e}.', ok=' Прогноз сбылся.', miss=' Прогноз не сбылся.', reflex='Рефлекс: {k}!',
                since=' Моментов с прошлого раза: {n}.', journal='Заметил новое в журнале: {s}.', journal_any='Заметил новое в системном журнале.',
                today=' Такое сегодня уже было.', yesterday=' Такое было вчера.', before=' Такое уже было раньше.',
                re_n=r'Заметил: (\S+) = ([-\d.]+) \(ждал ([-\d.]+)\)', re_j=r'Заметил: ([A-Za-z_][\w.\-]*)', none_mark='ждал None',
                re_r=r'Рефлекс[:\s]+(бей|беги|замри)', re_sim=r'Похожее состояние было (\d\d)\.(\d\d)', miss_mark='не сбылся', ok_mark='сбылся',
                zero='почти ноль', half='половина', one_half='полтора', and_half='{n} с половиной', per_s=' в секунду',
                units={'pct': ('процент', 'процента', 'процентов'), 'deg': ('градус', 'градуса', 'градусов'), 'mb': ('мегабайт', 'мегабайта', 'мегабайт'),
                       'gb': ('гигабайт', 'гигабайта', 'гигабайт'), 'kbs': ('килобайт', 'килобайта', 'килобайт'), 'mbs': ('мегабайт', 'мегабайта', 'мегабайт')},
                names={'cpu_pct': 'процессор', 'gpu_util': 'видеокарта', 'gpu_temp': 'температура видеокарты', 'gpu_mem_mb': 'память видеокарты',
                       'net_rx_kbs': 'входящая сеть', 'net_tx_kbs': 'исходящая сеть', 'mem_avail_mb': 'свободная память', 'mem_free_mb': 'свободная память',
                       'disk_root_pct': 'диск', 'disk_pct': 'диск', 'load1': 'нагрузка', 'procs': 'число процессов', 'journal_rate': 'поток журнала'},
                sources={'cron': 'расписание задач', 'crontab': 'расписание задач', 'sshd': 'удалённый вход', 'sudo': 'права администратора',
                         'kernel': 'ядро системы', 'systemd': 'системные службы', 'python3': 'программа на питоне', 'python': 'программа на питоне',
                         'dockerd': 'контейнеры', 'docker': 'контейнеры', 'containerd': 'контейнеры', 'NetworkManager': 'сеть', 'tailscaled': 'защищённая сеть',
                         'nginx': 'веб-сервер', 'apt': 'обновления', 'snapd': 'обновления', 'PackageKit': 'обновления', 'fwupd': 'обновления', 'fwupdmgr': 'обновления'}),
     'en': dict(noticed='Noticed: {n} — {v}{per}, usually {e}.', ok=' The forecast came true.', miss=' The forecast did not come true.', reflex='Reflex: {k}!',
                since=' Moments since last time: {n}.', journal='Noticed something new in the journal: {s}.', journal_any='Noticed something new in the system journal.',
                today=' This already happened today.', yesterday=' This happened yesterday.', before=' This has happened before.',
                re_n=r'Noticed: (\S+) = ([-\d.]+) \(expected ([-\d.]+)\)', re_j=r'Noticed: ([A-Za-z_][\w.\-]*)', none_mark='expected None',
                re_r=r'Reflex[:\s]+(fight|flight|freeze)', re_sim=r'A similar state was at (\d\d)\.(\d\d)', miss_mark='did not come true', ok_mark='came true',
                zero='almost zero', half='a half', one_half='one and a half', and_half='{n} and a half', per_s=' per second',
                units={'pct': ('percent',) * 3, 'deg': ('degree', 'degrees', 'degrees'), 'mb': ('megabyte', 'megabytes', 'megabytes'),
                       'gb': ('gigabyte', 'gigabytes', 'gigabytes'), 'kbs': ('kilobyte', 'kilobytes', 'kilobytes'), 'mbs': ('megabyte', 'megabytes', 'megabytes')},
                names={'cpu_pct': 'CPU', 'gpu_util': 'GPU', 'gpu_temp': 'GPU temperature', 'gpu_mem_mb': 'GPU memory',
                       'net_rx_kbs': 'inbound network', 'net_tx_kbs': 'outbound network', 'mem_avail_mb': 'free memory', 'mem_free_mb': 'free memory',
                       'disk_root_pct': 'disk', 'disk_pct': 'disk', 'load1': 'load', 'procs': 'number of processes', 'journal_rate': 'journal flow'},
                sources={'cron': 'the schedule', 'crontab': 'the schedule', 'sshd': 'a remote login', 'sudo': 'administrator rights',
                         'kernel': 'the kernel', 'systemd': 'system services', 'python3': 'a Python program', 'python': 'a Python program',
                         'dockerd': 'containers', 'docker': 'containers', 'containerd': 'containers', 'NetworkManager': 'the network', 'tailscaled': 'the private network',
                         'nginx': 'the web server', 'apt': 'updates', 'snapd': 'updates', 'PackageKit': 'updates', 'fwupd': 'updates', 'fwupdmgr': 'updates'})}
L = T.get(LANG, T['en']); RE_N, RE_R, RE_J, RE_SIM = (re.compile(L[k]) for k in ('re_n', 're_r', 're_j', 're_sim'))
last = [0.0, 0.0]; seen = [0]      # [time of the last ordinary sentence, time of the last call by name]; moments since then

def log(s):
    with open(OUT, 'a', encoding='utf-8') as f: f.write(datetime.datetime.now(TZ).strftime('%F %T ') + s + '\n')

def form(n, forms):
    """Pick the noun form for a whole number (Russian has three; English uses the first for 1 and the second otherwise)."""
    n = abs(int(n))
    if LANG != 'ru': return forms[0] if n == 1 else forms[1]
    if n % 10 == 1 and n % 100 != 11: return forms[0]
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14: return forms[1]
    return forms[2]

def spoken(v, unit):
    """A number for the ear: rounded to a whole (to a half below ten), megabytes become gigabytes above a thousand."""
    v = abs(v) if unit else v
    if unit == 'mb' and v >= 1000: v, unit = v / 1024, 'gb'
    if unit == 'kbs' and v >= 1000: v, unit = v / 1024, 'mbs'
    if abs(v) < 0.25: return L['zero']
    frac = False
    if abs(v) < 10:
        h = round(v * 2) / 2
        if h == int(h): w, n = str(int(h)), int(h)
        else:
            frac, n = True, 2
            w = L['half'] if h == 0.5 else L['one_half'] if h == 1.5 else L['and_half'].format(n=int(h))
    else: w, n = str(int(round(v))), int(round(v))
    forms = L['units'].get(unit)
    return w if not forms else f'{w} {forms[1] if frac else form(n, forms)}'

def when(line):
    m = RE_SIM.search(line)
    if not m: return ''
    today = datetime.datetime.now(TZ).date()
    try: d = datetime.date(today.year, int(m.group(2)), int(m.group(1)))
    except ValueError: return ''
    return L['today'] if d == today else L['yesterday'] if (today - d).days == 1 else L['before']

def phrase(line):
    """One log line -> (is_reflex, sentence) or (False, None)."""
    r = RE_R.search(line)
    if r: return True, L['reflex'].format(k=r.group(1))
    m = RE_N.search(line)
    if m:
        k, v, e = m.group(1), float(m.group(2)), float(m.group(3))
        unit = UNITS.get(k, '')
        t = L['noticed'].format(n=L['names'].get(k, k.replace('_', ' ')), v=spoken(v, unit), e=spoken(e, unit), per=L['per_s'] if unit == 'kbs' else '')
        if L['miss_mark'] in line: t += L['miss']
        elif L['ok_mark'] in line: t += L['ok']
        return False, t + when(line)
    j = RE_J.search(line)
    if j and L['none_mark'] in line:                       # a journal line: say where it came from, never what it said
        s = L['sources'].get(j.group(1).rstrip(':'))
        return False, (L['journal'].format(s=s) if s else L['journal_any']) + when(line)
    return False, None

def allowed(is_reflex):
    if QUIET:
        h = datetime.datetime.now(TZ).hour; q0, q1 = QUIET
        if (h >= q0 or h < q1) if q0 > q1 else (q0 <= h < q1): return False, 'quiet hours'
    if is_reflex: return True, ''
    if time.time() - last[0] < GAP: return False, 'pause'
    return True, ''

def main():
    log('start')
    while True:
        p = subprocess.Popen(SRC, stdout=subprocess.PIPE, text=True, errors='replace')
        for line in p.stdout:
            if ' SUNPOINT ' not in line: continue
            is_reflex, text = phrase(line)
            if not text: continue
            if not is_reflex: seen[0] += 1
            ok, why = allowed(is_reflex)
            if not ok: log(f'silent ({why}): ' + text); continue
            if not is_reflex and GAP >= 600 and seen[0] > 1: text += L['since'].format(n=seen[0])
            now = time.time()
            if OWNER and now - last[1] >= NAME_EVERY: text = f'{OWNER}. {text}'; last[1] = now
            try: subprocess.run([SAY, text], timeout=90)
            except Exception as ex: log(f'say.sh failed: {ex}')
            if not is_reflex: last[0] = time.time(); seen[0] = 0
            log('said: ' + text)
        log('source closed, retry in 30 s'); time.sleep(30)

if __name__ == '__main__':
    main()
