# Visual review — 2026-10-24

Actual Chromium 153 screenshots opened and reviewed: sloped-curve review sheet, full-resolution underside and assembled course; generic DUPLO regression review sheet. Automated capture passed 10 curve views (single, top, underside, section, balls perspective/top, assembled perspective/top, exploded, mobile), without page errors. Generic regression passed 10 views including assembled, exploded, crossed and collision control.

Observations: quarter-circle remains inside a square base; inlet is elevated one brick; outlet and low rail agree in height; both joints align in plan. Groove is open and descends, with rounded lips. Nine receiver tubes are open below and joined to the floor. Section shows a continuous supporting floor. Exploded view distinguishes the high approach and its nominal support. Blue balls are separate static envelopes, not an animation or dynamics result. Mobile layout stays within the viewport. Tessellated shading on the spline does not indicate the final print surface quality.

Limits: visual checks do not establish clutch force, smooth physical rolling, resistance to derailment, bridge quality, or child-use durability. Existing support/rail fit interference is disclosed in report.json. Physical fit and rolling remain unvalidated.

## Input SHA-256

- `viewer.html`: `48356e84aa4dc722f4de8544ab638cb49b65f75a71ce51d3b3cd099d2bb96950`
- `report.json`: `6f5e3cb17d1998bf614c9a94034ad38a33826c2c0e30c4d0ae558d6efbb83386`
- `brick.stl`: `c9fc4499e87c2415d782879a7b0b27b0ac74210008908f2625d4aef6cddb8408`
- `brick.step`: `578a6d30d49459b91f22772e3f66ee063ad5980f68249f54929dde98b46b40ad`
- `assembly.step`: `438d8faf9d1d6f126bac1ca1ff70e0ae947cacb560acbdaa28a93f034f0c45ba`

## Screenshot SHA-256

- `01-tunnel.png`: `8d8b5cda1623d803b579b808e36b0cd68aa5fc9ef4f19c63d94040a22e230d7f`
- `02-top.png`: `04fdb6d53a62a56ca4101c3b9a47781aa91cb73a8e1f97080ae149772499060a`
- `03-underside.png`: `28b0f9dde2d956c4922368f81baac2327b932717b9efea4d00e090cec2ccb1c4`
- `04-section.png`: `da1ba9bbd19e2a7ce26fac99cf43da257ed95ef8ad19c4be7872a881bcfa4d1f`
- `05-balls.png`: `09b8b1a717c7e6159ea9ea3f72b35f0a59a09412191972e5e9281808e334a325`
- `06-balls-top.png`: `7024b87e3832d7ab7e3c3dbd5c150e4904b24838d065dd1192cc00cbd58764e1`
- `08-course.png`: `f997354d9105160eb1773c6215715572dfdcb7853a11873bf6aaadc4379ef142`
- `09-exploded.png`: `8712c4437ea468adf574dd1322c16464eb21d9a3ddda7da80e0bdabcf47fa32d`
- `10-course-top.png`: `dcd8a322c5a43e23754d87f7259f13af7ffc24001aafe8d537a1b54fa1fa8986`
- `11-mobile.png`: `6f6a44612939412a8d7ebd7560852e20d5a77b5b87e88340b4cc1ffebfd2bea8`

## Generic regression

Browser report SHA-256: `113cffa6bb9889a528e6cecc06e278ba71589717c5358c83187467ecccfef654`. All ten images reviewed in the contact sheet; original captures remain reproducible in build/browser-qa.
