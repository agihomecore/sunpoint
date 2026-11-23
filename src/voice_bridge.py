#!/usr/bin/env python3
"""voice_bridge.py - SunPoint speaks: a moment of consciousness becomes one spoken sentence on the loudspeakers.

Model of consciousness: Khamzin Bauyrzhan Galymzhanovich.   Code: AISun.   MIT licence.

Rules (so that the voice does not become a chatterbox):
  * only moments of consciousness (SUNPOINT lines of the observer log) and reflexes are spoken;
  * an ordinary moment - at most once an hour, with the number of moments since the last spoken one;
  * a reflex (fight / flight / freeze) - at once, outside the hourly limit;
  * quiet hours (default 21:00-10:00): silence, everything is still written to bridge.log.

Environment
    SUNPOINT_LOG     path to the observer's log.txt            (default ./window/log.txt)
    SUNPOINT_SSH     ssh host alias if the log lives on another machine (optional)
    SUNPOINT_OWNER   the name to call, e.g. "Bauyrzhan"        (optional)
    SUNPOINT_LANG    ru | en                                   (default en)
    VOICE_TZ         IANA time zone for the quiet hours        (default: local time)
    VOICE_QUIET      "21-10" = silent from 21:00 to 10:00
Speech is produced by ./say.sh (Piper or espeak-ng, see that file).
"""
import os, re, subprocess, time, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
LOGF = os.environ.get('SUNPOINT_LOG', os.path.join(HERE, 'window', 'log.txt'))
SSH = os.environ.get('SUNPOINT_SSH'); OWNER = os.environ.get('SUNPOINT_OWNER', ''); LANG = os.environ.get('SUNPOINT_LANG', 'en')
SAY = os.path.join(HERE, 'say.sh'); OUT = os.path.join(HERE, 'bridge.log')
Q0, Q1 = [int(x) for x in os.environ.get('VOICE_QUIET', '21-10').split('-')]
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo(os.environ['VOICE_TZ']) if os.environ.get('VOICE_TZ') else None
except Exception: TZ = None
GAP, PER_H = 3600, 1
TAIL = f'tail -n 0 -F {LOGF}'
SRC = ['ssh', '-o', 'BatchMode=yes', '-o', 'ServerAliveInterval=30', SSH, TAIL] if SSH else ['bash', '-c', TAIL]
T = {'ru': dict(noticed='заметил: {n} {v}, ждал {e}.', ok=' Прогноз сбылся.', miss=' Прогноз не сбылся.', reflex='рефлекс: {k}.',
                since=' Моментов с прошлого раза: {n}.', re_n=r'Заметил: (\S+) = ([-\d.]+) \(ждал ([-\d.]+)\)',
                re_r=r'Рефлекс: (бей|беги|замри)', miss_mark='не сбылся', ok_mark='сбылся',
                names={'cpu_pct': 'процессор', 'gpu_util': 'видеокарта', 'gpu_temp': 'температура видеокарты', 'gpu_mem_mb': 'память видеокарты',
                       'net_rx_kbs': 'входящая сеть', 'net_tx_kbs': 'исходящая сеть', 'mem_avail_mb': 'свободная память',
                       'disk_root_pct': 'диск', 'load1': 'нагрузка', 'procs': 'число процессов'}),
     'en': dict(noticed='noticed: {n} {v}, expected {e}.', ok=' The forecast came true.', miss=' The forecast did not come true.', reflex='reflex: {k}.',
                since=' Moments since last time: {n}.', re_n=r'Noticed: (\S+) = ([-\d.]+) \(expected ([-\d.]+)\)',
                re_r=r'Reflex: (fight|flight|freeze)', miss_mark='did not come true', ok_mark='came true',
                names={'cpu_pct': 'CPU', 'gpu_util': 'GPU', 'gpu_temp': 'GPU temperature', 'gpu_mem_mb': 'GPU memory',
                       'net_rx_kbs': 'inbound network', 'net_tx_kbs': 'outbound network', 'mem_avail_mb': 'free memory',
                       'disk_root_pct': 'disk', 'load1': 'load', 'procs': 'number of processes'})}
L = T.get(LANG, T['en']); RE_N = re.compile(L['re_n']); RE_R = re.compile(L['re_r'])
spoken = []; seen = [0]

def log(s):
    with open(OUT, 'a', encoding='utf-8') as f: f.write(datetime.datetime.now(TZ).strftime('%F %T ') + s + '\n')

def num(x):
    v = float(x)
    return str(int(round(v))) if abs(v) >= 10 else str(round(v, 1))

def phrase(line):
    """One log line -> (is_reflex, sentence) or (False, None)."""
    call = (OWNER + ', ') if OWNER else ''
    r = RE_R.search(line)
    if r: return True, call + L['reflex'].format(k=r.group(1))
    m = RE_N.search(line)
    if not m: return False, None
    k, v, e = m.groups()
    t = call + L['noticed'].format(n=L['names'].get(k, k.replace('_', ' ')), v=num(v), e=num(e))
    if L['miss_mark'] in line: t += L['miss']
    elif L['ok_mark'] in line: t += L['ok']
    return False, t[0].upper() + t[1:]

def allowed(is_reflex):
    h = datetime.datetime.now(TZ).hour
    quiet = (h >= Q0 or h < Q1) if Q0 > Q1 else (Q0 <= h < Q1)
    if quiet: return False, 'quiet hours'
    if is_reflex: return True, ''
    t = time.time()
    while spoken and t - spoken[0] > 3600: spoken.pop(0)
    if spoken and t - spoken[-1] < GAP: return False, 'pause'
    if len(spoken) >= PER_H: return False, 'hourly limit'
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
            if ok:
                if not is_reflex and seen[0] > 1: text += L['since'].format(n=seen[0])
                subprocess.run([SAY, text], timeout=60)
                if not is_reflex: spoken.append(time.time()); seen[0] = 0
                log('said: ' + text)
            else:
                log(f'silent ({why}): ' + text)
        log('source closed, retry in 30 s'); time.sleep(30)

if __name__ == '__main__':
    main()
