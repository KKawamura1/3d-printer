# 水平・緩い左カーブ・トンネル

[右版E01-V3](../gentle_curve_tunnel/README.md) の**無刻印**CADをXZ面で反転し、可視の南面へ `E01L-V1` を標準の3.0mm／0.4mmで凹刻印する。右版の文字を反転しない。

```sh
python -m parts.gentle_curve_tunnel_left.design --out build/r48-left
```

STL生成は右版E01-V3へのバージョン固定依存。実物の逆向き通過は未検証。
