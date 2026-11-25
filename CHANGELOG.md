# Changelog

All times are 23 November 2026, Astana time. Alerts per hour are measured on the same server.

| Version | Time | Change | Alerts per hour | Result |
|---|---|---|---|---|
| 0.4 | 01:25 | 3-minute window, alert above 3 % of surprise | ~31 | 10–13 % worth attention |
| 0.4.1 | 02:51 | one event = one SunPoint; focus + guesses + actions; noise floors; fingerprints masked | ~6 | 50–65 % worth attention |
| 0.4.2 | 04:01 | events merged within 60 s; cause process; operator login | ~8.5 | ~85 % of alerts were rhythm |
| 0.4.3 | 07:32 | rhythm = automatism (time slots) | ~6.5 | rhythm helped little |
| 0.5 | 12:28 | the "±10 s" model: reflex, forecast and check, state vector, generator + deviations | — | a moment is 1.3–1.4 KB; first voice at 12:34 |
| **0.5.1** | 12:40 | background plans every minute; memory of spike strength | **~33** | noisy again: the rhythm filter was lost — see the review |

Other parts, same day: memory streams (cache / long-term / subconscious), eyes 0.1 → 0.2.1, hourly consolidation,
voice on loudspeakers (13:04).

**0.5.1 is the first public version.** Next: 0.5.2 — see `docs/SPEC_v0.5.2.md`.

## 23 November, 14:30 — review addendum
- One-hour probe added to the review (`docs/REVIEW_2026-11-23.md`, Addendum) with its raw output in `docs/data/`.
- Found by the probe and fixed on the reference server: the full-frame capture had been running twice.
- `docs/SPEC_v0.5.2.md`, section 7: what the hour changes for 0.5.2.
- Articles: the rate is now given as 19–33 moments per hour; the text says who wrote it.

## 23 November, 15:10 — the page, the new article, a re-check
- Article rewritten as a claim check: "The beginnings of consciousness — or a fake?" (`docs/ARTICLE.en.md`, `.kk.md`, `.ru.md`).
- `site/`: the same texts as a web page in English, Kazakh and Russian (`site/build.py`, `site/strings.py`).
- Review, Addendum 2: the forecast re-checked on 45 moments; raw output in `docs/data/baseline_45_moments.ru.txt`.

## 23 November, 17:45 — five hours of data, a word from Bauyrzhan
- Review, Addendum 3: the forecast re-checked on 74 moments. It is level with the trivial forecast again — ahead by
  error, behind by hits. Nine of the 76 moments are the body's own hourly schedule. Raw outputs:
  `docs/data/baseline_74_moments.ru.txt`, `docs/data/state_1737.txt`.
- Article and page: the check table, the charts and the byline carry the 17:40 numbers.
- Article and page: a new section, "A word from Bauyrzhan" — his statement of 15:16 and what the check says about it.

## 25 November, 00:40 — two days of data, the voice repaired
- Interim review: `docs/REVIEW_2026-11-25.md` (Russian: `.ru.md`). 254 checked forecasts — the bar of 200 is reached.
  The running forecast is still level with a trivial one. The learned rule of 0.5.2, replayed on the stored moments,
  beats the fixed trivial forecasts (error 0.47 against 0.72, skill +0.34) and leads a tougher one by 0.06.
  About 7 moments per hour; at least 43 % of them repeat by the clock of the body's own schedule.
- `tools/baseline_check.py`: replay of the 0.5.2 rule on past moments only, skill, a tougher trivial forecast
  (Mean or Persistence per signal), medians, block bootstrap, rate per day and hour, clock slots; `BRIEF=1`.
- Voice. Fault found on the reference server: the synthesiser's command-line tool returned 0.8 s of audio for any
  text, so the loudspeakers had played fragments since 23 November. `src/tts.py` and `src/say.sh` now use the Python
  interface of Piper (`VOICE_PYTHON`, `VOICE_SPEED`, `VOICE_VOLUME` replace `VOICE_PIPER`).
- `src/voice_bridge.py`: sentences for the ear — plain names, units, rounded numbers, "usually" for the expectation;
  a journal moment names only its source. New settings: `VOICE_GAP`, `VOICE_NAME_EVERY`, `VOICE_QUIET=none`.
  Defaults are unchanged: at most one ordinary sentence an hour, silent from 21:00 to 10:00.
- `docs/SPEC_v0.5.2.md`, section 8: what two days change — a tougher trivial forecast as the bar, the cause before
  the coefficient for GPU load, scheduled work first.
- Raw outputs: `docs/data/baseline_254_moments.txt`, `state_2511_0010.txt`, `proprio_2511_148s.md`.
- Not done: 0.5.2 itself. It was planned for 24 November.

## 25 November, 01:30 — version 0.5.2
| Version | Change | Measured |
|---|---|---|
| **0.5.2** | the forecast learns a return coefficient per signal and is scored against three trivial forecasts; the body's scheduled work — by announcement or by the clock — goes to the subconscious; the generator survives a restart and is rebuilt from stored moments on a first start | self-test and dry runs pass; **no live numbers yet** |

- `src/sunpoint.py`: `--selftest`; `generator.json`, `announce.jsonl`; new heartbeat counters `checks`, `skill`, `skill_fixed`, `by_clock`, `announced`.
- `src/consolidate.py` announces itself when `SUNPOINT_ANNOUNCE` is set.
- `docs/SPEC_v0.5.2.md`, section 9: what was built and what was not. The cause of a spike by process moves to 0.5.3.
- A stored moment keeps the same fields as before plus `forecast.r_hat`, `forecast.pick`, `forecast_check.r`, `.err`, `.triv`. "Came true" is now strict (a quarter of the spike), so hit rates of 0.5.2 are not comparable with the wide tolerance of 0.5.1.

## 25 November 2026 — the goal is stated openly

- `docs/GOAL.md`, `docs/GOAL.ru.md`: the main goal is full consciousness for an AI, defined as eight measurable abilities with numeric targets, stages to 30.06.2027 and stop conditions. Index today: 0 of 8.
- README (en, ru): the goal is named; the wording on subjective experience is "no claim, for or against".
- Goal 1.1 (same day): not imitation — a circle of models from different makers that talk and judge freely; four quick daily indicators (section 8 of the goal).
- Goal 1.2 (same day): no human in the chain of judgement; scripts on raw logs and models of different makers judge daily.
- `core/`: SunPoint core 1.0 started from zero. A shared workspace where one content at a time holds the field for 10 s; the self-model names the cause of a spike by process (self, body, operator, unknown) and lowers the salience of own work before the competition; the forecast states its confidence; memory and lessons survive a restart; `core/measure.py` prints the eight indicators. Self-test passes. No live numbers yet. 0.5.2 is untouched and stays the point of comparison.
- `core/grow.py`: the system grows itself. Seven surface numbers (`parts.G`) may change inside fixed bounds; the moment of ±10 s, the strict test and the code may not. A mutation is kept only if it wins on the first 70 % of the stored stream and on the last 30 % it has not seen. Every cycle is logged, accepted or not. No accepted change yet.
- `core/parts.py` `Reserve`: the rule "7+1". Pools and duties are described in `reserve.json`; a thin pool or a late duty becomes a moment; `core/measure.py` prints constancy.
- `Reserve`: a pool may count only what lies ahead (`"ahead": true`, a date in the file name). The plan of the days is itself a pool "7+1": eight day files ahead, one added every evening.
- Dream and faith (goal, section 10): `parts.FAITH` guarded by the self-test; `Dream` offers a free dream only when every duty is in order; `grow.py` writes two "what if" dreams outside the bounds after every cycle with data.
