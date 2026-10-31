# Working on this project

- Calibration also defaults to DUPLO: `python -m experiments.initial_calibration.design`; see experiments/initial_calibration/README.md. Legacy LEGO calibration requires `--family lego`.
- The user's actual target is DUPLO. Read docs/duplo.md. Default CLI/profile is DUPLO 2x4; keep legacy LEGO examples explicit. DUPLO is not a uniform 2x mesh scale: it has hollow studs and separate dimensional presets.
- Fit references must use the same family preset; never compare a DUPLO candidate against the 8 mm LEGO reference by accident.

- At the start of a fresh session, consult docs/new-session.md for setup as needed; do not assume an old Chromium installation, build directory, shell environment or process/session ID still exists. Do not launch the browser or smoke-test a legacy/default model as routine bootstrap when the current change does not require it. For a relevant visual check, use the **changed model's** viewer.
- Read README.md and docs/design.md first. Units: millimetres, Z up, bottom rim z=0.
- Use CadQuery BRep as the authoritative solid. Change parameters/source, regenerate, inspect the actual previews, and run geometric tests before claiming success.
- **Targeted verification only by default.** For a model-specific CAD change, run only its relevant test file(s), e.g. `python -m unittest experiments.receiver_fit.test -v`. For PR changes, use `python scripts/ci-tests.py --base <base-sha> --plan` to inspect the selected tests and then omit `--plan` to run them once. Do not use `python -m unittest discover -s tests -v` as the routine validation step.
- Generate and verify only the model(s) changed, using their dedicated module/command and output directory. `python -m brickcad build` builds the default DUPLO 2x4; `python -m brickcad all` additionally runs a calibration sweep and **must not be run by default** for unrelated features. Do not regenerate old models, nominal profiles or print archives unless the change actually affects them.
- When a shared CAD kernel, geometry/fit validator, shared profile or other dependency changes, expand tests only to genuinely affected dependents (use `scripts/ci-tests.py` for dependency selection); broad regression tests are justified for genuinely cross-cutting changes or on explicit request. If a new CAD module has no relevant test, add a targeted one rather than testing all legacy models. Report exactly which tests/models were checked, and do not describe unrun tests as passed.
- Never describe a collision-free rigid model as physically validated, or infer clutch force from overlap volume. Keep `physical_fit_validated=false` until real print results support a specifically identified profile, printer and material.
- Keep source dimension evidence, guesses, printer compensation and measured calibration distinct. Preserve failed trials and measurement metadata in `measurements/` when the user supplies them.
- Keep `profiles/nominal.json` (LEGO) and `profiles/duplo-nominal.json` (DUPLO) as synthetic references; do not silently tune it to make candidates pass. Compare both printed-on-reference and reference-on-printed.
- Keep negative controls (half-pitch misalignment, overinsertion, tight fit, broken mesh) so the harness demonstrably detects defects.
- Never send printer commands or produce machine-specific G-code without the actual machine/nozzle/material/slicer setup. STL and STEP are machine-independent outputs.
- Existing model supports rectangular bricks with at least two studs on each axis; 1-wide bricks and irregular layouts need new underside support logic and tests.
- All intermediate outputs (STEP, 3MF, ZIP, viewer, screenshots, generated reports) go in ignored `build/`. For multi-megabyte STL outputs, **push small design sources only**; generate STL through the `CAD preview and print artifacts` GitHub Action. Specify `targets=parts/play_set` for the manually triggered 8-piece plate, then download the `cad-verified-stl` Artifact. Do not stream Base64 STL through the connector or force an upload by reducing mesh accuracy. Only commit a print-ready STL beside its owner in `parts/` or `experiments/` when the user explicitly needs a repository-tracked version and a safe transfer path is available. Preserve source inputs and physical observations separately. Do not regenerate unchanged historical STLs during a layout-only refactor.

- Prefer the persistent `npm run browser:interactive` session for visual iteration: keep the browser alive, send JSON commands on stdin, open each returned screenshot, regenerate CAD and send `reload`. Use `BRICK_CHROMIUM_PACKAGE` for the bundled Linux fallback if the standard browser download fails. Do not default to CI for each edit.
- Visual verification for a model or viewer change must use that model's generated viewer only: after setting up Playwright if needed, run `npm run browser:check -- <changed-model-output> build/browser-qa` and `python scripts/review-sheet.py build/browser-qa`. Do not use legacy `build/first-print` or run other models' previews by default. If a local browser is unavailable, use the manual CAD preview workflow for the **selected model** and retrieve its screenshots.
- Open the real browser screenshots with the image inspection tool. Inspect top, underside, section, assembled, exploded and crossed views. Fix defects and repeat capture. A mocked canvas test, generated PNG from another renderer, or automated pixel check does not substitute for reviewing the actual browser output.
- Do not mark visual review complete based on a successful screenshot command. Record the input hashes, screenshot hashes, observations and remaining limitations in a review note after actually inspecting images.


