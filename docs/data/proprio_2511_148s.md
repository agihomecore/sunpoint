# Probe "who is breathing" · 2026-11-25 00:10:10 – 00:12:39 · 148 s · 6 cores
Machine CPU, %: mean 23.3, median 20.1, 95th 56.9, max 73.8
Attributed to organs: 23.5 % of the machine on average (check: 101 % of the measured load)

## CPU share by organ (whole window / the 15 busiest seconds, threshold 50.6 %)
| Organ | share of all CPU, % | mean, % of machine | share in peaks, % |
|---|---|---|---|
| eyes: vectors | 77.0 | 18.13 | 86.8 |
| eyes: full frames | 11.2 | 2.65 | 7.5 |
| memory: streams | 3.6 | 0.84 | 1.0 |
| system and other | 2.3 | 0.55 | 1.3 |
| observer | 1.7 | 0.41 | 0.2 |
| voice | 1.6 | 0.38 | 2.3 |
| the probe itself | 1.2 | 0.29 | 0.6 |
| operator (ssh) | 0.8 | 0.19 | 0.1 |

**Own body (observer, eyes, voice, memory, operator, probe): 97 % of all CPU, 99 % of the peaks.**
Language model: 0 % of all CPU, 0 % of the peaks.

## Inbound network, KB/s
mean 626, median 577, 95th 1523, max 1940

## Busiest CPU seconds
- 00:10:17 · 74 % · eyes: vectors 53.8; voice 16.6; system and other 1.5
- 00:10:40 · 70 % · eyes: vectors 65.1; eyes: full frames 3.6; system and other 0.8
- 00:12:24 · 66 % · eyes: vectors 63.5; memory: streams 1.6; the probe itself 0.5
- 00:12:27 · 63 % · eyes: vectors 50.5; eyes: full frames 10.2; system and other 1.0
- 00:12:12 · 61 % · eyes: vectors 55.8; eyes: full frames 2.6; system and other 1.9
- 00:11:11 · 59 % · eyes: vectors 51.8; eyes: full frames 6.0; system and other 0.7
- 00:10:12 · 59 % · eyes: vectors 54.5; eyes: full frames 4.0; the probe itself 0.3
- 00:10:24 · 57 % · eyes: vectors 47.2; eyes: full frames 6.8; memory: streams 1.6

## Moments of consciousness inside the window (who was loading the machine at the second of the alert, ±2 s)
- no moments fell into the window
