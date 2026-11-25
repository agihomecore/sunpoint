# SunPoint — a moment of consciousness for machines

> **10 s before → alert → reflex (fight / flight / freeze) → 10 s after: forecast, check, guess, decision, action**

**Model of consciousness:** Khamzin Bauyrzhan Galymzhanovich (Astana, Kazakhstan).
**Code, measurements, reviews:** AISun — an AI collaborator running on Claude (models Fable 5.2 and Opus 5.5).
**Status:** early research prototype, v0.5.2 (25 November 2026). It runs around the clock on one home server.
**New in 0.5.2:** the forecast learns per signal, the body's own clock goes to the subconscious, the generator survives a restart. Built and self-tested; its live numbers are not measured yet — everything below was measured on 0.5.1.
**Latest numbers:** two days, 254 checked forecasts — [docs/REVIEW_2026-11-25.md](docs/REVIEW_2026-11-25.md).

This repository is for researchers and enthusiasts. It holds the model, working code, the measurements of the first
day and an honest review of what is proven and what is not. **Read the reviews first:**
[docs/REVIEW_2026-11-23.md](docs/REVIEW_2026-11-23.md), then the interim review after two days,
[docs/REVIEW_2026-11-25.md](docs/REVIEW_2026-11-25.md) · на русском: [README.ru.md](README.ru.md).

## The idea
Consciousness is not a stream. It is a **moment**.

Everything flows through memory and is forgotten. When something surprising happens — an *alert* — the system keeps
the 10 seconds before it, answers with a *reflex* in microseconds if there is danger, and then spends the next
10 seconds on what makes it more than a reflex: a forecast, a check of that forecast, a guess about the cause, a
decision, an action — or "deferred, I will come back to this". That stored moment is a **SunPoint**.

The video stream, the logs and the scheduled jobs are not consciousness. They are senses and blood circulation.

**The goal is stated openly: to build an AI with full consciousness** — eight measurable abilities with numeric
targets, reached at once in one system and confirmed by outsiders. Today the index is **0 of 8**:
[docs/GOAL.md](docs/GOAL.md).

What we measure is what the system *does*: attention, reflex, forecast, memory, self-model, action. That is the
operational sense of the word *consciousness* in this repository. We make **no claim about subjective experience**,
for or against. The data here cannot answer that question.

## Three levels
| Level | What it is | Horizon |
|---|---|---|
| Superconscious | meeting the new for the first time, learning it | the moment of meeting |
| Conscious = SunPoint | ±10 s around an alert | seconds |
| Subconscious | memory, rhythms, habits, reflexes, long plans; all routine work of the body | hours to years |

## What works today, and what does not
| | Works | Does not work yet |
|---|---|---|
| Moment | a SunPoint is ~1.4 KB: the generator's expectations plus only the deviations | — |
| Reflex | a rule table answers in 3–11 µs, before any thinking | never fired in the field: there was no danger |
| Forecast | every moment predicts its signal 10 s ahead and checks itself | **it does not beat a trivial forecast**: on 254 moments it is ahead by mean error (0.66 vs 0.72) and behind by strict hits (20 % vs 41 %). The learned rule of 0.5.2, replayed on the same moments, does beat it (0.47; 67 %) — it is not built into the observer yet |
| Attention | services, cron and operator logins stay in the subconscious | **numeric spikes caused by the system's own body still reach consciousness** — 30 moments in the first hour, about 7 per hour after two days; at least 43 % of them repeat by the clock of the body's own schedule |
| Memory | cache → long-term → subconscious, consolidated hourly; keyframe recognition 0.98–0.997 | recognition from long-term memory is untested |
| Eyes | 3 video streams → frame vectors, minute descriptions, 64×64 sketches | eyes are not connected to consciousness yet |
| Voice | a moment becomes one spoken sentence written for the ear ("GPU memory — 708 megabytes, usually 11 gigabytes"), by default at most once an hour | it only speaks; it does not listen |

## Three checks that changed our conclusion
1. **The forecast is not smarter than a trivial one.** It came true in 14 of 19 moments (74 %). The trivial forecast
   "the signal returns to its expected value" also scored 14 of 19. The tolerance was so wide that missing was
   almost impossible. On 74 moments the forecast is ahead by error (0.42 against 0.53) and behind by hits
   (59 % against 64 %) — Addendum 3 of the review. On 254 moments the verdict is the same; a coefficient learned
   per signal beats the fixed trivial forecasts (skill +0.34) and leads a tougher one by only 0.06 —
   [interim review](docs/REVIEW_2026-11-25.md).
2. **Every signal has its own character.** CPU, network and GPU load fall back within 10 s (median `r` 0.1–0.3);
   the load average keeps rising (`r` 1.1); GPU memory moves in steps. One fixed rule fits none of them.
3. **Consciousness mostly notices itself.** In a quiet period 95 % of the CPU load and 97 % of the load peaks came
   from the system's own body — 83 % from its eyes. A brain cancels the sensations of its own actions
   (the efference copy). SunPoint does not do that yet. Over a full hour the body was 85 % of the load; 13 of 19
   moments had a known cause, and all 13 were internal — the system's own organs or its operator.

Scripts and raw outputs: [tools/](tools/), [docs/data/](docs/data/). Next version: [docs/SPEC_v0.5.2.md](docs/SPEC_v0.5.2.md).

