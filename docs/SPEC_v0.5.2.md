# SunPoint 0.5.2 — a forecast that learns, and a sense of own body

Status: design, written 23 November 2026 from the findings of the initial research review.
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
