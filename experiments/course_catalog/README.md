# PR56 — Issue #37の23分類・20モデルを共通CADから生成

**本PRは「坂×カーブ×トンネル×窓」の共通レシピから幾何生成器を選び、嵌合・刻印の共通契約を全形状へ強制する。**

## 現行共通仕様と分類レシピ（2026-11-03）

- 23分類・20形状を `models[].course = {slope,curve,enclosure,windows}` で定義。形状生成器は4軸から `brickcad.course_contract.kernel_for()` が決定し、`source.family` や旧仕様プロファイルで生成器を選択できない。
- **水平×直進×開放＝`R01-V1`** は、他の19形状と同じ `course_fit`、浅いE31-05 `add_course_receiver_features`、標準 `engrave_course` を用いて独立生成。基準は [PR #67](https://github.com/KKawamura1/3d-printer/pull/67) の固定SHAで、旧 `RAIL-LEGACY` は本番カタログから除外。
- 嵌合共通契約：E27寸法プロファイルを出発点に、E31-05チューブ半径6.60mm・下面深さ4.75mm・スリット終端Z3.50mmを適用する。深い通常ブロック17.60mm/Z4.40mmの契約は別であり、本コースに持ち込まない。
- 刻印共通契約：可視壁の `ID`、高さ3.0mm、深さ0.4mm。形状ごとに適切な刻印面・座標は異なるが、サイズや深さの変更を拒否する。
- 原典BRep一致試験は19形状を既存版と比較し、R01-V1は現行E31版と比較する。旧形状と一致することはもはや合格条件ではない。
- `tests/test_course_catalog.py` は23分類と4軸・実装レシピの整合／旧仕様の拒否を、`tests/test_course_contract.py` は全生成器の共通契約の使用を検証する。`tests/test_course_straight_rail.py` はR01の実形状を検査する。

**実機での合格はまだ別途必要**。共通仕様がコードで強制されても、サポートOFFスライス・自然転がり・接合・刻印の実印刷評価が完了するわけではない。

**本PRの最新方式は旧PRの生成スクリプトを呼び出さない。** 個別PRの `parts/*/design.py` は本番の生成経路では読み込まれず、テストでの形状一致の参照元としてだけ使用する。

## 形状ファミリーと共通部品

- **断面Loft（8モデル）:** 水平／19.2mm下り、直進／R16／R48、開放／トンネル、左右反転、後刻印。入口端と内部断面の変化、切断支持を共通化（`brickcad/course_loft_family.py`）。
- **水平R16急カーブ（2モデル）:** R16 quarter-torusの走路、開放・トンネルと局所屋根（`brickcad/course_sharp_curve.py`）。
- **急落下（3モデル）:** 共通シャフト、約14°の出口坂、東／南／北（南の鏡映）と正像刻印（`brickcad/course_steep_drop.py`）。
- **水平R48トンネル（2モデル）:** 円形口→屋根遷移のカーブトンネル、無刻印形状の左右鏡映（`brickcad/course_r48_tunnel.py`）。
- **緩坂R48トンネル（2モデル）:** 高さ変化・高天井・切断上面スタッド・完全チューブと切断下面支持の区別（`brickcad/course_r48_sloped_tunnel.py`）。
- **直線坂トンネル（1モデル）:** smoothstep床・可変窓・真円口・屋根・E31（`brickcad/course_downhill.py` と `course_downhill_primitives.py`）。
- **水平直進トンネル（1モデル）:** 2×2×高さ2、円形口→屋根遷移（`brickcad/course_straight_tunnel.py`）。
- **水平直進開放レール（1モデル）:** 同じ共通嵌合・刻印契約から `R01-V1` を生成する（`brickcad/course_straight_rail.py`）。

数え方：20個の固有CADでIssue #37の23分類（開放10、トンネル13）をカバーする。GC01-V5、C01-V6、C02-V8の各1個が逆走で左右2分類を兼用する仮説。**逆方向の実物試験は未実施**。

## 生成とテスト

```bash
python scripts/course_catalog.py --mode validate
python scripts/course_catalog.py --mode plan --targets all
python scripts/course_catalog.py --mode build --targets GC01-V5
python scripts/course_catalog.py --mode build --targets 7,8
python scripts/course_catalog.py --mode build --targets all
```

GitHub Actionsの `Issue 37 course catalogue generator (23 categories)` で `targets=all` またはモデルIDを指定すれば生成できる。普通のpushでは代表GC01-V5だけ生成し、20個のSTLを毎回作らない。成果物は `build/course-catalog/models/<ID>/brick.stl`、`report.json`、`course-manifest.json`、全体の `manifest.json`。

**形状一致の検証:** `tests/test_course_catalog_parity.py` が各生成BRepと元PR/旧mainの固定SHAから再生成したBRepを比較する。刻印前・刻印後とも双方向差分体積・全体積差が各0.001mm³以下を合格条件とする。

```bash
COURSE_PARITY_MODELS=all python -m unittest tests.test_course_catalog_parity -v
COURSE_PARITY_MODELS=GC01-V5 python -m unittest tests.test_course_catalog_parity -v
```

全件比較は重いためActions `Issue37 independent CAD vs original BRep parity` を手動実行し `models=all` を指定する。**テストを実際に完走するまでは「全20形状一致済み」とは扱わない。**

生成成功はBambu Studioでのサポートなしスライス・実印刷・球の転がり・E31嵌合の成功を意味しない。旧直線レール（RAIL-LEGACY）は本番生成対象外。直線レール（R01-V1）も他の19件と同じE31・標準刻印を強制する。

## 旧方式との関係

以前の `scripts/course_catalog.py` は原典PRの`cad-build.json`を固定SHAで呼び直すだけだったため、当初の共通CADの目的を満たしていなかった。現行の全20モデルは `source.kind=configured` に変更し、**本番では元パーツの生成コードを呼ばない**。参照元のSHAはテストの基準にのみ残す。

#58/#59/#60の床・刻印・左右反転ルールを維持。ただし旧いRAIL-LEGACYは本番カタログから除外した。設計上不採用の急落下×緩カーブ2方向（#52/#53）を含まない。

## ファミリー横断の共通化（形状不変）

`brickcad/course_geometry.py` に水平/下り坂のsmoothstep補間と
円形口→屋根の遷移補間を共通化した。数値演算順序は従来と一致させるため、
expanded/factoredを明示的に分けている。
`brickcad/course_artifacts.py` はカタログの主要出力ファミリーに共通する
STL/STEP出力、float32退化三角形除去とメッシュ検証を担う。
**各ファミリーのメッシュ精度（特に下りR48の .02/.15）、
形状構築、刻印座標、E31支持の切断仕様、レシピおよび出力レポートは変更しない。**
`tests/test_course_shared_primitives.py` で演算値、メッシュ正規化と出力を回帰テストする。
フル20個のBRep一致は従来どおり全件パリティCIで別途確認する。

### 旧バージョン固定実験の境界

`experiments/course_curve_open`/`course_curve_tunnel`、
`course_drop_east`/`course_drop_south`、
`course_windows_w01` は旧 `cad-build.json` の版を固定している。
これらが直接importする `course_sharp_curve.py`、`course_steep_drop.py`、
`course_downhill.py`、`course_downhill_primitives.py` のコードは
履歴再現性のため変更しない。新版カタログの R16/急落下は
`course_configured_special.py` で出力を共通化する。
D01坂トンネルの生成・出力は引き続き旧実験と共通の
`course_downhill.py` を用い、形状変更なしの安全な共通化を優先する。
