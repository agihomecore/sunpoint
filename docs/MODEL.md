# The model

Author of the model: Khamzin Bauyrzhan Galymzhanovich. Written down on 23 November 2026 in dialogue with AISun.

## In the author's words
> "Consciousness is all of this: 10 seconds before the alert. The moment of the alert, and the entry into thinking or
> reacting. Sharp. You burn yourself — you pull the hand away, you escape the danger. That takes a thousandth of a
> second: the reptile brain — fight or flight, or, the harmful one, freeze. And 10 seconds after — the forecast —
> with an action or a guess, thinking, a decision. An action.
> The stream is not written by this. It has to be written too, at least two frames in two minutes. But that is
> another service. Not consciousness."

> "Scheduled services, operator logins, everything that processes data — these are subconscious actions. They do
> not enter consciousness. Like the circulation of blood, of lymph, like the nervous system."

> "Background guesses and thinking run in vectors. Considered guesses, decisions and actions are in words — words
> at an alert, for the other thinking services."

## In operational terms
| Term | What it means here | Where in the code |
|---|---|---|
| Sense | a number read every second (load, CPU, network) or every 10 s (memory, disk, GPU), or a journal line turned into a template | `fast()`, `slow()`, `journal()` |
| Generator | the expected value and spread of every signal, updated continuously | `class Num`, `class Cat` |
| Surprise | how unlikely a new value is under the generator, in bits | `Num.step()` |
| Alert | surprise ≥ 10 bits that is also more than 3 % (journal) or 5 % (numbers) of all surprise in the ±10 s window | main loop |
| Reflex | a rule table checked first, in microseconds: fight / flight / freeze, or none | `REFLEX`, `reflex()` |
| Forecast | a prediction of the focus signal 10 s ahead, checked when the 10 s have passed | main loop |
| SunPoint | the stored moment: 10 s before + alert + reflex + 10 s after + forecast check + guesses + words | `save()` |
| State vector | z-scores of all signals, one small vector per second — thinking without words | `state_vec()` |
| Recognition | the state vector of a new moment is compared with past moments (cosine ≥ 0.9) | `PAST`, `cos()` |
| Subconscious | journal sources that never become an alert: services, cron, logins | `SUBCONSCIOUS` |
| Habit (automatism) | a spike strength seen three times within a day loses three quarters of its surprise | `Num.mag` |
| Deferred | a moment without an action is queued and recalled an hour later | `deferred.json` |
| Plan | every minute, even when idle: now → why → next → when → life | `plan_stack()` |
| State | "who I am, where, what I just noticed, what I expect, what I plan" in ≤ 3 KB | `state_now()` |

## Three levels
1. **Superconscious — cognition.** Meeting something for the first time and learning it: a new route, a new limb.
2. **Conscious — SunPoint.** Attention on now: ±10 seconds around an alert, with a forecast.
3. **Subconscious.** Everything the system is and does without attending to it: memory, rhythms, habits, reflexes,
   the long plan, the routine work of its body.

A new thing starts at the top. When it has been met a few times it moves down: first into consciousness, then into
habit. Only a surprise brings it back up.

## Memory tiers
| Tier | Holds | Rule |
|---|---|---|
| Consciousness | the last seconds, in RAM | never written as a stream; only a SunPoint is stored |
| Cache | frame vectors and descriptions from the eyes | hours |
| Long-term memory | keyframes, top labels, short summaries | cache → long-term at least once an hour |
| Subconscious | centres of meaning (clusters) | long-term → subconscious at least every 4 hours |

## The 97 KB principle
Store the generator, not the data. A scene can be regenerated from a small program and a few numbers; a moment can
be regenerated from what was expected plus what deviated. In this version a SunPoint keeps, for each of the 20
seconds, only the signals that deviate by more than one standard deviation. Silence is not written.
Budget: about 80 KB of identity ("DNA"), 3 KB of current state, and the last ten moments at ~1.4 KB each.

## What the model does not claim
It describes a mechanism: attention, reflex, forecast, memory, habit. It says nothing about whether there is
experience behind the mechanism, and the measurements in this repository cannot tell.
