# SC02-V1 — 緩い坂 × 緩い右カーブ × トンネル

[Issue #37](https://github.com/KKawamura1/3d-printer/issues/37) の **M31-05** に対応する未印刷の試作。4×4、R48、90°右カーブ、高い西入口から北出口へDUPLO 1段（19.2 mm）下降。

- S01-V2 の開放型坂カーブを走行面・曲線フットプリント・下面接続の基礎に使う。既存パーツは変更しない。
- **壁と天井のある完全なトンネル**。両端約1 mmは円形口、続く約4 mmで内部が高い涙滴形へ遷移。屋根は走路に沿って下降し、最上部は約3段。
- S01同様、上面スタッドなし。下部は完全な3本のチューブのみ。E31-05の直径13.20 mm・保持ビード・4スリットを移植するが、**新形状での保持力は未検証**。
- 凹刻印は SC02-V1。ソース変更時は隣接cad-build.jsonの版更新が必要。

実行: python -m parts.sloped_curve_tunnel.design --out build/sloped_curve_tunnel
テスト: python -m unittest parts.sloped_curve_tunnel.test -v

STL/STEPと簡易プレビューはpush時のCAD Actionsが差分生成する。大容量の生成物はコミットしない。

**残る検証**：連続球掃引クリアランス、Bambu Studioで0.20mm積層・サポートなしのスライス、長い屋根のブリッジ、実物の転がりと跳ね返り、純正・印刷品相互の着脱／保持力。有限個の球サンプルは連続経路や物理的な成功の保証ではない。
