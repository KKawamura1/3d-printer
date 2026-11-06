"""Pack ALL eleven architectural windows into printable A1 mini plate(s).

This is an explicit after-build step, NOT an additional production geometry
source. Prefer existing preview-plate packing code and preserve every model
as a separately identifiable STL. It is valid for the pieces to need more
than one plate; one overnight print may use only plate1.
"""
import json
from pathlib import Path
import argparse

from brickcad.course_architectural_windows import VERSIONS
from scripts.course_catalog import load_registry
from scripts.course_followup_print import create_print_plates


def collect(input_folder):
    input_folder=Path(input_folder)
    sources={m["id"]:m for m in load_registry()["models"]}
    paths,meta={},{}
    for source_id,version in VERSIONS.items():
        folder=input_folder/("architectural-"+source_id)
        stl=folder/"brick.stl"
        report=folder/"report.json"
        if not stl.is_file() or not report.is_file():
            raise FileNotFoundError(f"Not all eleven sources built: {source_id}")
        data=json.loads(report.read_text())
        if (data.get("part_id")!=version or data.get("passed") is not True
                or data.get("physical_fit_validated") is not False
                or data.get("slicing_validated") is not False):
            raise ValueError(f"Invalid source CAD report or misattributed print: {source_id}")
        paths[version]=stl
        meta[version]={
            "source_model_id":source_id,
            "issue37_no":sources[source_id]["issue37_no"],
            "course":{**sources[source_id]["course"],
                      "windows":data["geometry"]["total_windows"]},
            "source_reference":sources[source_id]["source"]["reference"],
            "contract_evidence":data["contract_evidence"],
        }
    return paths,meta


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,default=Path("build/window-models"))
    parser.add_argument("--out",type=Path,default=Path("build/window-plates"))
    args=parser.parse_args()
    paths,meta=collect(args.input)
    out=args.out
    out.mkdir(parents=True,exist_ok=True)
    result=create_print_plates("architecture",paths,meta,out)
    if result["model_count"]!=len(VERSIONS):
        raise ValueError("Missing shapes from night print campaign")
    print("ARCHITECTURAL WINDOW PLATES:",result["plate_count"],flush=True)
    for index,plate in enumerate(result["plates"],1):
        print("plate",index,":",",".join(plate["items"]),flush=True)


if __name__=="__main__":
    main()
