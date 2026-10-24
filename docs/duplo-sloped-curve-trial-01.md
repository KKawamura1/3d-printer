# 4×4・90度下りカーブ 試作01

黄色い既存カーブと同じ4×4ポッチの占有サイズに収め、球が90度曲がる間に1段下る。入口・出口の位置はデュプロの16 mm格子と既存直線レールの接続条件から決める。黄色い部品の途中の曲率や内部形状の完全な複製ではない。

## 印刷データ

- [STL](../examples/duplo-sloped-curve-trial-01/brick.stl)：印刷するのはこれ1個。
- [STEP](../examples/duplo-sloped-curve-trial-01/brick.step)：編集用。
- [印刷・プレビュー用ZIP](../prints/duplo_sloped_curve_trial_01.zip)：名前付きSTL、STEP、組立STEP、自己完結viewer.html、検証JSON、本手順を収録。
- [実ブラウザで確認した画像](../examples/duplo-sloped-curve-trial-01/review-sheet.jpg)
- [検証結果](../examples/duplo-sloped-curve-trial-01/report.json)

| 項目 | 設計値・根拠 |
|---|---|
| 外形 | 63.8 × 63.8 mm。ユーザーの「4×4に収まる」を16 mm格子へ反映 |
| 全高 | 約38.33 mm、突起なし |
| 落差 | 19.2 mm、今回の試作値（デュプロ1段） |
| 走路中心半径 | 48 mm。入口・出口位置と90度の接線を満たす四分円 |
| 入口 | 西辺、床基準点 (-32, -16, 25.55) mm |
| 出口 | 北辺、床基準点 (16, 32, 6.35) mm |
| 接続口の断面 | 既存 Rail と同じ開口25.74 mm、床6.35 mm、壁上端19.13 mm（入口は+19.2 mm） |
| 球 | 約24.26 mm、既報の実測参考値 |
| 底面 | 水平な4×4受け、9本の裏チューブ |
| 受けの寸法 | 既存試作の外径13.30 mm、内径9.40 mm、壁厚3.16 mmを継承。新しい嵌合補正は未実施 |
| 丸み | 走路の縁と壁上角R0.5、底板の外周角R0.8、挿入口0.3 mm面取り |

床高は角度の進行率 t に対し `6.35 + 19.2 × (1 − 3t² + 2t³)`。両端の勾配は0、中央の最大勾配は約20.9度。半径方向のU字断面を25断面の滑らかなBRepロフトでつなぐ。走路の下は底面まで埋まった構造で、カーブ自体に高低2枚の受け面は設けない。

## 組み合わせと試し刷り

1. STLをmm単位・100%で読み込む。4×4の平らな底面をプレート側、走路を上向きに置く。スライサーで約63.8 × 63.8 × 38.33 mmになることを確認する。
2. 裏面の受け天井はブリッジになる。プレビューでブリッジ・受け穴・壁の連続性を確認する。受け穴を埋めるサポートを無条件に追加しない。G-codeや材料・ノズル固有の設定は本データに含めない。
3. カーブ底面を基準高さに固定する。入口側の直線レールは通常ブロック1段で19.2 mm持ち上げる。出口側の直線レールはカーブと同じ底面高さに置く。組立STEPとviewerの「Rail connections + support」で配置を見られる。
4. 高い西側から低い北側へ球を流し、境目の引っ掛かり・中央での壁接触・出口での飛び出しを確認する。まず入口付近から小さな勢いで試し、次に手持ちコースからの流入を確認する。
5. 接続の保持力、球が止まる位置、脱線、レール端の段差を記録する。既存直線の受けが緩いという報告は残したままで、この部品の保持力も試し刷りで確認する。

## 検証と限界

BRepの妥当性・単一ソリッド、4×4外形からのはみ出し体積0、9本の受けチューブ、両端の接続、組立部品間の無干渉、STLの閉メッシュ・体積差、STEP再読込を検査した。高い直線レールと支持ブロックの接続だけは、従来の試作プロファイルに由来する剛体干渉約1.09 mm³を別欄に明示している。これは保持力の証明ではない。

球の通路は両端の直線レールを含む49位置の静的な球で確認。傾斜による球中心の高さを考慮した検査用配置であり、連続した全経路の保証や運動シミュレーションではない。2 mm低い球、1段の高さ違い、半ピッチの横ずれを負例として検出する。出力STEPに対しても実際の入口・出口の床高と、サンプル間の球通過をテストする。

スプライン面のBRep包囲箱は保守的に膨らむため、実メッシュの外形と「63.8 mm角の外へ残るソリッド体積が0」の両方で占有サイズを確認している。検証JSONには保守的BRep包囲箱も残す。

`physical_fit_validated=false`、`physical_rolling_validated=false`。曲がりながら加速するため、転がり・摩擦・跳ね・脱線と、スライサー上の造形性は実物で確かめる。

## 再生成

```sh
python -m brickcad.sloped_curve --out build/duplo-sloped-curve-trial-01
python -m unittest discover -s tests -p test_sloped_curve.py -v
BRICK_CHROMIUM_PACKAGE="$PWD/build/browser-package/node_modules/@sparticuz/chromium/build/index.js" node scripts/sloped-curve-browser-check.cjs build/duplo-sloped-curve-trial-01 build/sloped-curve-browser
python scripts/review-sheet.py build/sloped-curve-browser
```

環境準備は[new-session.md](new-session.md)。自動CIはこの変更に依存するテストを1回だけ実行する。遠隔でCAD・画像が必要なときだけ、手動の「CAD preview (manual)」で `sloped_curve` を選ぶ。
