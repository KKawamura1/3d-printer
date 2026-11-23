# 4×2坂付き急カーブ試作 X4A（4種類のみ）

**水平4×2（旧X4A-01〜04）は不要のため生成しない。** 坂付き4×2だけを対象とする。経路は西入口から直線32mm＋R16の90°カーブ、入口床Z25.55mm→出口床Z6.35mm（落差19.2mm）。

| A1 miniの配置 | 右曲がり（左列） | 左曲がり（右列） |
| --- | --- | --- |
| 奥・坂付き開放 | X4A-05 | X4A-06 |
| 手前・坂付きトンネル | X4A-07 | X4A-08 |

元のIDを維持して旧STLとの取り違えを防ぐ。一括STLは `X4A_4x2_downhill_sharp_curves_4parts_A1mini.stl`、個別STLも4点だけを出す。

- **既存形状を再利用**：X4A-05/06はSD01-V4/SD02-V4、X4A-07/08はSD03-V11/SD04-V10と、窓・実験刻印を除いた走路／下面／屋根の完成BRepを一致させる。
- **嵌合・ポート**：従来のE31-05下面受け、入口・出口の公称径25.74mmを変えない。左側は右形状のXZ鏡映後に刻印する。
- **窓**：トンネルのみ外側3か所（幅12mm、角R0.8mm）。直線部2個＋カーブ中央1個。
- **刻印**：西側の短い受け壁に高さ5mmの `X4A-05` 等を刻む。PR91のはみ出し不具合を受け、全文字の工具BRep外接範囲が幅31.8mm・深さ4.75mmの実際の刻印面内に収まらなければ失敗させる。

```sh
python -m experiments.compact_curve.export --out build/compact-curve
python -m unittest experiments.compact_curve.test -v
COURSE_PARITY_MODELS=SD01-V4,SD02-V4,SD03-V11,SD04-V10 python -m unittest tests.test_course_catalog_parity -v
```

STL生成時には共通下面の刻印前BRep差分、両端の実形状、窓貫通、個別・一括STLの水密性とプレート収まりを確認する。Bambu StudioサポートOFFスライスと実機の保持力・自然転がりは別途確認が必要。
