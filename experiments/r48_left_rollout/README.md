# PR91のR48大窓レールを左向きにも展開（次の2個入り印刷プレート）

## 印刷対象

| ID | 形状 | 対応する実機良好な右向きモデル |
|---|---|---|
| `X89-E01L-R10` | 水平・左R48・トンネル・5大窓 | `X89-E01-R10` |
| `X89-SC02L-R10` | 19.2mm下り・左R48・トンネル・5大窓 | `X89-SC02-R10` |

- PR #91を正とする。既存の `R48FamilyConfig(..., direction="left", relief_mm=1.0)` / `build_r48_family(..., marked=False)` で**完成BRepを鏡映**する。底面の受け・走路・部分受け・スタッド・大窓を独自に書き直さない。
- 入口・出口の直径は公称25.74mmで固定。**内部だけ**最大半径+1.0mmのR10。外側5窓×幅12mm、角R0.8。凹側には窓を作らない。
- PR #94が共通化した `course_finish.engrave_trial_west_skirt` で、**鏡映後に**正像5mm刻印を彫る。左側の受け壁はY=0..31.9mmで、刻印中心はY=16mm。物理文字は `E01L-R10` / `SC02L-R10`（ファイル・レポートのフルIDは維持）。
- PR91右向きの実績品も、旧E01L/SC02Lや他の確定モデルも上書きしない。

## 機械的検証と印刷準備

`experiments/r48_left_rollout/export.py` に、モデルごとの単一BRep、水密STL、STL体積一致、実ポートの96点断面、旧SC02下面構造・3完全+4部分受け、スタッド挿入の非嵌合部の接触なし、Z=0.1/4.65mm受け支持断面、5大窓、文字全体の完全収まりを検査する。

実ポート断面の確認にはPR91の実績あるポートプローブを流用し、左向きの完成品を**検証用だけ鏡映して右向き座標系へ戻す**。STL自体にはこの変換をかけない。

A1 mini 180×180mmに2個をXY±36mmへ配置する。元STLをXY平行移動するだけで結合し、SHA256一致・XY間隔5mm以上・ベッド外形を検査する。印刷対象は2個入り `X89_R48_left_E01L_SC02L_2parts_A1mini.stl`。

```bash
python -m unittest experiments.r48_left_rollout.test -v
python -m experiments.r48_left_rollout.export --out build/r48-left
# CIでは個別の並列生成後に --assemble-only で合体
```

GitHub Actions `R48 left big-window print trial (PR91 and PR94)` は新規ブランチへのpush時、個別2ジョブを並列実行し、一括STL・個別STEP/STL・manifest・検証JSONをArtifactにまとめる。重い共通20モデル全件CADは実行しない。

## 印刷実験で確認すること（未完了）

1. Bambu StudioでA1 mini / PLA Basic / 積層0.20mm / **サポートOFF** をスライス。特にZ=4.75mm近辺の下面ブリッジ、窓上端の支柱、断面の空中部分を確認する。
2. 底面受けと上面スタッドの実物嵌合、刻印の可読性、窓の強度・角をチェックする。
3. 純正レール→新E01L/SC02L→純正レール、さらに印刷レール同士の境界を固定条件で転がし、**入口・カーブ内・出口**の停止位置を記録する。
4. 連続転がりと反復着脱の長期試験は別途追跡する。

**CAD/STLの成功と実機成功は別。** この2種類は新規試作品として扱い、初回印刷が良好なことを確認するまでmainへマージしない。PR #91 / #94で確認済みの既存品は再印刷しない。

関連: [PR #91](https://github.com/KKawamura1/3d-printer/pull/91)、[PR #94](https://github.com/KKawamura1/3d-printer/pull/94)、[横断共通化 Issue #95](https://github.com/KKawamura1/3d-printer/issues/95)。
