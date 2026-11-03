# SD04-V7 — 左右共通生成の左側アダプタ

`parts/sharp_downhill_tunnel_right/design.py`（SD03-V8）と同じCAD形状をXZ平面で反転し、その**後で** `SD04-V7` の刻印を付与する。左右固有の走路実装・保持部実装は持たない。

- 共通仕様：`../sharp_downhill_tunnel_right/README.md`。
- STL出力：`python -m parts.sharp_downhill_tunnel_left.design --out build/sharp_downhill_tunnel_left`。
- 使用する刻印関数：標準の `brickcad.marking.engrave`（文字3mm、深さ0.4mm）。
- 依存する共通形状版は `SD03-V8` に固定し、右側の形状変更時は左側の版も更新して両方を再検証する。


## PR58転用（SD03-V9 / SD04-V8）

スリット終端中心Z4.40→3.50mm、上端Z4.15mm（下面天井より0.60mm下）。リブなし。左右の共通形状と、反転後に標準刻印を刻む手順は維持。PR58の2×2試験片Bは印刷・嵌合感良好、当モデルは実印刷未検証。
