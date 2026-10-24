# Visual review — 2026-10-24, corner floors removed

Actual Chromium 153 screenshots opened and reviewed: complete 13-view curve review sheet, full-resolution top, underside, 4x4 seating and exploded 4x4 insertion. Generic DUPLO regression sheet reviewed (10 views, including assembly, exploded, crossed and collision control). Automated capture has no page errors and passed all 13 curve views.

Observations: both unused square corner platforms have gone; plan view is a quarter-annular rail. The underside retains only the part of the receiver below the rail, including clipped tube sectors joined to its roof. It is one connected BRep solid. The seated view shows lower studs exposed in the removed corners instead of a floor platform. The exploded view exposes the receiver and confirms the intended common 16 mm grid. Cross section retains continuous floor under the running groove. Approach remains one brick higher than exit. Ball envelopes remain clear at sampled static placements. Mobile fits the viewport.

Geometric receiver audit supplements images: all 16 nominal studs checked individually; 5 insertion heights; floor/wall/roof blocking overlap is 0 mm³. Roof clearance is 0.25 mm. The original 0.03629 mm radial tube interference remains and gives 2.27812 mm³ total seated overlap on nominal 9.40 mm studs. This is not a completely collision-free rigid fit. The 9.32 mm measured-diameter sensitivity case has 0 overlap, but measured dimensions and physical retention are uncertain. Half-pitch shift and overinsertion controls detect obstruction.

Limits: no physical fit, clutch-force, rolling/friction, derailment or bridge-quality validation. Floor removal changes receiver stiffness; old straight-rail fit is not validation of this irregular receiver. Newly exposed cut receiver edges require real-print burr/feel inspection.

Tests: existing 35 passed in full discovery. One of the 5 affected tests initially rejected a 0.00513 mm rounded/clipped STL bounds difference against an unrealistically exact target; corrected the mesh bounds assertion to 0.02 mm in line with 0.01 mm tessellation. All 5 affected tests then passed. Exact BRep outside-envelope volume check remains unchanged and passed. See tests.log for both runs. python -m brickcad all also completed.

## Input SHA-256

- `viewer.html`: `be759dcf670e4457b23628b422e8006a4c21d3ac9d7e5228d6686f5a8ffa4194`
- `report.json`: `4d47156132e6235abb26c98a59a786cd5b5431777b9ed1e171e18422f228f63f`
- `brick.stl`: `4cb0cebea6ab1bde8a6ac1fd96f3f16d9431b4aa32818fce66e609de55726ded`
- `brick.step`: `fb87c38ad6ba039b4e60b80fe36621e4be7bdf7a3b31c4d7c1ca40386c7c084f`
- `assembly.step`: `82aecc21d48db61612c90781702b43693918de9104c8d84b94f8114991b89f43`

## Screenshot SHA-256

- `01-tunnel.png`: `0e88f62d1743678b47a781e66210de9b569cdab7d300717dcb06690d5f710b59`
- `02-top.png`: `159414ffe0a6a206cff9cb69760264d450aff468618f6a92a4feb2bc4d360dcf`
- `03-underside.png`: `aadbd22e15f8d4e72f0d73c28440001627cb8b9a174ddc3366b669cca3e95271`
- `04-section.png`: `f26394f5a2bd8d8a469f7803ae4804b99f53e536fade3a6e2f035902f2c8194f`
- `05-balls.png`: `c6f5f1ee549a9ce6ea9a51d30d9aa517da15d8e68c50d2b04ea9aa00935fe129`
- `06-balls-top.png`: `241484504f8fa4168f043ebcefa6e3405ee15b1e9595f6f8705141b57ddfae4b`
- `08-course.png`: `0446dfeade4a6f516d8c908557ef60315626c80b4636ea84c99bcba43c8d4111`
- `09-exploded.png`: `d101fc17887b41284a068092cdf3dd9f1635d1ceaac9bd231c927ec08269041b`
- `10-course-top.png`: `0c31b53866cd6c18180032ebac901cde383231b4900a9b53ae7df80c820adf2b`
- `12-receiver.png`: `8c442e89d7e1068c4b49347385aac76be4600219c184dc461b6b72e990ef1aa0`
- `13-receiver-exploded.png`: `52b42fb04969f932482c71fd16d7e33496127a76aa7f41af725f40aed9388180`
- `14-receiver-top.png`: `1f536f6e5e0d421b52734ab4b5e68512c064ecdb2e39c2d4a6b8756e419520c1`
- `11-mobile.png`: `256479a19cd74313380ebc9be4d5dd9c304d42de621d50fb1ab462ca17c74aa4`

## Generic regression report SHA-256

`e480cd6371013f35f225d863308639c906aceeb46f4d2068a1b681c89b8be789`
