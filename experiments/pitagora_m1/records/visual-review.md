# Visual review — M1 / 2026-10-24

Reviewed the real Chromium screenshots in the 8-view contact sheet, and opened the ball/cutaway screenshot at full size. Browser automatic checks and this human/agent visual observation are separate records.

- Assembly: two separate 2x2 tunnels between two rails; circular mouths and 0.2 mm nominal joins align.
- Top/underside: eight hollow upper studs and the existing receiver/tube structures remain present; no apparent drawing-order defects.
- Section: floor continuity, enclosed roof and receiver separation are visible.
- Exploded: four distinct modules, drawn farther apart only for inspection. No movement/assembly path validation is implied.
- Ball envelopes: three 24.26 mm spheres at the join centres; the cutaway shows the concealed middle sphere. These are static envelopes, not moving simulations.
- Mobile: no horizontal overflow; controls and model fit the viewport.
- Existing DUPLO and legacy LEGO 10-view browser regression sheets also opened and reviewed: top, underside, section, assembly, exploded, crossed and collision-control views render consistently.

No physical print, clutch-force, genuine-rail interface, rolling or safety validation. The support bricks are absent from the assembly CAD. Rigid CAD path PASS is not a physical result.

Full-resolution PNGs and generated viewer are reproducible via scripts/pitagora-browser-check.cjs and are uploaded by the CAD CI job. The browser report intentionally retains visual_review_performed=false because that flag is automated; this note is the separate completed visual review.

## Final input SHA-256

- `viewer.html`: `23148130ecfeee5c64c5b8bc4377ca34ef0e59e58731fe62c9d578f084c90203`
- `report.json`: `1d908be43c1c24180193d24c8d2dd10669057993d27c96a1836330572b2fec08`
- `assembly.step`: `3b19143918bbbdabdf99d61e75bef89a0b9ce06c9398245e536dcf18f2619fcf`

## Inspected screenshot SHA-256

- `01-assembled.png`: `cb754e79a6df5a1d6edafaec93c580e517d343653eb8cfc835154c6ae458bdd6`
- `02-top.png`: `c8270de9c26b9dbb2a452236eb08c7624562296c47ab2b5e37cb08e6eae512fe`
- `03-underside.png`: `14e6ca2d27a818ca4b9d4124988eb8b0c1f9141d3da702a5c7426aacb5f23de3`
- `04-section.png`: `ad32c5c808618a0122b2c09b39bec847bb5b3b8979074b44dd2d8f8f7b300f16`
- `05-exploded.png`: `94b00324afe56c02b4fc88ee61d9b4d19a330c589f72cc47cfc1fac0b5f30a86`
- `06-balls.png`: `ec744c53c81dd94c635d88a6301cffa5afd8c682c0b3fbe78b8c26be4416f158`
- `07-balls-section.png`: `fa8257922052c6c691954207150509062594588f9ef598f5ce8c193fda88ca97`
- `08-mobile.png`: `2633251c5490381313242154d04144a065f3e8f3f13d55b70f57018182599168`

Contact sheet: `905ace4a1c4b3a10ae15e28e54abe42172b7eb6d26d14f83ac4b3e21cfcef175`
