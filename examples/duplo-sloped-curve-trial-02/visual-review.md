# 試作02 目視確認 — 2026-10-25

実Chromium 153.0.8010.0の13視点をreview-sheet.jpgで確認し、03-underside.pngも原寸で開いた。切断されたC字チューブ端と側壁端に丸みがある。底面の縁は全周が丸く、完全なチューブ3本と部分チューブが残る。上面・断面・球・レール接続・組立・分解・4×4への着座・スマホ表示に欠落や予期しない床の復活は見られない。全47テストとpython -m brickcad allが成功。

STLは193,222三角形、非多様体辺0、向き不整合0、退化三角形0。STEP再読込も成功。旧版との差分でz=0.50 mmより上の名目突起接触域と走路の変化体積はいずれも0 mm³。触感と保持力は新しい印刷で確認が必要。

R0.80の縦フィレットはBRep検査を通ってもSTLに欠陥が出たため採用せず、STLと体積の検査を通るR0.70を選んだ。底の縁はR0.50。検査閾値は緩めていない。

## 確認入力のSHA-256

- `viewer.html`: `293bec4e00f65069fb6ad24e1c3333669d32ea55a74d647fde94d0a4ab4544a5`
- `report.json`: `780a223480dce9e5adae3eca312ac2afe1b28c592d27cc2930157ccd0f18e32e`
- `brick.stl`: `dcf4849d457d9739be530e561de58cf456f2d9e185828b1e0fd188a682399e0f`
- `brick.step`: `0eabe552d77f3c5aa3924bc71dac03e45b3014f3784c9b9903291507d3be119b`
- `assembly.step`: `22e21e33e436422d9d5c901ae7a7a1c696109889e05fd32c8e0a5a41e2d43c30`

## 確認画像のSHA-256

- `01-tunnel.png`: `b17edb8b93c71de44bd9b5df55f9ab34809002cfd9a1599c9623705affb08c56`
- `02-top.png`: `3b4dfe54cf4215e8c4fd0b8b418be383aed44d70e7e4120e8763b7a7c9bb666b`
- `03-underside.png`: `f4992f8b2efcd47691a729ce9f4cfb0e0f65cd218a1aa339541ddbafd188b5da`
- `04-section.png`: `64490a8cce49f12483f060251fc3fbce56ffddb68469321dd8eda1d8e8d0aa5d`
- `05-balls.png`: `aae677e56396e58fa657ff370a524c1c792cfb42a6fa67008020f3f451594675`
- `06-balls-top.png`: `5dea070dcdd8de897122a133f3c1153da69d97b19e87ab71d40aa5af817999ea`
- `08-course.png`: `b8acc7fceb699ba1c5b8f784a91dc74f537283ed854bb95e0cdb1563a79cafb6`
- `09-exploded.png`: `0ed2c9b6282dec0bcd2d54561e43d614509860571cafdc96af772eb4f496eb2b`
- `10-course-top.png`: `cb205af6d642d5b0d3c55f74a612e76efe2da21271470e9e89ef390c0ccfa1db`
- `12-receiver.png`: `2c2587d84d4637545f4324bcf2ce3a16087bdd7687d1dc91c59cfca6f47fc3f0`
- `13-receiver-exploded.png`: `086eaa1b7f53037fa32117514019517cfca4fe68bb6e74ddc45e516c1703c9fc`
- `14-receiver-top.png`: `a777b7d7c0606d72d832424910866e03d349b1184abd75e43a747f172d1dd3cc`
- `11-mobile.png`: `23173e0847d47198c49b6955e8146622b6af5dfbbfff98b9f208158c6bff6fe1`
