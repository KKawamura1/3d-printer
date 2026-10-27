# duplo-2x2 ブラウザ目視確認

2026-10-24、Chromium 153.0.8010.0で実際に撮影した画像をエージェントが開いて確認した。

- 上面: 中空スタッドの個数と穴、外形を確認。
- 裏面: 開口と中空チューブを確認。
- CAD断面: スタッド穴の底・天井・側壁・チューブを確認。
- 着座、分解、90度交差: 赤と青のモデルの向き・高さ・隠面表示を確認。
- 回転・ズーム・モバイル: 描画と操作パネルの表示を確認。DUPLO寸法に応じて自動的に画角を合わせる。
- 半ピッチずれの負例では干渉あり表示、正常姿勢では検出なし表示。

CAD寸法と実物DUPLOの嵌合、保持力、スライサー結果は別途校正が必要。純正の完全な形状再現ではない。

## 確認対象

viewer.html SHA-256: `485292f04e5ca937f96cfe3b81ca4191cba9f6672fb60d168bd120020b3904c6`

| 画像 | SHA-256 |
|---|---|
| 01-perspective.png | `8fbfc4ef3eb9ca706d50286905fc21d37b75427ff6b18cf71401bab2c238b3c9` |
| 02-top.png | `d6904a2d6e6cbf60aa5b9b93a75bd8128bac64d71f3f58bbf26d15a91724ce7b` |
| 03-underside.png | `76be4bf48ca5fe14144a6b52d026acc36380e0b58f459c561af5a16d21954ffb` |
| 04-section.png | `c63b5d263d9788c4039248d316e32f8747eae96ec8abc74a3c99e7505932c56a` |
| 05-assembled.png | `688abd0fa719da689fbc116238bedcf0075c07bb8029fb1fd52a7056c000ae2b` |
| 06-exploded.png | `818a9a2a5fe448cbac8ba37ae6ab4f008e39d4e8e2c54798d1038d3af6b2eadd` |
| 07-cross-90.png | `6b8e9678e6ee098f221d0edb8862f2d22555453f43d8db6e9386d682b59e8c0c` |
| 08-collision-control.png | `62d782560b6b9d532b967f2e958525cbecb73a5f707cee60e16480c67bb24f06` |
| 09-orbit-zoom.png | `88e922d5c7637ba40b751e0e85ccce52a1650d1d8b6864d43fd05abab4f05765` |
| 10-mobile.png | `d0e98e8c896c0b3fbe21a388cf3a4a4bb6e88190b210ddfbf78897739a3abea5` |

review-sheet.jpgは上記10画像の縮小一覧。browser-report.jsonは自動撮影時の状態を維持し、後から行った目視確認は本文書に記録する。
