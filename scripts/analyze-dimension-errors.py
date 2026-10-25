#!/usr/bin/env python3
"""Describe reported dimensions without treating caliper readings as printer truth.

Standard library only. Run from any working directory; no CAD/browser dependency.
"""
import argparse
import json
import math
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def summary(values):
    values = list(values)
    return dict(n=len(values), mean=st.mean(values),
                sample_sd=st.stdev(values) if len(values) > 1 else None,
                minimum=min(values), maximum=max(values))


def errors(records, feature, axis=None):
    return [r['value_mm'] - r['cad_mm'] for r in records
            if r['feature'] == feature and r.get('bed_axis') == axis
            and r.get('value_mm') is not None and r.get('cad_mm') is not None]


def rms(values):
    values = list(values)
    return math.sqrt(st.mean(x*x for x in values))


def analyze(data):
    records = data['observations']
    current = [r for r in records if r['job'] == 'experiment16']
    ids = sorted({r['part'] for r in current})
    # One XY average per part, never pretend the two axes are two print repeats.
    studs = []
    for part in ids:
        rr = [r for r in current if r['part'] == part and r['feature'] == 'stud_od']
        studs.append(dict(part=part, cad_mm=rr[0]['cad_mm'],
                          observed_mm=st.mean(r['value_mm'] for r in rr),
                          role=rr[0]['toolpath_role']))
    gap = [s for s in studs if s['role'] == 'gap_infill']
    inner = [s for s in studs if s['role'] == 'inner_wall']
    bias = st.mean(s['observed_mm']-s['cad_mm'] for s in gap)
    single_bias = st.mean(s['observed_mm']-s['cad_mm'] for s in studs)
    role_fit = [s['observed_mm']-s['cad_mm'] -
                st.mean(t['observed_mm']-t['cad_mm'] for t in studs if t['role']==s['role'])
                for s in studs]
    # Within-job LOO: optimistic for a future job. Inner's singleton is not validated.
    loo_gap = []
    loo_linear = []
    for held in gap:
        train = [s for s in gap if s is not held]
        offset = st.mean(s['observed_mm']-s['cad_mm'] for s in train)
        loo_gap.append(held['observed_mm']-held['cad_mm']-offset)
        xm = st.mean(s['cad_mm'] for s in train)
        ym = st.mean(s['observed_mm'] for s in train)
        slope = sum((s['cad_mm']-xm)*(s['observed_mm']-ym) for s in train) / sum((s['cad_mm']-xm)**2 for s in train)
        loo_linear.append(held['observed_mm']-(ym+slope*(held['cad_mm']-xm)))
    walls = {}
    wall_loo = {}
    for feature in ['body_span', 'receiver_span']:
        walls[feature] = {axis: summary(errors(current, feature, axis)) for axis in ['X','Y']}
        residuals = []
        for r in current:
            if r['feature'] != feature:
                continue
            train = [t for t in current if t['part'] != r['part']]
            predicted_error = st.mean(errors(train, feature, r['bed_axis']))
            residuals.append(r['value_mm']-r['cad_mm']-predicted_error)
        wall_loo[feature] = dict(part_held_out_rmse_mm=rms(residuals),
                                 max_abs_error_mm=max(map(abs,residuals)))
    thickness = []
    shared_residuals = []
    for part in ids:
        for axis in ['X','Y']:
            b = next(r for r in current if r['part']==part and r['feature']=='body_span' and r['bed_axis']==axis)
            c = next(r for r in current if r['part']==part and r['feature']=='receiver_span' and r['bed_axis']==axis)
            thickness.append((b['value_mm']-c['value_mm'])/2)
            shared_residuals.append((c['value_mm']-c['cad_mm'])-(b['value_mm']-b['cad_mm']))
    old = {}
    for part in ['02','03']:
        vals = [r['value_mm'] for r in records if r['job']=='compact5' and r['part']==part and r['session']=='detail' and r['feature']=='stud_od']
        old[part] = summary(vals)
    tube_deltas = []
    stud_deltas = []
    for part in ids:
        for feature, result in [('tube_od',tube_deltas),('stud_od',stud_deltas)]:
            vals = [r['value_mm'] for r in current if r['part']==part and r['feature']==feature]
            result.append(abs(vals[0]-vals[1]))
    return {
        'schema_version': 1, 'units': 'mm',
        'scope': 'Conditional descriptive model for reported readings; not unloaded geometry, machine accuracy, or a validated CAD compensation.',
        'source_snapshot': '2026-10-25-error-model-sources.json',
        'counts': {'observation_records':len(records), 'measured_experiment_parts':len(ids),
                   'unmeasured_experiment_parts':['05','06','08','09','11','12','13','14','16'],
                   'controlled_same_site_repeats':0},
        'current_stud_part_means':studs,
        'stud_role_offsets': {
            'gap_infill': {**summary(s['observed_mm']-s['cad_mm'] for s in gap),
                           'domain_cad_mm':[min(s['cad_mm'] for s in gap),max(s['cad_mm'] for s in gap)],
                           'loo_within_job_rmse_mm':rms(loo_gap)},
            'inner_wall': {**summary(s['observed_mm']-s['cad_mm'] for s in inner),
                           'domain_cad_mm':[9.48,9.48], 'validated':False},
            'observed_role_offset_difference_mm':st.mean(s['observed_mm']-s['cad_mm'] for s in inner)-bias,
            'causal_role_effect_identifiable':False,
            'single_offset_training_rmse_mm':rms(s['observed_mm']-s['cad_mm']-single_bias for s in studs),
            'role_offsets_training_rmse_mm':rms(role_fit),
            'gap_free_slope_loo_rmse_mm':rms(loo_linear),
            'free_slope_adopted':False},
        'current_straight_wall_offsets':walls,
        'straight_wall_validation':wall_loo,
        'effective_wall_thickness_paired':summary(thickness),
        'receiver_minus_body_error_paired':summary(shared_residuals),
        'compact_stud_detail_descriptive':old,
        'current_xy_absolute_difference':{'stud_od':summary(stud_deltas),'tube_od':summary(tube_deltas)},
        'unidentified_parameters':[
            'caliper absolute bias and pure repeatability', 'measurement-force compliance and contact geometry bias',
            'between-job variance', 'independent bed-position and rotation effects',
            'global scale versus feature/size offsets', 'unloaded roundness',
            'tube/inner-diameter compensation', 'quantitative clutch force'],
        'automatic_cad_compensation_enabled':False,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',type=Path,default=ROOT/'measurements/2026-10-25-dimension-observations.json')
    ap.add_argument('--output',type=Path,default=ROOT/'measurements/2026-10-25-error-model.json')
    args = ap.parse_args()
    data = json.loads(args.input.read_text())
    result = analyze(data)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))


if __name__ == '__main__':
    main()
