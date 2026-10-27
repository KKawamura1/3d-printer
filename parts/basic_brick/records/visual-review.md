# duplo-2x4 ブラウザ目視確認

2026-10-24、Chromium 153.0.8010.0で実際に撮影した画像をエージェントが開いて確認した。

- 上面: 中空スタッドの個数と穴、外形を確認。
- 裏面: 開口と中空チューブを確認。
- CAD断面: スタッド穴の底・天井・側壁・チューブを確認。
- 着座、分解、90度交差: 赤と青のモデルの向き・高さ・隠面表示を確認。
- 回転・ズーム・モバイル: 描画と操作パネルの表示を確認。DUPLO寸法に応じて自動的に画角を合わせる。
- 半ピッチずれの負例では干渉あり表示、正常姿勢では検出なし表示。

CAD寸法と実物DUPLOの嵌合、保持力、スライサー結果は別途校正が必要。純正の完全な形状再現ではない。

## 確認対象

viewer.html SHA-256: `f8c79a0a13910a3c7ec64730859bfa991636a83c15008e4dc12a38446c3011ee`

| 画像 | SHA-256 |
|---|---|
| 01-perspective.png | `0c01789ad93279fc36b034f8a1129abd9958bb1490f235fb09dc6d58134cfca2` |
| 02-top.png | `541e75635563845854860ec3e0b47c04ad405d2555b6371957aa41e856e07aa7` |
| 03-underside.png | `f1425a3db9191c6a914b179a031787971f30384989e39f425e74ce880127aaa3` |
| 04-section.png | `3f5f1e28aacf3271e9aed47dbd6a61f1697a02fe8de896842fbb7d5d6f6e2d85` |
| 05-assembled.png | `e27db0d8682c5dfabc841a042ebba32df3e5793e024563ac388ca2e79b6b2dd3` |
| 06-exploded.png | `22fbd120e8e5f70bb945d571104a93dff95fb318dc891c209eebcae418f49d9e` |
| 07-cross-90.png | `8f8b49ee4c38ca65c4be82d321c8ef1596997af18987d92fd95492261ef2fecd` |
| 08-collision-control.png | `5002320a2a7efebaf9d4fe2222faba461e7eec0d62e646510a43e53e996d0904` |
| 09-orbit-zoom.png | `4a37f9b151796d4fcdff57322bc2c85a2c02cd357758c5d5bba6596774486e67` |
| 10-mobile.png | `05b797d3a1f436995bc316cbf888b90599650072f27f7f2054f9d6d22f800553` |

review-sheet.jpgは上記10画像の縮小一覧。browser-report.jsonは自動撮影時の状態を維持し、後から行った目視確認は本文書に記録する。
