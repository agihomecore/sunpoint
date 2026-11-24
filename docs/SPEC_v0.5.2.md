# SunPoint 0.5.2 — a forecast that learns, and a sense of own body

Status: sections 1 and 3 and the schedule part of sections 7–8 are built in `src/sunpoint.py` 0.5.2 (25 November 2026). Section 2 — the cause of a spike by process — is not built and moves to 0.5.3. Nothing here has live numbers yet.
Written 23 November 2026 from the findings of the initial research review.
Goal: close the two gaps of 0.5.1 — the forecast does not beat a trivial one, and consciousness mostly notices itself.

## 1. The forecast learns
**Now.** `pred = expected + 0.5 · (spike − expected)` for every signal. Measured: signals differ
(`r` ≈ 0.1–0.3 for CPU, network and GPU load; ≈ 1.1 for the load average; 1.0 for step signals such as GPU memory).

**Change.**
- Keep, per signal, the last 60 observed values of `r = (actual − expected) / (spike − expected)`.
- `r̂` = their median when there are at least 3; otherwise the median over all signals when there are at least 5;
  otherwise 0.5. Clip `r̂` to [−0.5, 2].
- `pred = expected + r̂ · (spike − expected)`, where `expected` is the value **before** the spike updated it.
- At the check, score three forecasts in units of surprise: model `|r − r̂|`, Mean `|r|`, Persistence `|r − 1|`.
- "Came true" becomes strict: model error ≤ 0.25.
- **Skill** = 1 − Σ model error / min(Σ Mean error, Σ Persistence error). It goes into the heartbeat and the state.
- The subconscious learns from everything: every candidate alert gets a forecast and a check, whether or not it
  becomes a SunPoint. This gives hundreds of samples per day instead of dozens.
- `r` histories are saved to `forecast_r.json` and bootstrapped from the stored moments on first start.

**Accept when:** skill > 0 on at least 200 checks, with the two trivial forecasts logged next to it.

## 2. Efference copy: "who did this?"
A brain predicts the sensory consequences of its own actions and cancels them. SunPoint will do the same before a
moment enters consciousness. The decision is taken at the end of the 10 s after the alert — that window is for thinking.
The reflex stays first and unconditional.

**Organs.** Every process belongs to an organ by its command line; a process without a rule inherits the organ of
its parent (as in `tools/proprio_probe.py`): observer, eyes, voice, memory, language model, operator, schedule,
"system and other", kernel.

**Evidence, by kind of signal**
| Signal | Evidence | How |
|---|---|---|
| CPU, load average | CPU time by organ in the second of the alert (for load: the last 15 s) | `/proc/<pid>/stat` every second; children that lived < 1 s are attributed to the parent |
| GPU load, memory, temperature | GPU memory by organ and its change; per-process GPU load sampled right after the alert | `nvidia-smi --query-compute-apps`, `nvidia-smi pmon -c 1` |
| Network | bytes by organ since the previous snapshot | `ss -tinp` every 10 s and at the alert; sockets with an invisible owner count as "foreign" |
| Operator present | operator organ active in the last 15 s, or a login line in the journal in the last 2 minutes | — |

**Each organ has its own generator** (expected CPU share, GPU memory, network rate) with the same habit memory as
the signals. So an organ can itself be habitual or unusual.

**Decision**
1. Reflex fired → conscious, always.
2. Take the organs whose activity exceeds their own expectation. Split the excess into *calm* (an own organ, the
   operator, the schedule or the language model, at a habitual strength) and *odd* (an unknown organ, or a known
   one at an unusual strength).
3. *Odd* excess ≥ 30 % of the spike → **conscious**, with the cause ("the eyes work unusually hard", "not one of ours").
4. Otherwise *calm* excess ≥ 30 % of the spike → **subconscious**, written to `subconscious.jsonl` with its cause.
5. Otherwise the cause is unknown → **conscious**.

The first few times an organ does something, its strength is unusual, so the moment is conscious. After three
repetitions within a day it becomes a habit. This is the path "new → conscious → automatism" of the model.

**Accept when:** ≤ 10 conscious moments per hour on the reference server, and a reviewer who sees only the log
judges more than half of them worth attention.

## 3. The generator survives a restart
Expectations, spreads, habit memory (as counts per strength band, not as a list) and `r` histories are saved every
minute and on stop to `generator.json` (a few KB), and loaded on start if younger than 6 hours. Warm-up drops from
5 minutes to 30 seconds.

## 4. Words
A moment names its cause and its forecast error:

> Noticed: cpu_pct = 79.2 (expected 13.2). No reflex needed (9.5 µs) — thinking. Cause: operator — unusually strong.
> Forecast for 10 s: 30.4 → got 28.1 — came true (error 0.03; trivial forecast: 0.23).

## 5. Rollout
1. Unit run with simulated time: an unexplained spike → SunPoint; a spike explained by a habitual organ → subconscious.
2. Shadow run next to 0.5.1 on the same server: separate data directory, no event stream, no voice.
3. Compare on the same hours: conscious moments per hour, causes, skill.
4. Switch the service; keep the previous file; carry the learned `generator.json` and `forecast_r.json` over.
5. Repeat `tools/baseline_check.py` and `tools/proprio_probe.py`; write the numbers into the next review.