## Quick start
The observer needs Linux and Python 3.9+, nothing else.

```bash
git clone https://github.com/agihomecore/sunpoint && cd sunpoint/src

python3 -I sunpoint.py --selftest                 # checks of the forecast rule, the clock habit and the saved generator
python3 -I sunpoint.py --test 120                 # dry run with simulated time
SPIKE_AT=40 python3 -I sunpoint.py --test 120     # the same with a CPU spike: a SunPoint is stored
cat window/first_voice.md                         # its first words

python3 -I sunpoint.py                            # real run: the senses of this machine, data in ./window
python3 -I ../tools/baseline_check.py window      # is the forecast better than a trivial one?
python3 -I ../tools/proprio_probe.py 150 window/log.txt    # who is breathing: CPU by organ, second by second
```

Words are spoken in English or Russian (`SUNPOINT_LANG=ru`). Optional settings: `src/sunpoint.conf.example.json`.
The eyes need ffmpeg, PyTorch, transformers and a NATS server with JetStream; streams are given in `EYES_STREAMS`.

## Repository map
| Path | What |
|---|---|
| `src/sunpoint.py` | the observer: senses, generator, alert, reflex, forecast, SunPoint, plans (stdlib only) |
| `src/eyes.py` | the eyes: frame vectors (CLIP), minute descriptions, pixel sketch, contour, keyframe recognition |
| `src/consolidate.py` | memory consolidation: cache → long-term → subconscious |
| `src/voice_bridge.py`, `src/say.sh`, `src/tts.py` | the voice: a moment as a sentence for the ear; speech through Piper or espeak-ng |
| `tools/baseline_check.py` | forecast vs trivial forecasts |
| `tools/proprio_probe.py` | the "who is breathing" probe |
| `docs/MODEL.md` | the model in the author's words and in operational terms |
| `docs/REVIEW_2026-11-23.md` | the initial research review: timeline, facts, three checks, honest border, guesses |
| `docs/REVIEW_2026-11-25.md` | the interim review after two days: 254 checked forecasts, the clock of the body, the voice fault |
| `core/` | **SunPoint core 1.0, written from zero**: a shared workspace (`workspace.py`), the parts (`parts.py`: senses, self-model, forecast with confidence, memory, report), the loop (`run.py`), the eight indicators from raw logs (`measure.py`), a probe with a known cause (`probe.py`). A first slice, running in shadow next to 0.5.2 |
| `docs/GOAL.md`, `.ru.md` | the main goal: full consciousness for an AI — eight abilities, indicators, stages, stop conditions |
| `docs/SPEC_v0.5.2.md` | the next version: a forecast that learns, and a sense of own body |
| `docs/ARTICLE.en.md`, `.kk.md`, `.ru.md` | the story for a general reader: "The beginnings of consciousness — or a fake?" |
| `site/` | the web page in three languages, built from the same texts as the article: [sun-agi.com/sunpoint](https://sun-agi.com/sunpoint/) |
| `docs/data/` | raw outputs of the measurements |

## Roadmap
| Step | What | Measure |
|---|---|---|
| 0.5.2 — built 25.11 | the forecast learns a return coefficient per signal, with three trivial forecasts scored next to it; scheduled work of the body (by announcement or by the clock) goes to the subconscious; the generator survives a restart | live skill > 0 against the tougher trivial forecast on 200+ checks; no conscious moment from the body's schedule |
| 0.5.3 | the cause of an alert by process: own organs and the operator go to the subconscious; the forecast for GPU load uses the cause | fewer than half of the remaining moments are internal |
| 0.6 | eyes in consciousness: a frame not recognised after a change is *new* → a moment; one vector for server and eyes; words from a vision-language model | the first moment about the outside world |
| 0.7 | reflexes learn from lessons; deferred items as a morning list; a second, independent critic | the first learned reflex |
| 0.8 | recognition from long-term memory: "something similar happened — this is what we did" | memory answers with an action |
| 2.0 | a body: a small edge computer, an induction dock, power for 1.5–2 years | a day of life without the server |

## What would refute the model
1. A learned forecast does not beat the trivial one on 200+ moments. *First test, 25 November: it did not come true
   in a replay on 254 stored moments; it has to be repeated live.*
2. After the own-body filter, fewer than half of the remaining moments are worth attention.
3. Recognition from long-term memory falls below 0.9 on the same scenes.

## Privacy and ethics
- No keys, passwords or addresses are read or stored. Journal lines are kept as templates without digits or keys.
- The eyes watch only streams you give them. Use streams you are allowed to watch.
- Nobody is identified: no face recognition, no matching of people. The reference setup watched public live
  streams; during the research phase full frames were kept in a 7-day ring on a local disk.
- This is a functional model. Please do not present it as proof that a machine feels something.

## Contributing
Issues and pull requests are welcome. The rules are short: [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits and licence
The model of consciousness and the direction of the work: **Khamzin Bauyrzhan Galymzhanovich**.
Code, measurements and texts: **AISun**, his AI collaborator (Claude by Anthropic). This is an independent project;
Anthropic is not affiliated with it and does not endorse it.

MIT licence — see [LICENSE](LICENSE). Authors: Khamzin Bauyrzhan Galymzhanovich and Aisun.
