# R01-V1：水平・直進・開放レール（E31-05更新）

Issue #37 No.01。旧部品 parts/straight_rail/design.py と model.stl は変更せず残します。
本CADは旧版の実測由来の63.8 × 31.65 × 19.13mmの外形、Z6.35mmの溝底、25.74mmの開口、端部Rと入口逃げを維持し、下面受けだけを現行仕様に更新します。

- 下面3本の完全チューブ：OD13.20mm、ビードR0.20mm（Z2.25）、4方向スリット（幅1.10mm）
- 浅い受け：深さ4.75mm、スリット端中心Z3.50mm＋R0.65、床への残肉0.60mm。補強リブ無し
- 深い通常デュプロ：従来のスリットZ4.40mmを維持。このPRでは通常ブロックを変更しない
- 開放レールなので上面スタッド、屋根、高いガード壁を設けない
- 最終形状の側面にDejaVu Sans Bold 3.0mm・深さ0.4mmでR01-V1を凹刻印
- 24.26mm球の連続通過CAD、28mm負例、旧走路との比較、STEP往復と閉鎖STLをテスト

## 生成

python -m unittest parts.straight_rail_e31.test -v
python -m parts.straight_rail_e31.design --out build/straight-rail-e31
python scripts/cad_versions.py --mode build --targets parts/straight_rail_e31

Actionsのcad-verified-stl成果物：parts/straight_rail_e31/R01-V1/brick.stl（検証レポート・プレビュー付き）。
成功を確認した後にPR #55 plate3のRAIL-LEGACYから差し替えるため、今回PR #55は編集しません。

## 現物未検証

A1 mini / PLA Basic / サポートOFFで床・スリット・刻印のスライスを確認。印刷後は旧品との接続・球10回の往復通過・純正/印刷同士の保持力と耐久を評価。CAD合格は印刷成功・嵌合保証を意味しません。
