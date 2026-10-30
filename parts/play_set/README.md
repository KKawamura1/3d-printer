# 版付きコース8個セット

**[8個まとめた印刷用STL](play-set-8.stl)**。A1 miniの180mm角ベッドへmm・100%・中央配置で読み込む。約140×170mm、独立8個、ブリムは最大2mm。スライスは手元で行う。

| 側面の刻印 | 個数 | 内容 | 個別STL |
|---|---:|---|---|
| S01-V2 | 1 | 坂カーブ・完全な円筒3本、開放下面 | [model.stl](../sloped_curve/model.stl) |
| S02-V2 | 1 | 坂カーブ・円筒3本＋閉じたD形4本＋中実支柱1本 | [S02-V2.stl](../../experiments/pr20_comparison/S02-V2.stl) |
| E01-V2 | 2 | 90度トンネル・現行涙滴天井 | [model.stl](../elbow/model.stl) |
| T01-V2 | 1 | 直線トンネル・現行涙滴天井（比較基準） | [model.stl](../tunnel/model.stl) |
| T02-V1 | 1 | 直線トンネル・全長真円 | [T02-V1.stl](../../experiments/pr20_comparison/T02-V1.stl) |
| T03-V1 | 1 | 丸入口1mm＋遷移2mm | [T03-V1.stl](../../experiments/pr20_comparison/T03-V1.stl) |
| T04-V1 | 1 | 丸入口1mm＋遷移4mm | [T04-V1.stl](../../experiments/pr20_comparison/T04-V1.stl) |

IDは形状番号＋版。複製同士は同じ刻印で、設計を変更すると版を上げる。深さ0.4mm、文字高3mmの凹刻印で、上下の嵌合面・球の走路を避けた側面に置く。配置記録のE01-V2-A/Bは左右の複製を示し、刻印は共にE01-V2。

共通嵌合は `duplo-e27-play-v1`：上面OD9.40/穴6.40mm、下面チューブOD13.50/穴9.40mm、内法25.40mm相当、16mm格子。E27の結果を新形状へ移した候補で、保持力・印刷再現性は未確認。通常ブロックと通常レールは含めない。

S02-V2は隅の床を増やさず、切れた円筒を切断面の壁で閉じる。小さい1か所は中実にし、縦角・下端をR0.5で丸める。S01-V2より下面天井の支えを増やした比較案。丸入口案も#19の仮説を実物比較する候補であり、短い真円区間がサポート不要を保証するものではない。

印刷前：サポートOFFで、浮き警告・天井の積層・上面スタッドのInner wall・所要時間を確認。印刷後：大人が縁を触り、上下接続と球通過を両方向に確認。結果は刻印IDで報告すればよい。

```sh
python -m parts.tunnel.design --out build/play-set-v2/tunnel
python -m parts.elbow.design --out build/play-set-v2/elbow
python -m parts.sloped_curve.design --out build/play-set-v2/sloped_curve
python -m experiments.pr20_comparison.design
python -m parts.play_set.design
```

STEP、viewer、画像、自動レポートは `build/`。比較候補の詳細は [比較記録](../../experiments/pr20_comparison/README.md)、今回の検証範囲は [確認記録](records/revision-v2.md) に記載。
