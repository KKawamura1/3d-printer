# SD04-V8 — 左向きアダプタ（右SD03-V9と共通形状）

左側の走路・支持構造は独自実装しない。`parts.sharp_downhill_tunnel_right.design` で**無刻印**の形状を組み、XZ面で反転した**後**に左ID `SD04-V8` を凹刻印する（鏡文字不可）。依存元 `SD03-V9` と異なる版を読み込む場合は例外にする。

- 共通形状・仕様・検証境界：`../sharp_downhill_tunnel_right/README.md`。
- 出力：`python -m parts.sharp_downhill_tunnel_left.design --out build/sharp_downhill_tunnel_left`。
- 標準刻印：`brickcad.marking.engrave()` の既定値、DejaVu Sans Bold / 3.0mm / 凹み0.4mm。完成後の可視外壁に彫る。
- 見える入口・出口の真円断面、輪郭切断スタッド・下面支持、約1mmの真円リップ＋約4mmの屋根遷移は右側と共通。
- Issue #60 / PR #58 B条件：完全チューブのE31-05スリット終端中心Z=3.50mm、最上端Z=4.15mm、下面天井まで0.60mm余裕。補強リブなし。

**検証状態:** #58の小型試験片Bで床印刷・嵌合感は良好。**この左SD04-V8の大型パーツは未再印刷**。#55の旧SD04-V3の床面不良が現行版で解消したと断定しない。CAD検証・STL生成成功、Bambu StudioサポートOFF確認、実機床面・転がり・刻印・保持力の合格を別々に扱う。

Refs #37 #42 #50 #51 #55 #58 #59 #60.
