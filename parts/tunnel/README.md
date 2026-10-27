# 直線トンネル

継続利用する2段トンネル。通路・下面の寸法は従来どおり。

印刷用: [model.stl](model.stl)。mm・100%で読み込み、スライスは手元で行う。

## 生成

```sh
python -m parts.tunnel.design --out build/tunnel
```

生成時のSTEP・viewer・画像・検証JSON等は `build/tunnel/` 内の中間生成物。採用するSTLだけを更新する。

```sh
cp build/tunnel/brick.stl parts/tunnel/model.stl
```

## 検証

```sh
python -m unittest parts.tunnel.test -v
```

[設計・実験の詳細記録](design-notes.md)

`records/` は当時の条件・記入票・確認記録。新規の実測結果も設計入力や自動検証の出力と区別して保存する。

既存STLをそのまま移動したもの。今回の構成整理では形状・寸法・印刷条件は変更していない。
