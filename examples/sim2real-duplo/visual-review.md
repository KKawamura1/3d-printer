# DUPLO compact calibration visual review — 2026-10-24

Source baseline: main 7e98f38eec97c028670e89d6eb57b9e624d99555.
Actual Chromium 153.0.8010.0 screenshots opened and inspected by the agent.

- Plate: five separate 2x2 short bodies, each with four hollow studs and one underside tube. No shared base.
- Label-side orbit: tally grooves 1..5 on exterior walls.
- ID5: top, underside, CAD section, assembled, exploded, crossed, negative collision control and mobile views inspected.
- Existing DUPLO 2x4: full browser regression and contact sheet inspected.
- Browser automated checks passed for DUPLO 2x4 and ID5; plate interactive captures returned no errors.
- Eighteen unit tests passed; default CAD all/sweep, compact calibration and optional full-height calibration generation passed.
- Curated ASCII STL passed roundtrip closed-mesh, winding, volume and five-component checks.
- Compact body height 6.4 mm; full-height body remains 19.2 mm. Stud height 4.5 mm; receiver depth 4.8 mm.
- Physical clutch and print quality remain untested. Short walls may flex differently; confirm selected compensation on a regular-height brick.

## Input hashes

- brickcad/calibration.py: `9f80b3545eeed09aa94514244fe5d066e422f4b383dbe09301bcdde3fca3d89f`
- examples/sim2real-duplo/plate.stl: `f64fccac2c09def9776dc71159a50936874ded03a3358df58d7c139b52d71584`
- examples/sim2real-duplo/viewer.html: `96bdfb302d981a9f3859cf94e691bae4f29bc99996f0c4f8c8716ab1200233eb`

## Inspected screenshot hashes

- build/interactive/006-orbit.png: `3c3a5c1c2059d8802e865693e4fa830c10d9aa6a9f8004b718d1d90fd91094da`
- build/interactive/002-view.png: `da9ad0c2860a09b971a1c38228643cb95490ba759256fd03aef486d85d33a59b`
- build/sim2real-duplo/browser-qa/review-sheet.jpg: `34914a17a6fc08301d8cc6b00498a0c68db051914a6a3250666f087894fb50a7`
- build/duplo-browser-qa/review-sheet.jpg: `8fc25f74d520a1af640916d11610e17f227c2115353a3406a371d3b1d1574ad0`
