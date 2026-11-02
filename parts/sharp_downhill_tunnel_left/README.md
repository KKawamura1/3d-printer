# SD04-V7 — 左右共通生成の左側アダプタ

`parts/sharp_downhill_tunnel_right/design.py`（SD03-V8）と同じCAD形状をXZ平面で反転し、その**後で** `SD04-V7` の刻印を付与する。左右固有の走路実装・保持部実装は持たない。

- 共通仕様：`../sharp_downhill_tunnel_right/README.md`。
- STL出力：`python -m parts.sharp_downhill_tunnel_left.design --out build/sharp_downhill_tunnel_left`。
- 使用する刻印関数：標準の `brickcad.marking.engrave`（文字3mm、深さ0.4mm）。
- 依存する共通形状版は `SD03-V8` に固定し、右側の形状変更時は左側の版も更新して両方を再検証する。
