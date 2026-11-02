# SD01-V2

Issue #37: sharp_downhill_open_right。独立した刻印・版付きパーツ。

- 16mmピッチ、高さ19.2mm、球径24.26mm。落差19.2mm。
- 天井: False。開放型にはスタッド・高い衝突壁を付けない。
- 下面の完全チューブにE31-05を移植。曲線輪郭で支持を切り、角の不要な床を除く。
- 刻印は `brickcad.marking.engrave()` の標準仕様（DejaVu Sans Bold、文字サイズ3.0mm、凹み0.4mm）。入口直線区間の外側 -Y 面（X=-16mm、Z=12mm）へ移動。形状の左右反転後に刻印するので鏡文字にならない。
- 連続球通過はレポートの折れ線全体をカプセルで検査。静的通過可能性であり、重力による自然転がりの証明ではない。
- Bambu Studioスライス・実物の転がり・嵌合は未確認。

生成: `python -m parts.sharp_downhill_open_right.design --out build/sharp_downhill_open_right`。
Actionsの`cad-verified-stl`にSTL/STEP/検証レポートを保存。
