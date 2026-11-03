# SD01-V4 / SD02-V4 — 緩坂＋急90°カーブ開放レール（左右統合）

Issue #37。左右の形状構築は **PR #48 の `parts/sharp_downhill_open_right/design.py` に1本化**。右の無刻印BRepをXZ平面で鏡映し、左の`design.py` は薄いラッパーとして残す。生成対象とパーツIDは左右それぞれ独立。

- 右：`SD01-V4`、西入口→南出口。左：`SD02-V4`、西入口→北出口。
- 16mmピッチ、落差19.2mm、対象球径24.26mm、E31-05下面支持・切断輪郭・ポート位置は従来仕様を継承。
- **標準刻印**：`brickcad.marking.engrave`（DejaVu Sans Bold、文字高3.0mm、凹み0.4mm）。入口直線部の外側 -Y 面（X=-16mm、Z=12mm）。**形状の鏡映後に**別々のIDを刻むため鏡文字にならない。
- 左`cad-build.json` は `SD01-V4` を明示的に依存指定。左右の版を連動更新すること。
- CADテストは左右の走路連続クリアランス、支持、反射対称、刻印カッター位置・標準寸法を確認。重力による自然転がり・Bambu Studioスライス・実印刷は別途検証が必要。

生成：`python -m parts.sharp_downhill_open_right.design --out build/sharp_downhill_open_right` または `python -m parts.sharp_downhill_open_left.design --out build/sharp_downhill_open_left`。
Actionsの`cad-verified-stl`が両方のSTL/STEP/検証レポートを保存する。


## SD01-V4（PR58床面改善）

下面E31-05のスリット終端中心を4.40→3.50mm、上端を4.15mmへ短縮。下面空洞の天井Z4.75mmに対して0.60mmの余裕を確保し、補強リブは追加しない。完全チューブにのみスリットとビードを適用し、輪郭で切れたチューブは支持部として残す。右SD01-V4と鏡映した左SD02-V4の双方に同じ仕様を適用する。

#58の小型B試験片では床面合格・嵌合感に違和感なし。一方、この大型SD01/SD02-V4の実印刷・Bambu StudioサポートOFFスライス・保持耐久・自然転がりは未検証である。

### #60 の確認と生成実績（2026-11-03）

- 標準刻印は左右とも鏡映後に彫刻し、切削面をCADテストで検証する。**過去に印刷したSD01-V1の刻印NGと、V4の実機判定を混同しない**。
- CAD tests: [V4成功 run 41564378928](https://github.com/KKawamura1/3d-printer/actions/runs/41564378928)。
- STL/STEP/report.json: [V4左右の生成成功 run 41564369955](https://github.com/KKawamura1/3d-printer/actions/runs/41564369955)（artifact `cad-verified-stl`, ID `13198499659`）。実行時SHA `d1452c21c1095fb91d73c62aab032f0db5a427ea`。以後のテスト・README更新は別途CIで確認する。
- チェック対象はCADモデルの閉鎖メッシュ・左右の鏡映一致・切断支持・E31スリット床側の残肉。実印刷結果は未報告。
