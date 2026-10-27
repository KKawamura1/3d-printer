# 通常ブロック 2×4

既存の通常ブロック。合成名目寸法の候補であり、最新の嵌合調整を採用したことを意味しない。

印刷用: [model.stl](model.stl)。mm・100%で読み込み、スライスは手元で行う。

## 生成

```sh
python -m parts.basic_brick.design --out build/basic-brick
```

生成時のSTEP・viewer・画像・検証JSON等は `build/basic-brick/` 内の中間生成物。採用するSTLだけを更新する。

```sh
cp build/basic-brick/brick.stl parts/basic_brick/model.stl
```

`records/` は当時の条件・記入票・確認記録。新規の実測結果も設計入力や自動検証の出力と区別して保存する。

既存STLをそのまま移動したもの。今回の構成整理では形状・寸法・印刷条件は変更していない。
