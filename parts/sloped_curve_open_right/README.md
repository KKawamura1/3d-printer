# SC03-V5 / SC05-V1 — 緩坂×緩カーブ開放レール（左右共通）

Issue #37 No.12 / No.13、Issue #60対応。**PR #46が左右両方の唯一の実装先**。

- 右: `parts/sloped_curve_open_right/SC03-V5/brick.stl`。既存SC03-V4の右向きCADを維持。
- 左: `parts/sloped_curve_open_left/SC05-V1/brick.stl`。右の**無刻印BRep**をXZ鏡映したCADから生成（右のデフォルトは鏡映済みなので、左は共通の鏡映前形状）。
- 両方向とも半径48mm、4×4×高さ2、落差19.2mm、球径24.26mm、開放レール（高い追加壁・天井・上面スタッドなし）。
- E31-05は完全チューブだけに適用。曲線で切られた下面チューブは支持材として残す。スリット終端中心はPR #58実験Bに合わせZ=3.50mm（上端4.15mm、天井まで0.60mm）、補強リブなし。
- 刻印は**鏡映と壁合成がすべて終わってから**各IDを凹刻印。見える西側入口外壁に共通 `brickcad.marking.engrave_west()` 既定値（DejaVu Sans Bold / 文字高3.0mm / 深さ0.4mm）、Z12mm。文字まで鏡映しない。両方向に切削回帰テストを設置。
- 連続球カプセル掃引、下面支持、BRep、STEP往復、閉鎖STLはCAD/CIで確認する設計。CAD通過は自然転がりの保証ではない。

生成: `python -m parts.sloped_curve_open_right.design --out build/sc03` と `python -m parts.sloped_curve_open_left.design --out build/sc05`。

**検証ステータス:** 旧SC03-V3の成功Artifactは本変更の検証結果ではない。最新版についてCAD tests、CAD/STL Artifact、Bambu StudioサポートOFFスライス、実物床面・嵌合・刻印・左右10回転がりはそれぞれ別に確認する。プレート2の旧SC03-V3は未再構成。実機未検証。
