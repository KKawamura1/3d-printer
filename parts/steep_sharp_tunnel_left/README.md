# S03-V5 — 急落下＋急左カーブトンネル（PR41統合版）

PR #45で独立していた左版を、PR #41の右版S02-V11から生成する方式に統一。

**生成順序**
1. 共通形状 `parts.steep_sharp_curve_tunnel.design.build_tunnel(label=None)` を生成（スタッド、下面E31-05、円形口、1:4約14°出口坂、屋根を含む）。
2. XZ面でY軸反転する。西側高入口はそのまま、南側低出口が北側に変わる。
3. 鏡映した**後に**南面に `S03-V5`（3.0mm）の凹刻印を行う。文字は鏡映せず、外側から正しく読める。
4. S03の独立STL `brick.stl` とCAD report/STEPを出力する。右版のSTLと混同しない。

外形は31.8×31.8×57.6 mm、スタッド含む高さ62.1 mm。高入口Z25.55→低出口Z6.35、落差19.2 mm。出入口の円形断面を16方向で検証、球径24.26 mmの球掃引・下面支持・上面4スタッドを検査する。

```sh
python -m parts.steep_sharp_tunnel_left.design --out build/s03
python -m unittest parts.steep_sharp_tunnel_left.test -v
```

`cad-build.json` は S02-V11 を明示的に要求するので、右版の形状更新が左版に自動反映される。GitHub Actions Artifact `cad-verified-stl/parts/steep_sharp_tunnel_left/S03-V5/brick.stl` を印刷に使用。

**注意**：鏡映CADと球クリアランスは実機の転がりやサポート不要のスライスを保証しない。左右両方で接続・刻印を試すこと。


## PR58 下面の印刷対策

S02-V12 / S03-V6ではE31-05スリット終端中心をZ4.40→Z3.50mmへ短縮。上端Z4.15mmで下面天井Z4.75mmを突き抜けない。リブなし。PR58 B試験片の床・嵌合は良好だが、本パーツの支持なしスライス・実機印刷・保持力は未検証。
