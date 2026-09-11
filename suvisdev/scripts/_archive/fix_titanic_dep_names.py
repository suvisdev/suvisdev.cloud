from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "apps" / "titanic"

RENAMES = {
    "get_james_use_case": "get_crew_james_director_use_case",
    "get_walter_use_case": "get_crew_walter_roaster_use_case",
    "get_andrews_blueprint_use_case": "get_crew_andrews_architect_use_case",
    "get_cal_pistol_use_case": "get_passenger_cal_tester_use_case",
    "get_hartley_violin_use_case": "get_crew_hartley_violin_use_case",
    "get_isidor_bed_use_case": "get_passenger_isidor_couple_use_case",
    "get_jack_sketch_use_case": "get_passenger_jack_trainer_use_case",
    "get_rose_diamond_use_case": "get_passenger_rose_model_use_case",
    "get_ruth_corset_use_case": "get_passenger_ruth_validation_use_case",
    "get_smith_captain_use_case": "get_crew_smith_captain_use_case",
    "get_lowe_boat_use_case": "get_crew_lowe_boat_use_case",
    "get_molly_scaler_use_case": "get_passenger_molly_scaler_use_case",
}

STALE = [
    "adapter/inbound/api/v1/walter_router.py",
    "adapter/inbound/api/v1/james_router.py",
    "adapter/outbound/pg/walter_pg_repository.py",
    "adapter/outbound/pg/james_pg_repository.py",
    "app/use_cases/walter_interactor.py",
    "app/use_cases/james_interactor.py",
    "app/dtos/crew_walter_roaster_dto.py",
    "app/dtos/crew_james_director_dto.py",
    "dependencies/james.py",
    "dependencies/walter.py",
]

for rel in STALE:
    p = ROOT / rel
    if p.exists():
        p.unlink()

for path in ROOT.rglob("*.py"):
    text = path.read_text(encoding="utf-8")
    new = text
    for old, new_name in RENAMES.items():
        new = new.replace(old, new_name)
    if new != text:
        path.write_text(new, encoding="utf-8")

print("fixed")
