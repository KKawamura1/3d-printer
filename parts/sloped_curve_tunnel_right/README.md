# SC04-V2

Issue #37: sloped_curve_tunnel_right。独立した刻印・版付きパーツ。

- 16mmピッチ、高さ19.2mm、球径24.26mm。落差19.2mm。
- 天井: True。開放型にはスタッド・高い衝突壁を付けない。
- 下面の完全チューブにE31-05を移植。曲線輪郭で支持を切り、角の不要な床を除く。
- 刻印は入口下の非走行面（Z5.55mm、文字高1.1mm）。反転後に刻印するので鏡文字にならない。
- 連続球通過はレポートの折れ線全体をカプセルで検査。静的通過可能性であり、重力による自然転がりの証明ではない。
- Bambu Studioスライス・実物の転がり・嵌合は未確認。

生成: `python -m parts.sloped_curve_tunnel_right.design --out build/sloped_curve_tunnel_right`。
Actionsの`cad-verified-stl`にSTL/STEP/検証レポートを保存。

STEP往復は適応型Gauss積分（相対誤差1e-9）による体積差0.01mm³未満とソリッド有効性を検査。
