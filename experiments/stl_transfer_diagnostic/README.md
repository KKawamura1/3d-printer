# Binary STL transfer diagnostic — 2026-10-31

Independent of PR #20 geometry generation and browser previews. This branch is **not for merging**: test files include a tetrahedron and copies of prior STLs, not intended as deliverables.

## GitHub connector API tests

Tests used `create_blob(base64)` followed (for 284B, 253KB and 1.04MB) by `create_tree`, `create_commit`, and `update_ref`. These are **not a local `git push`**. Results are observations from one session, not a universal GitHub size limit.

| Binary STL bytes | Blob upload | Branch commit | Notes |
|---:|---|---|---|
| 284 | pass | pass | generated tetrahedron |
| 253,484 | pass | pass | existing `experiments/nominal_duplo_2x2/model.stl`; returned SHA matched |
| 1,035,284 | pass | pass | existing `experiments/xy_fit/model.stl`; returned SHA matched |
| 2,000,084 | pass | not attempted | synthetic fixture with tetrahedra |
| 3,000,084 | pass | not attempted | synthetic fixture with tetrahedra |
| 4,000,084 | fail | not attempted | `h2 protocol error: error reading a body from connection` |
| 5,000,084 | fail | not attempted | same error |
| 9,755,684 | fail | not attempted | same error; same size as PR #20 `play-set-6.stl` |

The synthetic fixtures are for transfer testing only. No CAD generation or preview was executed as part of the upload tests.

## Download-path observation

`fetch_file(encoding=base64)` returned content for existing 253KB, 555KB, and ~1.04MB STLs, but returned empty content despite a nonempty file SHA for 1,540,784 and 2,218,684 byte STLs. **Never call create_blob on an empty content response.** A mistaken empty blob was created once during diagnosis but was not committed.

## What can be concluded

The connected GitHub API transport can upload several-MB binary STL objects, but it consistently returned an HTTP/2 protocol error for the tested 4MB and larger requests. The limit is only bracketed by 3MB success and 4MB failure under these conditions; encoding into base64 increases request size. Separately, binary download returns empty content at some sizes.

This supports a size-sensitive transport problem as a credible explanation of the repeated Work failures, but **does not prove** that the Work crash was caused by this connector or that native GitHub `git push` has the same limitation.

## Follow-up / containment

- Preserve PR #20 assets and source; do not merge this branch.
- Keep CAD generation, validation, preview, and upload as separate stages, with concise progress summaries and detailed file logs.
- Do not upload large STLs via this connector without a fallback.
- Prefer transferring small source files and generating large STLs in a controlled manual CI job, or test native Git transfer separately.
- Do not reduce mesh density merely to meet transport constraints without validating print geometry.
