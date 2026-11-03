# SC02L-V4 — 緩坂 × 緩左カーブ × トンネル

Issue #37 の緩左カーブ・トンネルの未実装セルをPR #40へ統合する。右版 `SC02-V10` と**同じ無刻印CAD**を使用し、XZ面で反転してから左版 `SC02L-V4` を西面へ標準刻印する。文字は鏡映しない。

- 4×4×高さ3、R48、落差19.2mm、入口は西側高位置、出口は南側低位置
- 上面スタッド10個は輪郭切断型。下面は完全チューブ3本（E31-05）＋部分支持チューブ4本
- 共通E31-05はスリット終端Z3.50mm（R0.65mm、天井まで0.60mm）
- 真円入口と出口、内部で高い涙滴屋根へ遷移
- 刻印：DejaVu Sans Bold、3.0mm、0.4mm凹み。完全なCAD合成と鏡映の後に実施
- 凹刻印回帰、真円ポート、BRep・閉鎖STL、球干渉、左右ポート高はCADテストで検査する

実行：`python -m parts.sloped_curve_tunnel_left.design --out build/sloped-curve-tunnel-left`

テスト：`python -m unittest parts.sloped_curve_tunnel_left.test -v`

GitHub Actionsの `cad-verified-stl` Artifactから個別の `brick.stl` を取得する。CAD成功はサポートOFFでのBambu Studio確認や実物合格を意味しない。床面／天井／刻印の造形、球10回通過、次レール接続、保持力と耐久は未検証。

## STEP往復検証の数値許容範囲（SC02L-V4）

PR #61の`brickcad.verify.precise_volume()`を使用してSTEP再読込後の体積を適応積分で比較する。許容閾値は元の**相対体積差1e-6未満**を維持（緩和しない）。加えて**有効な単一ソリッド**および**外形寸法差0.02mm未満**を必須とする。以前左版で観測された3.20e-6の差は通常のOCC体積積分の数値誤差であり、PR61の共通高精度計算で対処する。形状・スリット・走路の変更ではない。実印刷は未検証。