- CI policy: push runs the version-aware planner (`scripts/cad_versions.py`); new/bumped `auto:true` revisions generate for **parts and experiments**. `auto:false` (including bulk plates) requires manual `targets`. Only the selected model's tests are executed; screenshots require explicit `previews=true`. Shared source changes require bumps on affected models instead of silently rebuilding unchanged revisions.


## Shared part design

- For new parts, read docs/shared-part-design.md and choose an explicit version from brickcad/standards.py with brick_from_fit(). Add a new profile ID rather than rewriting an existing profile's dimensions. Keep nominal references synthetic.
- Use the shared make_studs()/receiver() primitives. Keep body_offset_xy separate from receiver_inset_xy; do not tune new receivers through the legacy wall or coupled clearance fields.
- Preserve the existing calibration scripts/IDs as historical trials. Give new experiments a run-qualified specimen label such as E07-03 in the CAD, filenames and measurement records.
- Save resolved dimensions and source fingerprints with design_manifest(); record actual printer/slicer/placement settings and all three mating directions separately.

## Repository layout

- Read docs/repository-layout.md. Maintained designs and adjacent tests live in parts/<name>/design.py and test.py. One-off trials live in experiments/<run>/.
- parts/ and brickcad/ must never import experiments/. Adopt findings by adding explicit shared profile versions.
- Do not overwrite completed experiment inputs, specimen labels or saved STLs; create a new experiment. Exact historical reproduction uses the original Git commit.
- A layout/import/docs-only change does not require new browser screenshots or CAD regeneration when geometry, dimensions and viewer behavior are unchanged. Validate imports, path resolution, affected tests and original STL blob identity instead.

- Maintained printable parts also need an engraved design ID and revision (e.g. T01-V2). Keep the label on non-mating, non-running surfaces; use the same ID for identical copies and increment the revision when the released geometry changes. Match engraved IDs to STL names or a documented manifest.

## Remote CAD workflow (PR20+)
- Do not upload STL, STEP, viewer HTML, or PNG through the chat/GitHub connector. Commit small design/config/test changes only.
- New maintained parts and experiments opt in through adjacent `cad-build.json`, with required `version`. Bump the version whenever a CAD source/config changes. Version is the immutable geometry identity and should match the engraved part revision.
- Both parts and experiments default to `auto:true` and generate only on their own new/bumped `version`. An experiment's pinned dependency revision changing does not automatically rebuild that experiment. Set `auto:false` only when a large manual/batch build is intentional. Tests and docs do not invalidate CAD outputs.
- Dependencies must be pinned as `{"target":"parts/tunnel","version":"T01-V2"}`. When the current revision differs from the pin, generate the historical revision in an isolated checkout at a matching Git commit; never substitute today's geometry.
- A dependent can use `{deps}` in its command to reference outputs of the pinned sources. Experiments with independent parameters can omit `requires`.
- The 8-piece plate is manual-only (`targets=parts/play_set`). Cached same-version CAD output may be reused; an expired cache is re-created from versioned sources.
- `previews=true` requests screenshots. The screenshots must actually be opened and checked before claiming visual review; CAD checks are not evidence of slicing or physical fit.

## PR and CI recovery policy
- Prefer one topic per PR. Fix tests, reports and generation failures by committing to the **same branch/PR**; do not close and recreate a PR just to make CI green.
- Never force-push or rewrite an open PR's history as routine error correction. If absolutely necessary, first inspect the current branch head and the incremental planner's fallback behavior.
- For ordinary pushes, the runner compares the exact previous commit. If it is unreachable (e.g. history rewrite), the planner uses the common ancestor with `origin/main` and logs the broader selection. If there is no safe common ancestor, fail explicitly rather than silently skipping builds.
- Run small source-only checks first: `python -m unittest discover -s scripts -p test_cad_versions.py -v` and `python -m unittest discover -s scripts -p test_cad_report.py -v`. Then run only changed model tests and GitHub Actions; do not regenerate unchanged CAD.
- New model reports must provide top-level `passed: true` only after all geometry checks pass. The shared pipeline validates or supplies `mesh.passed` from the actual STL when absent. Never use a report/schema fix to hide a failing geometry or mesh test. Numeric dimensions are floating point: use tolerance-based comparisons (e.g. `assertAlmostEqual`), not strict equality.
- Before claiming completion, inspect both CAD tests and CAD artifact workflow results and confirm whether the downloadable STL artifact exists; these do not validate Bambu Studio slicing or physical fit.
