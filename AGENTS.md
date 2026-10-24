# Working on this project

- Read README.md and docs/design.md first. Units: millimetres, Z up, bottom rim z=0.
- Use CadQuery BRep as the authoritative solid. Change parameters/source, regenerate, inspect the actual previews, and run geometric tests before claiming success.
- Run `python -m unittest discover -s tests -v` and `python -m brickcad all` after CAD changes. For nominal-profile changes also regenerate nominal output.
- Never describe a collision-free rigid model as physically validated, or infer clutch force from overlap volume. Keep `physical_fit_validated=false` until real print results support a specifically identified profile, printer and material.
- Keep source dimension evidence, guesses, printer compensation and measured calibration distinct. Preserve failed trials and measurement metadata in `measurements/` when the user supplies them.
- Keep `profiles/nominal.json` as the synthetic reference; do not silently tune it to make candidates pass. Compare both printed-on-reference and reference-on-printed.
- Keep negative controls (half-pitch misalignment, overinsertion, tight fit, broken mesh) so the harness demonstrably detects defects.
- Never send printer commands or produce machine-specific G-code without the actual machine/nozzle/material/slicer setup. STL and STEP are machine-independent outputs.
- Existing model supports rectangular bricks with at least two studs on each axis; 1-wide bricks and irregular layouts need new underside support logic and tests.
- Generated files go in ignored `build/`; curated reproducible examples in `examples/` may be committed. Refresh examples when source/profile changes and identify the exact profile used.

- Prefer the persistent `npm run browser:interactive` session for visual iteration: keep the browser alive, send JSON commands on stdin, open each returned screenshot, regenerate CAD and send `reload`. Use `BRICK_CHROMIUM_PACKAGE` for the bundled Linux fallback if the standard browser download fails. Do not default to CI for each edit.
- Batch visual verification is required after model or viewer changes: run `npm ci`, `npx playwright install --with-deps chromium`, `npm run browser:check -- build/first-print build/browser-qa`, and `python scripts/review-sheet.py build/browser-qa`. If a local browser is unavailable, run CI and retrieve its screenshots.
- Open the real browser screenshots with the image inspection tool. Inspect top, underside, section, assembled, exploded and crossed views. Fix defects and repeat capture. A mocked canvas test, generated PNG from another renderer, or automated pixel check does not substitute for reviewing the actual browser output.
- Do not mark visual review complete based on a successful screenshot command. Record the input hashes, screenshot hashes, observations and remaining limitations in a review note after actually inspecting images.
