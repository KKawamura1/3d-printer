# Issue #89 — R48カーブトンネルを「坂の有無だけ」で生成し直す

- 親Issue: https://github.com/KKawamura1/3d-printer/issues/89
- 元の箱型E01をSC02の扇形で切るだけのPR #90とは**設計が異なる**。
- 新エンジン: `brickcad/course_r48_unified.py`
- **実機印刷前提ではなく、2モデル同時生成・比較・球干渉確認のための独立PoC**。
- 旧E01/SC02、既存成功版、PR #75/#85/#87は一切編集しない。

## 1つの生成器・2つのモデル

| 入力 | 水平E01系列 | 坂ありSC02系列 |
|---|---|---|
| 新実験ID | `X89-E01-U1` | `X89-SC02-U1` |
| R48中心線 | 同一XY | 同一XY |
| 床Z | 6.35mm一定 | 西口25.55mm→北口6.35mm、smoothstepで19.2mm降下 |
| 外装 | 曲線に沿うLoft | **同じ**曲線Loft |
| スタッド | **同じ7個の完全な円形スタッド** | 同じ7個 |
| 下面チューブ | **同じ3本の完全なE31-05チューブ** | 同じ3本 |
| 窓 | **同じ外周5窓・角R0.8** | 同じ5窓（床の高さに追従） |
| 屋根上面 | Z=38.4mm | Z=57.6mm |
| 検査対象球 | 直径24.26mm | 同じ24.26mm |

- 本体外形ははじめからR48沿いにLoftし、矩形完成モデルの切断で細い支持片を作らない。
- シェル上下R、窓の角R、スタッド頭Rは共通。
- 屋根上面は**水平**（通常デュプロを載せるため）。坂ありモデルだけ屋根上面が高い。
- ポート中心の座標・向き、真円断面直径25.74mm、球径24.26mm、E31-05の下面スリット深さとビード仕様は固定。
- 内部の走路半径は両方とも端面から約1mmのリップで元通り、奥に約4mm遷移して **半径+0.4mm**（過去の停止報告に対応）。既製品側の開口を拡げる変更ではない。
- `X89-...` の凹刻印は試験的に5mm。E31/既存本番刻印標準は改変しない。

## 実行

```bash
python -m unittest experiments.r48_unified_issue89.test_contract -v
python -m experiments.r48_unified_issue89.export --out build/issue89-shared-r48
python scripts/stl_snapshot.py --stl build/issue89-shared-r48/X89-E01-U1/brick.stl --out build/issue89-shared-r48/X89-E01-U1/preview.png
python scripts/stl_snapshot.py --stl build/issue89-shared-r48/X89-SC02-U1/brick.stl --out build/issue89-shared-r48/X89-SC02-U1/preview.png
```

GitHub Actions `.github/workflows/issue89-r48-unified.yml` の通常pushは**軽量テストのみ**。対象2形状のCAD/STL/BRep+球干渉チェック・Artifact生成は `[issue89-cad]` のコミットか手動実行のみ。20形状を全生成しない。

## 強い制約と完了条件

- [ ] CAD結果が単一実体かつSTL水密、デュプロ外形内
- [ ] E01/SC02の球サンプリング21点でCAD干渉がなく、`+0.4mm` の内側径の端部遷移が連続
- [ ] 接続口が旧E01/SC02と**実BRep断面・位置・接線方向**で一致すること。今のポート解析は数値／入力契約検査で、完全な旧品との形状差分テストではない
- [ ] **同尺度・同視点**で5窓、7スタッド、3チューブ、内外壁、刻印の位置を手で目視
- [ ] Bambu Studio/A1 mini/PLA Basic/0.20mm/サポートOFFでスライスを確認
- [ ] 実機の保持力、支持材強度、子供が触る角、実際の球の転がり・継ぎ目停止を確認
- [ ] 左巻き版は鏡映後の刻印位置を別途確認し、改めてモデルID発行。現在は右巻き2品のみ
- [ ] 最終採用時だけ新規本番版IDとディスパッチャ統合を検討。旧版を上書きしない

**CADで球が干渉しない ≠ 実際に転がる/止まらない ≠ 印刷して遊んで安全。**

## CI検証ログ

このコミットから、2モデルのCAD/BRep/STL生成および21点×2の球干渉検証を意図的に実行する。結果はPR #91へ報告する。
