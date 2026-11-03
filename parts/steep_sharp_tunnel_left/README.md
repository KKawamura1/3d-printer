# S03-V7 — 急落下＋急左カーブトンネル（PR #41）

[右版S02-V13](../steep_sharp_curve_tunnel/)の**無刻印BRep**をXZ面で鏡映した後、南の完成外壁へ `brickcad.marking.engrave()` により `S03-V7` を凹刻印。DejaVu Sans Bold／3.0mm／深さ0.4mm。左右の形状は1PR内の共通実装で維持し、鏡文字は発生させない。

西高入口Z25.55→北低出口Z6.35。出口坂は約14°、接続口は真円。E31-05スリットはPR #58のB条件（終端Z3.50、上端Z4.15、床天井Z4.75、リブなし）。

`cad-build.json`は右版S02-V13を依存指定する。STLは最新版Artifact内 `parts/steep_sharp_tunnel_left/S03-V7/brick.stl`。

**この版は実機未検証**。サポートOFF、床面、文字可読性、転がり、接続、嵌合・耐久を印刷後に確認する。詳細は[共通README](../steep_sharp_curve_tunnel/README.md)。