## 6. Open design questions
- Is the language model an own organ or a messenger of the outside world? A request to it comes from somewhere.
  First version: an own organ; its first activations are conscious until they become a habit.
- Network attribution misses UDP and sockets of other users. Is the "foreign sockets + operator present" rule enough?
- The 30 % threshold and the 15 s window are first guesses. They need a measurement, not an opinion.

## 7. Input from the one-hour probe (23 November, 14:30)
Measured after this design was written; see the addendum of the review. It changes priorities, not the design.

- **GPU and network evidence come first, not later.** 14 of 19 alerts in the hour were on GPU, network and load
  signals. CPU evidence alone names the cause of 5 moments.
- **Evidence must come from the organ that owns the signal.** The rule "the organ with the largest excess over its
  own mean" named the eyes for 16 of 19 moments: the eyes were above their mean in every alert second. Compare the
  excess with the spike in the same unit — GPU with GPU, bytes with bytes.
- **One cause, one moment.** A request to the language model raises a GPU alert and, about 10 s later, a CPU alert.
  An alert whose cause matches a moment opened in the last 15 s updates that moment instead of opening a new one.
- **Announce, do not only detect.** The hourly consolidation raised a network alert in the very second it started.
  The body knows its own schedule. A scheduled organ writes one line before it starts ("what, when, how long"), and
  an alert that matches an announcement goes to the subconscious. This is the efference copy in the literal sense:
  a copy of the command, not a guess after the fact.
- **Log who calls the language model.** All 7 long requests in the hour came from programs on the same machine.
  The caller's organ decides whether the load is the body's own thinking or a message from outside.
- **Tool.** Fix or remove the "seconds near a frame capture" counter of `tools/proprio_probe.py`; add per-second
  raw output so that a rule can be tested against random seconds.

## 8. Input from two days of work (25 November)
Measured on 254 checked forecasts; see `docs/REVIEW_2026-11-25.md`. It sharpens the acceptance conditions.

- **The rule of section 1 passes its condition in a replay.** Replayed over the stored moments in time order, the
  per-signal median gives skill +0.34 against the fixed trivial forecasts (error 0.47 against 0.72). A replay is not
  a live run: the condition still has to hold in the running observer.
- **A tougher trivial forecast is logged and is the one that counts.** "For each signal: Mean or Persistence,
  whichever had the smaller total error so far." Against it the learned rule leads by 0.06. New acceptance
  condition for the forecast: **skill > 0 against the tougher trivial forecast on at least 200 live checks.**
- **GPU load needs the cause, not a coefficient.** It is 39 % of the moments and has three outcomes of almost equal
  frequency (returns, stays, in between). Per-process GPU evidence (section 2) is a condition for forecasting it,
  not only for attributing it.
- **Scheduled work first.** At least 43 % of the moments repeat by the clock: the same signal at the same minute in
  8 to 32 different hours. The announcement of scheduled work (section 7) and a habit by time of day remove them.
  New acceptance condition for attention: **no conscious moment that matches an announced job.**
- **The rate alone is not a measure.** 0.5.1 already gives about 7 moments per hour — below the limit of 10 — after
  its habit memory warmed up, and half of them are the schedule. The condition of section 2 stands only together
  with the judgement of a reviewer who did not write the code.
- **Tool.** `tools/baseline_check.py` now prints the replay, the tougher trivial forecast, medians, a block
  bootstrap and the clock slots; `BRIEF=1` leaves out the list of moments.

## 9. What 0.5.2 does, as built (25 November)
- **Forecast.** `r_hat(k)`: the median of the last 60 `r` of the signal when it has 3; else the median over all signals when there are 5; else 0.5; clipped to [−0.5, 2]. "Came true" is strict: error ≤ 0.25 of the spike. Every check scores the model, Mean, Persistence and the tougher trivial forecast (per signal, the better of the two so far, chosen before the check). `skill` (against the tougher one) and `skill_fixed` are in the heartbeat. A moment says its error: "came true (error 0.05; trivial forecast 0.25)".
- **The body's clock.** A numeric spike of the same signal at the same minute of the hour (±1), seen in 3 or more other hours of the last 48, and not stronger than twice the strongest of them, goes to `subconscious.jsonl` with the cause. A reflex always stays conscious. The spike still gets a forecast and a check, so the forecast learns from it.
- **Announcements.** A line `{"t": unix time, "what": "...", "for_s": 120}` in `announce.jsonl` (or `$SUNPOINT_ANNOUNCE`) sends numeric spikes of that time to the subconscious. `src/consolidate.py` writes one when `$SUNPOINT_ANNOUNCE` is set.
- **Generator.** `generator.json`: expectations, spreads, habit strengths as counts per band, journal habits, `r` histories, clock slots, the last 500 state vectors. Written every minute and on stop. Expectations are restored when the file is younger than 6 hours (warm-up 30 s); what was learned is restored at any age. On a first start the learned memory is rebuilt from stored moments; `$SUNPOINT_BOOTSTRAP` names other data directories to learn from.
- **Checks.** `python3 -I src/sunpoint.py --selftest`.
- **Known gaps.** The clock habit can hide a real event that happens to fall on a habitual minute with a habitual strength. An announcement hides every numeric spike in its time, whatever the signal. Both are logged in `subconscious.jsonl` with their cause, so they can be counted and judged.
