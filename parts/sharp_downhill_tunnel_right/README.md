# SD03-V9 / SD04-V8 — 緩坂＋急カーブ・左右共通生成

Issue #37 / #60、PR #50。右カーブ（SD03）と左カーブ（SD04）を**同一の無刻印BRep**から生成し、片側をXZ平面で鏡映した**後**にそれぞれのIDを彫る。左右別の走路や支持構造は実装しない。

- **右:** `SD03-V9`、`parts/sharp_downhill_tunnel_right/design.py` の `build_part(mirror=False)`。
- **左:** `SD04-V8`、`parts/sharp_downhill_tunnel_left/design.py` の薄いラッパーから `build_part(mirror=True)` を呼ぶ。左アダプタは右の形状版 `SD03-V9` に依存し、バージョン不一致なら失敗させる。
- **刻印:** `brickcad.marking.engrave()` の既定値（DejaVu Sans Bold、文字高3.0mm、深さ0.4mm）。完成外形の外側 -Y 壁、X=-16 / Z=12へ最後に凹刻印する。左も文字を鏡映しない。切削ツールと最終形状に干渉が残らないことを回帰テストする。
- **開口:** 見える入口・出口は半径 `BALL_TRACK.radius` の真円断面。外端の円形リップ約1mm、続く屋根の滑らかな遷移約4mm。
- **嵌合:** 上面スタッドと下面チューブは輪郭で切断された支持部分を保持。E31-05のビード／4分割スリットは完全チューブに限る。
- **床面の採用候補（PR #58 B）:** スリット終端中心Z=3.50mm、端R=0.65mm、最上端Z=4.15mm。下面空洞天井Z=4.75mmまで**0.60mm**確保し、追加リブは付けない。小型試験片Bでは床印刷OK・嵌合感も良好だったが、**SD03/SD04の実印刷は未確認**。
- **検証:** 左右反転一致、独立刻印、円形開口、球経路のCADクリアランス、切断支持、スリット終端、CAD単一ソリッド、閉鎖STL、STEP往復を個別に確認する。CADの通過判定は実物の自然転がりを保証しない。

```sh
python -m parts.sharp_downhill_tunnel_right.design --out build/sharp_downhill_tunnel_right
python -m parts.sharp_downhill_tunnel_left.design --out build/sharp_downhill_tunnel_left
```

各 `cad-build.json` で別々のSTL / STEP / `report.json` を生成する。GitHub Actionsの `cad-verified-stl` は生成された**対象コミットSHA**と対応を必ず確認する。旧#55プレートは旧版（SD03-V4 / SD04-V3）を参照しており、ここでの更新がそのまま旧プレートに伝播するわけではない。

**検証状態:** #58の2×2試験片Bの結果のみ実機確認済み。SD03-V9 / SD04-V8についてはBambu StudioサポートOFF再スライス、実物の床面、次レール接続・自然転がり（各10回）、刻印可読性、純正／印刷相手別の挿抜耐久を未確認。子どもへの提供前にバリ・剥離・床崩れを確認する。

Refs #37 #42 #51 #55 #58 #59 #60.
