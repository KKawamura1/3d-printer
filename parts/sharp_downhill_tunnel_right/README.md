# SD03-V3

Issue #37: sharp_downhill_tunnel_right。独立した刻印・版付きパーツ。

- 16mmピッチ、高さ19.2mm、球径24.26mm。落差19.2mm。
- 天井: True。開放型にはスタッド・高い衝突壁を付けない。
- 下面の完全チューブにE31-05を移植。曲線輪郭で支持を切り、角の不要な床を除く。
- 刻印は入口下の非走行面（Z5.55mm、文字高1.1mm）。反転後に刻印するので鏡文字にならない。
- 連続球通過はレポートの折れ線全体をカプセルで検査。静的通過可能性であり、重力による自然転がりの証明ではない。
- Bambu Studioスライス・実物の転がり・嵌合は未確認。

生成: `python -m parts.sharp_downhill_tunnel_right.design --out build/sharp_downhill_tunnel_right`。
Actionsの`cad-verified-stl`にSTL/STEP/検証レポートを保存。

## 生成物の確認

V3はV1の形状改訂を版管理し、V2プレビューで発見した外周スタッドの細い断片を削除した版。V1/V2ではなく、V3に対するActionsの`cad-verified-stl`成功結果を印刷対象とする。R16急カーブの自然転がり、Bambu Studioでのサポートなしスライス、実物の保持力は未検証のため、量産前に小数のテスト印刷を行う。

- スタッドは屋根上で全周が支持される位置のみ採用し、曲線境界でクリップされる危険な半端スタッドを省く。
