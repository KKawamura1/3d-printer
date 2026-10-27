# Sim2Real visual review — 2026-10-24

Actual Chromium 153.0.8010.0 screenshots opened and inspected by the agent.

- Full plate: five separate 2x2 bodies; four studs and one underside tube each; no shared raft.
- Label-side orbit: tally grooves 1..5 present on exterior walls; mating faces untouched.
- ID5 coupon: top, underside, BRep section, assembled, exploded, crossed, negative collision control and mobile reviewed.
- Existing 2x4: same full browser regression and contact sheet reviewed.
- Browser automated checks passed for existing 2x4 and ID5. Plate captured interactively without browser errors.
- Nine unit tests passed; CAD all/sweep and calibration generation passed.
- ASCII STL roundtrip passed closed-mesh, winding, volume and five-component checks.
- physical_fit_validated=false. Actual print results and slicer preview remain pending.

## Input hashes

- brickcad/calibration.py: `bf00d2bd185e9582dcda5112d06713c87e45b9eee71906c4029ba314cc7b5788`
- examples/sim2real/plate.stl: `3e65489d74812fa47d05a5075c64761ea21acb64f30814ade11582c8863de73b`
- examples/sim2real/viewer.html: `795fded333d73fc70afc959ad2b93233e0b93742ef44d856b86d98fae38792cf`

## Screenshots inspected

- build/interactive/001-capture.png: `73f79584b9808efeaf96ef148e0faaab840749e86224b81a853f15aca78c1cd6`
- build/interactive/002-view.png: `73cd90ccb28626f67302deaf8aadc0f198e502c75618dc7b76408f753fe1f2e2`
- build/interactive/006-orbit.png: `59a5eb9440ae3f4b059d4b48b1244059d6cb730f87279e006085dae294d8c402`
- build/sim2real/browser-qa/review-sheet.jpg: `597c9f7d47287046b36fc371ed91d75315414b0a6d2bccafcb148fa21233a92f`
- build/browser-qa/review-sheet.jpg: `2da1a1253c7613022527c0459d177575d0cb8f52d22360200d9eed98aece8470`
