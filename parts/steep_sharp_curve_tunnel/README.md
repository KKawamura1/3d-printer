# S02-V13 / S03-V7 — 急落下＋急カーブトンネル左右（PR #41）

Issue #60準拠。**左右はPR #41の共通CADで管理**し、左版の独立実装（旧PR #45）は使用しない。

- **右 S02-V13**：2×2×高さ3、西高入口Z25.55 → 南低出口Z6.35、落差19.2mm。落下室＋勾配1:4（約14°）の13mm出口坂＋3mm水平。旧33°版は不採用。
- **左 S03-V7**：右の**無刻印BRep**をXZ面で鏡映し、西高入口→北低出口へ。鏡映後に独立刻印・独立STL生成。
- **円形口**：両側ポートを円筒切削し、内外16方向のCAD回帰テストで確認。内部屋根は連続遷移。
- **標準刻印**：共通 `brickcad.marking` を使い、右の北面に `S02-V13`、左の南面に `S03-V7` を完成後に凹刻印。DejaVu Sans Bold／文字高3.0mm／深さ0.4mm。鏡文字を生成しない。CAD差分体積テストを追加。
- **嵌合・支持**：E31-05中央下面チューブ径13.2mm。4スリットは終端中心Z3.50、上端Z4.15で下面天井Z4.75に0.60mmの余裕。補強リブなし。上面スタッド4個と下面中央チューブは通路に交差せず全形が残るため、この形状には輪郭で切れる支持体はない。ビードとスリットは完全チューブにのみ適用。
- **CAD検証**：球径24.26mmのサンプル／連続掃引、円形口、勾配、閉鎖メッシュ、刻印切削、下面支持とスリット天井余裕。

```sh
python -m unittest parts.steep_sharp_curve_tunnel.test parts.steep_sharp_tunnel_left.test -v
python -m parts.steep_sharp_curve_tunnel.design --out build/s02
python -m parts.steep_sharp_tunnel_left.design --out build/s03
```

`cad-build.json`はS02-V13とS03-V7を対応付ける。最新版のGitHub Actions `cad-verified-stl`で `parts/steep_sharp_curve_tunnel/S02-V13/brick.stl` と `parts/steep_sharp_tunnel_left/S03-V7/brick.stl` を別々に確認すること。

**未検証（最新版）**：Bambu StudioサポートOFF、実印刷の床面／嵌合／左右刻印可読性、球の自然転がり10回、後続レール接続、挿抜耐久。CAD合格だけでは実機成功を示さない。PR #58の小型B試験片の床面成功や旧S02-V6の実機評価とは区別する。
