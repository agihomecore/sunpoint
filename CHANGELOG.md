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
