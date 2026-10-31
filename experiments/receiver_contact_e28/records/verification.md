# E28-V1 STL/preview verification — 2026-10-31

- PR: https://github.com/KKawamura1/3d-printer/pull/23
- Remote generation run: https://github.com/KKawamura1/3d-printer/actions/runs/41163420776
- Artifact: `cad-verified-stl` (id `13027853971`, expires 2026-11-14 UTC)
- Built from commit: `42728e705eff22982fdc6626aa67b16b60895e24` (temporary verification branch based on E28-V1 geometry at `734734f47673c554f01026eba042e6bbbb3162be`; temporary workflow file alone was added)
- Version: `E28-V1`
- CAD input fingerprint on verification commit: `53c0bed7fa8b60b571845fc3096f032ad2aaf765a26e91d72595f6a0a7624c73`. PR now has `auto:true` and merged newer generation scripts; **geometry source and version did not change**. Fingerprint changes due to auto-scheduling metadata do not mean the fit model changed.

## Automated evidence

- Targeted `experiments.receiver_contact_e28.test`: 4 tests passed. Run's stage exit code 0.
- All **5 STLs** generated and verified: E28-01/02/03/04 and E28-plate; STEP roundtrip and mesh report `passed=true` for all 4 coupons.
- Bed plate bounds: **73.80 × 73.80 × 23.70 mm**; **4 disconnected** parts; 94,492 triangles.
- Current `CAD tests` after syncing PR with main also passed: https://github.com/KKawamura1/3d-printer/actions/runs/41163566976
- Artifact manifest: `physical_fit_validated=false`, `slicing_validated=false`. No Bambu Studio slice or physical fit test was run.

| File | STL SHA-256 | PNG preview SHA-256 |
| --- | --- | --- |
| E28-01/brick | `6549337abc06b8c7f47e196575d4f6761f01b618d0eb34022e3fcb9e5313efe8` | `447125fee82c98c620f83b253f1b81ea854c2c06ce08006b0b8543e90bb272aa` |
| E28-02/brick | `0affb614b82c313ae4e28320cfabdd3bbc6ebb3ce989731a5364ef49b4d67a7c` | `842a90851498dc0d4560ed7ee1a77c8a53b149a6fa012baefed29772d6ef943f` |
| E28-03/brick | `69d004e13b8ff21937731ee40a15e757856825d58ac241985724e3db2ecb0265` | `2ba32107dcea88fc66e86e81be5970f81ba8b2ced7115eefb1a822ffc33aa9a1` |
| E28-04/brick | `87547c940eb5f241f7887f8ff94fdb31b994b1f53371d3c74b4f8ebbffb10ac8` | `ae6f3a036e3fe887f241116855b501198707f6758b37a4b1b4bf03d32f71196b` |
| E28-plate | `2b354284429bf1cbb429df58b46948a2ca88f70df532d57936206791c13a98fd` | `5ba2c7c2a00c48f37306b60d6429f3d9a70714512555a35d8a9de81f2015c21c` |

## Visual inspection (actual STL, independently rendered)

1. Opened the E28-plate and E28-01 four-view Matplotlib snapshots. **Large triangular areas appeared missing or darker** on exterior walls, so automated preview alone was not accepted as geometry evidence.
2. Loaded the same binary STL in an independent local **VTK z-buffer renderer** and opened isometric, underside, top and front images. All four specimens are separated, have four hollow studs on top, one central underside tube each, full sidewalls with inset labels, no visible triangular cuts, and no gross positioning/orientation errors.
3. Parsed the real STL meshes independently using `trimesh`: each coupon is **one watertight, winding-consistent mesh**, while the plate contains exactly **four watertight separated components**.
4. Per-coupon STL volumes (mm³): E28-01 ≈9968.96; E28-02 ≈9968.84 (label difference), E28-03 ≈9789.26 (wider inner cavity), E28-04 ≈9894.85 (smaller tube). The signs of the volume changes match the intended receiver relief.
5. The triangular gaps are therefore **snapshot rendering artifacts**, not an observed STL defect. Follow-up rendering issue: https://github.com/KKawamura1/3d-printer/issues/25.

## Verdict

**CAD/mesh and independently visualized geometry: ready for slicer validation.** The paired receiver dimensions are intentionally experimental and should **not** be promoted to the shared fit profile without the three-direction printed-fit comparison. Do not claim the model is slice-ready or child-safe solely from these checks.
