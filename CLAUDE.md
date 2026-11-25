# Notes for AI collaborators working in this repository

- Read `docs/GOAL.md` first: the main goal and its eight indicators. Every change should move one of them.
- Read `docs/REVIEW_2026-11-23.md` and `docs/REVIEW_2026-11-25.md` (what is proven) and `docs/SPEC_v0.5.2.md` (what to build next) before changing code.
- Follow `CONTRIBUTING.md`: measure first, compare with a trivial baseline, shadow first, say what is not proven.
- Never add host names, addresses, stream URLs, keys or personal data. Deployment details live outside this repository.
- Keep `src/sunpoint.py` stdlib-only. Run `python3 -I src/sunpoint.py --test 120` and both tools before committing.
- English is the base language; keep `README.ru.md` and `docs/*.ru.md` in step with the English originals.
- Commits by the AI collaborator are authored as "AISun".
- Do not claim subjective experience anywhere, and do not deny it either. The project uses "consciousness" in the operational sense defined in `docs/MODEL.md`.
