# S02-V10 — 急落下＋急右カーブトンネル（2×2×高さ3）

PR #36（C01-V5）の西→南の右90°方向転換と、PR #38（S01-V6）の屋根付き落下室／約14°の緩い出口坂を組み合わせた複合試作。

- **入口・出口**：西の高入口 Z25.55 mm → 南の低出口 Z6.35 mm。全体落差19.2 mm。
- **外形**：31.8×31.8×57.6 mm、スタッド含む高さ62.1 mm。
- **床**：勾配0.25（約14°）、落下室から南へ13 mm下る斜路（走路落差3.25 mm）、出口手前3 mmは水平。旧33°版を不採用。
- **円形の穴**：西入口・南出口とも既存円形のポートを保持。16方向の半径内外テストを実施。
- **嵌合**：下面E31-05・上面4スタッドは維持。
- **刻印**：北面 S02-V10、3.0 mm（PR38と同じ標準サイズ）。

完全な水平R16曲線と落下穴を2×2内に同居させられないため、下段は南向きの直線斜路による90°方向転換。S01-V6の15 mm斜路／3.75 mm落差に対し、S02-V9は13 mm／3.25 mm。

```sh
python -m parts.steep_sharp_curve_tunnel.design --out build/s02
python -m unittest parts.steep_sharp_curve_tunnel.test -v
```

`cad-build.json` は C01-V5・S01-V6を参照。STLはGitHub Actionsの `cad-verified-stl` Artifactに生成し、Gitには入れない。

**未確認**：再印刷、Bambu StudioでのサポートOFFスライス、接続時の自然転がり、実物嵌合。CADでの球掃引クリアランスは物理性能の保証ではない。


## 左右反転版 S03-V4

PR #45の急落下＋左90°は本PRの `parts/steep_sharp_tunnel_left/` で生成。
右版と共通の `build_tunnel(label=None)` から刻印前のBRepを取得し、
XZ面（Y反転）で鏡映したあと**南面に新しく `S03-V4` を3.0 mmで刻印**する。
形状生成・勾配0.25・円形口・球通過・E31-05は同じ設計を共有し、
パーツ別のSTLとCADテストをGitHub Actionsから生成する。
