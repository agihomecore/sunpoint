# Contributing

Five rules. They come from mistakes we made on the first day.

1. **Measure before you write.** A claim without a script that reproduces it is a guess. Mark it as a guess.
2. **Compare with something trivial.** A forecast, a filter or a detector must beat the simplest alternative.
3. **Shadow first.** A new version runs next to the old one on the same events before it replaces it.
4. **No secrets, no addresses, no people.** No keys, tokens, host names or stream addresses in code, data or text.
   Nobody is identified by the eyes.
5. **Say what is not proven.** Every review has an "honest border" section.

Practical notes
- The observer is stdlib-only Python. Please keep it so.
- English is the base language of code and documents. Translations live next to the original (`*.ru.md`).
- `python3 -I src/sunpoint.py --test 120` must run clean before a pull request.
- Raw outputs of measurements go to `docs/data/` together with the command that produced them.
