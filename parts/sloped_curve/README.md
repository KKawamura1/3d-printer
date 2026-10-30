# 坂カーブ

4×4、90度の曲がりに19.20mmの落差。上面スタッドなし。

[現在の印刷用STL](model.stl)。今回の嵌合条件・角処理・印刷手順・残る確認は [週末用コースセット](../play_set/README.md) に集約。旧試作品はGit履歴とdesign-notes.mdを参照。

```sh
python -m parts.sloped_curve.design --out build/sloped_curve
python -m unittest parts.sloped_curve.test -v
```

共通嵌合profileは duplo-e27-play-v1。保持力・実印刷・触感の新形状への転用は未検証。
