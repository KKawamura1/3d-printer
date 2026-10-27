# Visual and export review — experiment 01

Reviewed actual Chromium 153.0.8010.0 captures after opening their images.

- `review-sheet.jpg`: single C sample, top, underside, boolean section, assembled, exploded, cross-90, negative collision control, orbit and mobile. Four hollow studs, open receiver, connected central tube and roof are visible. No cap closes the underside. Rounded upper edges remain present. Assembly is against the synthetic model, not scanned OEM geometry.
- `plate-top.png`: 16 separate 2×2 coupons in a 4×4 grid; no common floor or connecting struts.
- Plate underside capture SHA256 `083eac49a831bfff77595b6bf2a4edce20510c61b30d54f9fbde9a7ccad550c5`: all 16 receiver openings/tubes visible; no extra floor.
- `marks.png`: recessed ID and directional arrows visible above the receiver engagement zone. Numeric coordinate checks, rather than this browser projection alone, establish local-axis directions. Physical legibility at 0.4mm nozzle remains untested.

The first large-plate browser attempt exposed a pre-existing JavaScript argument-count overflow at `projected.push(...vv)`. Replaced it with a per-vertex loop in the shared viewer. Recaptured the plate top/underside with errors=[] and reran all ten sample browser checks successfully. Input and capture hashes are in browser-report.json; automated_passed=true and visual_review_performed=false in that machine report is intentional: this note records the separate human/model visual review.

Plate-top SHA256: `9adef98a585b4f10fa65670efaf4b4929a4a0e946466c36e797c70721b4537cc`.
Marks SHA256: `caea2610e87ec723c446c6f45862e89e5dba43626d861f8a81cd5d19f215ec3d`.

Validation: all 37 unit tests passed; `python -m brickcad all` passed; experiment geometry/export gates passed; serialized standard 3MF was read back and verified for bed transform, 16 occupied coupon footprints, closed consistently oriented mesh and volume. Marked body contact band is unchanged by exact BRep difference. Nominal dimensions are intentional trial values, not physically calibrated output.

Limitations: no Bambu Studio slice/import UI verification, no printer exclusion-area/brim validation, no original low-coupon toolpath analysis, no actual print, no clutch-force validation. The model-only 3MF has no Bambu settings/G-code. The 4×4 grid has no X=90 center-line coupon; treatment groups each have one sample and remain confounded with location. See the experiment guide.
