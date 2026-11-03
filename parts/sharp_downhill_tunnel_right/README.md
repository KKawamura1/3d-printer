# SD03-V8 / SD04-V7 — 緩坂＋急カーブ・左右共通生成

Issue #37 / PR #50。右カーブ（SD03）と左カーブ（SD04）は**共通BRepをXZ面で鏡面反転**して生成する。別形状として手修正しない。

- **共通形状:** `parts/sharp_downhill_tunnel_right/design.py` に1つだけ実装する。
- **右:** `SD03-V8`、`build_part(mirror=False)`。刻印は `SD03-V8`。
- **左:** `SD04-V7`、`parts/sharp_downhill_tunnel_left/design.py` は薄い呼び出しラッパー。共通形状を反転し、**反転後に** `SD04-V7` を凹刻印。文字は鏡文字にならない。
- **刻印標準:** `brickcad.marking.engrave` 既定値（DejaVu Sans Bold / 文字サイズ3.0mm / 深さ0.4mm）、位置は直線部外側（X=-16, Z=12, -Y外壁）。
- **開口:** mainのトンネル方式を参照し入口・出口を円形に、1mmの円形リップと4mmの屋根遷移。
- **下面・上面:** 輪郭切断チューブとスタッドを保持。完全チューブへのE31-05適用、極小スタッド片除去は既存仕様を維持。
- **差分テスト:** 左右の走路・ポート鏡面対称、刻印前BRepの鏡像一致、口の円形断面、CAD閉鎖単一ソリッド、連続球掃引、刻印の実切削。
- **印刷:** 2つの`cad-build.json`を更新し、1つのPRからそれぞれのSTL/STEP/レポートを生成する。実機での自然転がり・スライス・嵌合は未検証。

```sh
python -m parts.sharp_downhill_tunnel_right.design --out build/sharp_downhill_tunnel_right
python -m parts.sharp_downhill_tunnel_left.design --out build/sharp_downhill_tunnel_left
```

PR #51 は独立生成コードを引き継いだため統合後にクローズする。PR #55 の旧一括プレートはこの版を含まない。


## PR58転用（SD03-V9 / SD04-V8）

スリット終端中心Z4.40→3.50mm、上端Z4.15mm（下面天井より0.60mm下）。リブなし。左右の共通形状と、反転後に標準刻印を刻む手順は維持。PR58の2×2試験片Bは印刷・嵌合感良好、当モデルは実印刷未検証。
