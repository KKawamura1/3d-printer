# 90度トンネル

継続開発する曲がり通路。実物の通過・保持力は個別に確認する。

印刷用: [model.stl](model.stl)。mm・100%で読み込み、スライスは手元で行う。

## 生成

```sh
python -m parts.elbow.design --out build/elbow
```

生成時のSTEP・viewer・画像・検証JSON等は `build/elbow/` 内の中間生成物。採用するSTLだけを更新する。

```sh
cp build/elbow/brick.stl parts/elbow/model.stl
```

## 検証

```sh
python -m unittest parts.elbow.test -v
```

[設計・実験の詳細記録](design-notes.md)

`records/` は当時の条件・記入票・確認記録。新規の実測結果も設計入力や自動検証の出力と区別して保存する。

既存STLをそのまま移動したもの。今回の構成整理では形状・寸法・印刷条件は変更していない。
