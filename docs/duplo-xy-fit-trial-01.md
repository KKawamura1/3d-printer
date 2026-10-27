# XY補正2×2・PR14 ID3の下面を採用

[印刷用STL](../examples/duplo-xy-fit-trial-01/brick.stl) / [STL・STEP・HTML一式ZIP](../prints/duplo_xy_fit_trial_01.zip)

2026-10-25、ユーザーがPR #14のID3（03 C-tube）を印刷し「ぴったり」と報告したため、下面チューブ外径を13.10→13.50 mmへ更新。内法をYだけ狭める条件は採用しない。[結果記録](../measurements/2026-10-25-receiver-id03-feedback.json)と[issue #1](https://github.com/KKawamura1/3d-printer/issues/1#issuecomment-6396705976)を参照。

| 項目 | CAD値 mm |
|---|---:|
| 本体X / Y | 32.00 / 31.87 |
| 本体高さ / スタッド高さ | 19.20 / 4.50 |
| スタッドピッチ X/Y | 16.00 / 16.00 |
| スタッド外径 / 穴径 | 9.40 / 6.40 |
| 下面内法 X/Y | 25.40 / 25.40 |
| 下面チューブ外径 / 内径 | **13.50 / 9.40** |
| 側壁厚 X/Y | 3.300 / 3.235 |
| 天井厚 / 本体角R / 突起上端R / 入口面取り | 1.60 / 0.80 / 0.50 / 0.30 |

上面OD9.40/ID6.40は14片実験の良好な結果を維持。本体外寸のXY補正は[誤差モデル](duplo-dimension-error-model.md)の7片・1ジョブの外寸偏差（X平均−0.2043、Y−0.0671）からの条件付き仮説。以前の偏差が再現すれば約31.80角となる計算であり、新しい実測値ではない。ピッチ・円・Zへ一括スケール補正はしない。内壁は外側の補正に追随させない。

ID3は本体31.80角であり、この候補の外寸・壁剛性は異なる。成功した試料の結果を採用するが、更新した本体の実物嵌合は未検証。ID1/2の良否、実寸、曲げ荷重・繰返し回数は今回未報告。今回の実際の印刷設定も未添付のため、過去の設定から確認済みとみなさない。

## 印刷

mm・100%、スタッド上向き、回転0°（CAD X=プリンターX）。既知の比較設定はA1 mini、0.4 mm、PLA Basic、0.20 mm、壁2周、Classic。全4スタッドのInner wall、チューブと天井ブリッジを最終スライスで確認する。純正スタッド→この下面の着座・引抜き・X/Y曲げ、印刷同士、10回着脱後の保持と触感を比較する。3MFを残す。

## 検証と再生成

```sh
python -m brickcad.xy_trial --out build/duplo-xy-fit-trial-01 --zip prints/duplo_xy_fit_trial_01.zip
```

BRep、STL、STEP再読込、上下方向・回転・ずらし・負例・隣接を検査する。13.50 mmのチューブは名目9.40 mm突起と剛体干渉を生む。この干渉はレポートにそのまま残し、保持力の予測や無干渉とは扱わない。`passed`は形状・出力検査、`fit_geometrically_clear`は剛体干渉の有無。更新形状の`physical_fit_validated`と`slicing_validated`はfalse。
