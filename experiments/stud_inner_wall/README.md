# 突起のInner wall比較

14片比較。穴径・外径の段階は --stage holes / diameters で選ぶ。過去にZIPだけで配布したSTLは必要時に生成する。旧ZIPは design-notes.md の固定コミットのリンクから取得できる。

## 生成

```sh
python -m experiments.stud_inner_wall.design --stage combined --hole 6.40 --out build/stud-inner-wall
```

出力は `build/stud-inner-wall/`。必要なSTLだけをスライサーへ渡す。STEP・viewer・検証JSON等は中間生成物。

## 検証

```sh
python -m unittest experiments.stud_inner_wall.test -v
```

[設計・実験の詳細記録](design-notes.md)

`records/` は当時の条件・記入票・確認記録。新規の実測結果も設計入力や自動検証の出力と区別して保存する。

この実験の刻印・条件・保存済みSTLは固定し、次の比較には新しい実験フォルダを作る。正確な過去の再現には [移行前のコミット](https://github.com/KKawamura1/3d-printer/tree/c0ff73d59efe906385426e859ac26ff70e7f650e) を使う。共通処理の更新後も当時の生成結果を保証するものではない。
