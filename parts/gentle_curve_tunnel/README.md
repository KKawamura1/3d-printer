# 水平・緩い左右カーブ・トンネル（Issue #37 No.07/08）

旧 `parts/elbow` E01-V2 は歴史的なE27試作品として維持し、E31-05採用版を新規追加する。

- **右 E01-V3:** `parts/gentle_curve_tunnel/`
- **左 E01L-V1:** `parts/gentle_curve_tunnel_left/` （無刻印の右CADをXZ鏡映、反転後に正立刻印）
- 4×4×高さ2、外形63.8×63.8×42.9mm（スタッド込み）、水平90° R48、球24.26mm
- 見える入口・出口は真円、1mmの円形リップから約4mmかけて内部の高天井へ遷移
- 天井・壁あり。南／北の向き以外は同じ通路、開放型ガード壁は追加しない
- E31-05：下面チューブ外径13.20、ビードR0.20、4方向スリット（終端中心Z3.50mm）。浅い受け深さ4.75mmの床まで0.60mmの余裕、補強リブなし
- 完全な9本の下面チューブ／16個の上面スタッドを維持。切断支持が必要な輪郭ではない
- 刻印：DejaVu Sans Bold、文字高3.0mm、深さ0.4mm。反転後の完成した可視南面に正像で凹刻印

```sh
python -m parts.gentle_curve_tunnel.design --out build/r48-right
python -m parts.gentle_curve_tunnel_left.design --out build/r48-left
python -m unittest parts.gentle_curve_tunnel.test parts.gentle_curve_tunnel_left.test -v
```

STL、STEP、CAD検証レポートはGitHub Actions `cad-verified-stl` Artifactで取得する。旧版の配布STLを新しいE31版と取り違えない。

**CAD合格と物理合格は別。** A1 mini／Bambu StudioでサポートOFFの床面、橋渡し、入口真円、刻印をスライス・造形確認し、純正／印刷同士の保持力と右左それぞれ10回の自然転がりを確認する。水平レールには入射速度が必要。
