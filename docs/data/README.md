# Raw outputs of the measurements, 23 November 2026

These files are the unedited outputs of the tools on the reference server. They are in Russian because the
reference deployment speaks Russian; the English tools in `tools/` print the same tables in English.

| File | Tool and command | What it shows |
|---|---|---|
| `baseline_19_moments.ru.txt` | `UNTIL='2026-11-23 13:07:00' baseline_check.py <data dir>` | forecast vs Mean and Persistence on the 19 moments of 12:33–13:06 |
| `baseline_27_moments.ru.txt` | `baseline_check.py <data dir>` at 13:27 | the same on 27 moments |
| `proprio_quiet_148s.ru.md` | `proprio_probe.py 150` at 13:13:58 | CPU by organ in a quiet period, second by second |
| `proprio_one_hour.ru.md` | `proprio_probe.py 3600` at 13:18 | the same for one hour, with the moments of consciousness that fell into it |

Glossary for the Russian organ names: глаза: векторы — eyes: vectors; глаза: полные кадры — eyes: full frames;
память: потоки — memory: streams; память: консолидация — memory: consolidation; наблюдатель v0.5.1 — the observer;
старые наблюдатели — earlier observer versions running for comparison; оператор (ssh) — operator;
языковая модель — language model; зонд — the probe itself; система и прочее — system and other; ядро — kernel.
