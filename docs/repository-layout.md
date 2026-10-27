# 構成と移行方針

`parts/` は継続更新、`experiments/` は実験単位で固定する。ファイル形式で出力フォルダを分けない。Gitに置く生成物は印刷用STLのみ。設計入力・実測・判断の記録は生成物ではないため保存する。

ソース移動に伴いCLI/importは下表へ変更した。旧モジュールの互換ラッパーは設けない。`python -m brickcad build` は通常ブロックの汎用生成用として継続利用できる。旧パスはGit履歴で参照する。

| 旧パス | 新パス |
|---|---|
| `brickcad/calibration.py` | `experiments/initial_calibration/design.py` |
| `brickcad/elbow.py` | `parts/elbow/design.py` |
| `brickcad/experiment.py` | `experiments/full_height_fit/design.py` |
| `brickcad/pitagora.py` | `experiments/pitagora_m1/design.py` |
| `brickcad/rail.py` | `parts/straight_rail/design.py` |
| `brickcad/receiver_trial.py` | `experiments/receiver_fit/design.py` |
| `brickcad/sloped_curve.py` | `parts/sloped_curve/design.py` |
| `brickcad/stud_trial.py` | `experiments/stud_inner_wall/design.py` |
| `brickcad/tunnel.py` | `parts/tunnel/design.py` |
| `brickcad/xy_trial.py` | `experiments/xy_fit/design.py` |
| `docs/duplo-elbow-trial-01.md` | `parts/elbow/README.md` |
| `docs/duplo-experiment-01.md` | `experiments/full_height_fit/README.md` |
| `docs/duplo-fit-trial-01.md` | `experiments/fit_trial_01/README.md` |
| `docs/duplo-rail-trial-01.md` | `parts/straight_rail/README.md` |
| `docs/duplo-receiver-trial-01.md` | `experiments/receiver_fit/README.md` |
| `docs/duplo-sloped-curve-trial-01.md` | `experiments/sloped_curve_v1/README.md` |
| `docs/duplo-sloped-curve-trial-02.md` | `parts/sloped_curve/README.md` |
| `docs/duplo-stud-inner-wall.md` | `experiments/stud_inner_wall/README.md` |
| `docs/duplo-tunnel-trial-01.md` | `parts/tunnel/README.md` |
| `docs/duplo-xy-fit-trial-01.md` | `experiments/xy_fit/README.md` |
| `docs/pitagora-m1.md` | `experiments/pitagora_m1/README.md` |
| `docs/sim2real-duplo.md` | `experiments/initial_calibration/README.md` |
| `docs/sim2real.md` | `experiments/lego_calibration/README.md` |
| `profiles/duplo-2x2.json` | `experiments/nominal_duplo_2x2/profile.json` |
| `profiles/duplo-first-print.json` | `parts/basic_brick/profile.json` |
| `profiles/duplo-fit-trial-01.json` | `experiments/fit_trial_01/profile.json` |
| `profiles/duplo-xy-fit-trial-01.json` | `experiments/xy_fit/profile.json` |
| `profiles/first-print.json` | `experiments/lego_first_print/profile.json` |

## 生成物と記録

既存の個別STLはGit blob SHAを維持して移動する。STLを再生成・再メッシュ化しない。旧ZIPだけに入っていた16片・突起比較のSTLは、実験READMEの手順で必要時に生成する。元ZIPは詳細記録の固定コミットリンクから参照できる。

旧STEP・画像・viewer・3MF・ZIP・自動検証JSONは現行ツリーから除く。手書きの確認記録・実験条件・実測記入票は各フォルダの records/ に残し、旧パスやハッシュも当時の記録として維持する。共有の実測データは measurements/ に保持する。過去のレビューが今回の移動後に再実行されたことを意味しない。

共通基準 profiles/ と版付きの brickcad/standards.py は残し、パーツ／実験固有のJSONは所有者のフォルダへ移動する。終わった実験を正確に再現するときは、その実験を行ったGitコミットを使う。
