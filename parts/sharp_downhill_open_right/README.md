# SD01-V3 / SD02-V3 — 緩坂＋急90°カーブ開放レール（左右統合）

Issue #37。左右の形状構築は **PR #48 の `parts/sharp_downhill_open_right/design.py` に1本化**。右の無刻印BRepをXZ平面で鏡映し、左の`design.py` は薄いラッパーとして残す。生成対象とパーツIDは左右それぞれ独立。

- 右：`SD01-V3`、西入口→南出口。左：`SD02-V3`、西入口→北出口。
- 16mmピッチ、落差19.2mm、対象球径24.26mm、E31-05下面支持・切断輪郭・ポート位置は従来仕様を継承。
- **標準刻印**：`brickcad.marking.engrave`（DejaVu Sans Bold、文字高3.0mm、凹み0.4mm）。入口直線部の外側 -Y 面（X=-16mm、Z=12mm）。**形状の鏡映後に**別々のIDを刻むため鏡文字にならない。
- 左`cad-build.json` は `SD01-V3` を明示的に依存指定。左右の版を連動更新すること。
- CADテストは左右の走路連続クリアランス、支持、反射対称、刻印カッター位置・標準寸法を確認。重力による自然転がり・Bambu Studioスライス・実印刷は別途検証が必要。

生成：`python -m parts.sharp_downhill_open_right.design --out build/sharp_downhill_open_right` または `python -m parts.sharp_downhill_open_left.design --out build/sharp_downhill_open_left`。
Actionsの`cad-verified-stl`が両方のSTL/STEP/検証レポートを保存する。


## SD01-V3（PR58床面改善）

下面E31-05のスリット終端中心を4.40→3.50mm、上端を4.15mmへ短縮。補強リブなし。PR58 B試験片は床面合格・嵌合感に違和感なし。SD01-V3のスライス・印刷・保持力は未検証。
