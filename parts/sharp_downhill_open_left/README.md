# SD02-V3（緩坂＋急左カーブ開放レール）

**共通実装：PR #48**。右SD01-V3（`parts/sharp_downhill_open_right/design.py`）から無刻印形状を鏡映し、左ID`SD02-V3`をそのあとで新規刻印する。固有の走路形状コードは持たない。

- 入口直線区間の外側 -Y 面、X=-16mm・Z=12mm。
- 刻印は`brickcad.marking.engrave`の標準仕様（DejaVu Sans Bold 3.0mm、深さ0.4mm）。鏡文字にしない。
- 対象球径24.26mm、落差19.2mm、E31-05下面支持、輪郭切断レール。
- `cad-build.json`はSD01-V3へのバージョン付き依存関係を記録。
- CADでの通過検査は実物の自然転がりを保証しない。スライス・印刷・嵌合は未検証。

生成：`python -m parts.sharp_downhill_open_left.design --out build/sharp_downhill_open_left`。
