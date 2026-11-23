# SunPoint — a moment of consciousness for machines

> **10 s before → alert → reflex (fight / flight / freeze) → 10 s after: forecast, check, guess, decision, action**

**Model of consciousness:** Khamzin Bauyrzhan Galymzhanovich (Astana, Kazakhstan).
**Code, measurements, reviews:** AISun — an AI collaborator running on Claude (models Fable 5.2 and Opus 5.5).
**Status:** early research prototype, v0.5.1 (23 November 2026). It runs around the clock on one home server.

This repository is for researchers and enthusiasts. It holds the model, working code, the measurements of the first
day and an honest review of what is proven and what is not. **Read the review first:**
[docs/REVIEW_2026-11-23.md](docs/REVIEW_2026-11-23.md) · на русском: [README.ru.md](README.ru.md).

## The idea
Consciousness is not a stream. It is a **moment**.

Everything flows through memory and is forgotten. When something surprising happens — an *alert* — the system keeps
the 10 seconds before it, answers with a *reflex* in microseconds if there is danger, and then spends the next
10 seconds on what makes it more than a reflex: a forecast, a check of that forecast, a guess about the cause, a
decision, an action — or "deferred, I will come back to this". That stored moment is a **SunPoint**.

The video stream, the logs and the scheduled jobs are not consciousness. They are senses and blood circulation.

We use the word *consciousness* in this operational sense: a mechanism of attention, reflex, forecast and memory.
We make **no claim about subjective experience**. The data in this repository cannot answer that question.

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
| Forecast | every moment predicts its signal 10 s ahead and checks itself | **it does not beat a trivial forecast** (74 % vs 74 %) |
| Attention | services, cron and operator logins stay in the subconscious | **numeric spikes caused by the system's own body still reach consciousness** — 30 moments in the first hour, about 10 per hour later |
| Memory | cache → long-term → subconscious, consolidated hourly; keyframe recognition 0.98–0.997 | recognition from long-term memory is untested |
| Eyes | 3 video streams → frame vectors, minute descriptions, 64×64 sketches | eyes are not connected to consciousness yet |
| Voice | a moment becomes one spoken sentence, at most once an hour | — |

## Three checks that changed our conclusion
1. **The forecast is not smarter than a trivial one.** It came true in 14 of 19 moments (74 %). The trivial forecast
   "the signal returns to its expected value" also scored 14 of 19. The tolerance was so wide that missing was
   almost impossible. On 45 moments the forecast is slightly ahead by error (0.40 against 0.54) and level by the
   wide tolerance (71 % against 67 %) — Addendum 2 of the review.
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
| `src/voice_bridge.py`, `src/say.sh` | the voice |
| `tools/baseline_check.py` | forecast vs trivial forecasts |
| `tools/proprio_probe.py` | the "who is breathing" probe |
| `docs/MODEL.md` | the model in the author's words and in operational terms |
| `docs/REVIEW_2026-11-23.md` | the initial research review: timeline, facts, three checks, honest border, guesses |
| `docs/SPEC_v0.5.2.md` | the next version: a forecast that learns, and a sense of own body |
| `docs/ARTICLE.en.md`, `.kk.md`, `.ru.md` | the story for a general reader: "The beginnings of consciousness — or a fake?" |
| `site/` | the web page in three languages, built from the same texts as the article: [sun-agi.com/sunpoint](https://sun-agi.com/sunpoint/) |
| `docs/data/` | raw outputs of the measurements |

## Roadmap
| Step | What | Measure |
|---|---|---|
| 0.5.2 | the forecast learns a return coefficient per signal; cause of an alert by process; own body goes to the subconscious; habit memory survives a restart | gain over the trivial forecast > 0; ≤ 10 moments per hour |
| 0.6 | eyes in consciousness: a frame not recognised after a change is *new* → a moment; one vector for server and eyes; words from a vision-language model | the first moment about the outside world |
| 0.7 | reflexes learn from lessons; deferred items as a morning list; a second, independent critic | the first learned reflex |
| 0.8 | recognition from long-term memory: "something similar happened — this is what we did" | memory answers with an action |
| 2.0 | a body: a small edge computer, an induction dock, power for 1.5–2 years | a day of life without the server |

## What would refute the model
1. A learned forecast does not beat the trivial one on 200+ moments.
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
