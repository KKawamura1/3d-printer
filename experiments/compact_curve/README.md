# 4×2急カーブ試作 X4A

4×2の「直線32 mm＋R16の90°カーブ」を、水平／19.2 mm下り、開放／トンネル、右／左の8通りで造形する。右は西入口→南出口、左は西入口→北出口。

| A1 mini上の列 | 右曲がり（左列） | 左曲がり（右列） |
| --- | --- | --- |
| 奥、水平・開放 | X4A-01 | X4A-02 |
| 水平・トンネル | X4A-03 | X4A-04 |
| 下り・開放 | X4A-05 | X4A-06 |
| 手前、下り・トンネル | X4A-07 | X4A-08 |

スライサーでプレートの向きを変えた場合は西側面の刻印を参照。個別モデルは同じIDのフォルダにある。

既存SD01-V4／SD02-V4とSD03-V11／SD04-V10を作る`course_loft_family`を使う。4通りのBRepを作り、左曲がりは右曲がりをXZ平面で反転した後で刻印する。入口／出口の公称径25.74 mm、E31-05受け、従来の内部断面と半径の遷移を継承する。既存の水平C01/C02は2×2なので、新しい水平型の比較元は4×2の坂付き型とする。

PR91と屋根・通路のLoft、断面、下面受け、窓の切削形状、刻印処理を共有する。トンネルの外側に幅12 mm・角R0.8 mmの窓を2つの直線部位置と曲線中央に配置する。西側面には高さ5 mmの試作IDを刻む。

```sh
python -m experiments.compact_curve.export --out build/compact-curve
python -m unittest experiments.compact_curve.test -v
COURSE_PARITY_MODELS=SD01-V4,SD02-V4,SD03-V11,SD04-V10 python -m unittest tests.test_course_catalog_parity -v
```

出力はmm単位。生成時に、刻印前の下面BRepの一致、実際の出入口断面、窓の貫通、個別とプレートのSTLの水密性、BRepとの体積差、プレート内の間隔を確認する。Bambu Studioのスライス、実物の嵌合と球の自然転がりは未確認。
