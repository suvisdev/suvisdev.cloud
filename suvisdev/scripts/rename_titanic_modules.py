"""Titanic 모듈 파일명을 schemas 접두·접미사 규칙으로 일괄 생성."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "apps" / "titanic"

MODULES = [
    {
        "base": "crew_andrews_architect",
        "old": "andrews_blueprint",
        "use_case": "AndrewsBlueprintUseCase",
        "interactor": "AndrewsBlueprintInteractor",
        "repository": "AndrewsBlueprintRepository",
        "pg": "AndrewsBlueprintPgRepository",
        "method": "get_blueprint",
        "handler": "get_blueprint",
        "path": "/blueprint",
        "prefix": "/api/titanic/andrews",
        "tags": "andrews",
        "response": "int",
        "returns": "0",
        "dep_fn": "get_andrews_blueprint",
        "router_var": "crew_andrews_architect_router",
    },
    {
        "base": "passenger_cal_tester",
        "old": "cal_pistol",
        "use_case": "CalPistolUseCase",
        "interactor": "CalPistolInteractor",
        "repository": "CalPistolRepository",
        "pg": "CalPistolPgRepository",
        "method": "get_pistol",
        "handler": "get_pistol",
        "path": "/pistol",
        "prefix": "/api/titanic/pistol",
        "tags": "pistol",
        "response": "None",
        "returns": "None",
        "dep_fn": "get_cal_pistol",
        "router_var": "passenger_cal_tester_router",
    },
    {
        "base": "crew_hartley_violin",
        "old": "hartley_violin",
        "use_case": "HartleyViolinUseCase",
        "interactor": "HartleyViolinInteractor",
        "repository": "HartleyViolinRepository",
        "pg": "HartleyViolinPgRepository",
        "method": "get_violin",
        "handler": "get_violin",
        "path": "/violin",
        "prefix": "/api/titanic/violin",
        "tags": "violin",
        "response": "int",
        "returns": "0",
        "dep_fn": "get_hartley_violin",
        "router_var": "crew_hartley_violin_router",
    },
    {
        "base": "passenger_isidor_couple",
        "old": "isidor_bed",
        "use_case": "IsidorBedUseCase",
        "interactor": "IsidorBedInteractor",
        "repository": "IsidorBedRepository",
        "pg": "IsidorBedPgRepository",
        "method": "get_bed",
        "handler": "get_bed",
        "path": "/bed",
        "prefix": "/api/titanic/bed",
        "tags": "bed",
        "response": "int",
        "returns": "0",
        "dep_fn": "get_isidor_bed",
        "router_var": "passenger_isidor_couple_router",
    },
    {
        "base": "passenger_jack_trainer",
        "old": "jack_sketch",
        "use_case": "JackSketchUseCase",
        "interactor": "JackSketchInteractor",
        "repository": "JackSketchRepository",
        "pg": "JackSketchPgRepository",
        "method": "get_sketch",
        "handler": "get_sketch",
        "path": "/sketch",
        "prefix": "/api/titanic/sketch",
        "tags": "sketch",
        "response": "int",
        "returns": "0",
        "dep_fn": "get_jack_sketch",
        "router_var": "passenger_jack_trainer_router",
    },
    {
        "base": "passenger_rose_model",
        "old": "rose_diamond",
        "use_case": "RoseDiamondUseCase",
        "interactor": "RoseDiamondInteractor",
        "repository": "RoseDiamondRepository",
        "pg": "RoseDiamondPgRepository",
        "method": "get_diamond",
        "handler": "get_diamond",
        "path": "/diamond",
        "prefix": "/api/titanic/diamond",
        "tags": "diamond",
        "response": "int",
        "returns": "0",
        "dep_fn": "get_rose_diamond",
        "router_var": "passenger_rose_model_router",
    },
    {
        "base": "passenger_ruth_validation",
        "old": "ruth_corset",
        "use_case": "RuthCorsetUseCase",
        "interactor": "RuthCorsetInteractor",
        "repository": "RuthCorsetRepository",
        "pg": "RuthCorsetPgRepository",
        "method": "get_corset",
        "handler": "get_corset",
        "path": "/corset",
        "prefix": "/api/titanic/corset",
        "tags": "corset",
        "response": "int",
        "returns": "0",
        "dep_fn": "get_ruth_corset",
        "router_var": "passenger_ruth_validation_router",
    },
    {
        "base": "crew_smith_captain",
        "old": "smith_captain",
        "use_case": "SmithCaptainUseCase",
        "interactor": "SmithCaptainInteractor",
        "repository": "SmithCaptainRepository",
        "pg": "SmithCaptainPgRepository",
        "method": "get_captain",
        "handler": "get_captain",
        "path": "/captain",
        "prefix": "/api/titanic/captain",
        "tags": "captain",
        "response": "int",
        "returns": "0",
        "dep_fn": "get_smith_captain",
        "router_var": "crew_smith_captain_router",
    },
    {
        "base": "crew_lowe_boat",
        "old": None,
        "use_case": "LoweBoatUseCase",
        "interactor": "LoweBoatInteractor",
        "repository": "LoweBoatRepository",
        "pg": "LoweBoatPgRepository",
        "method": "get_boat",
        "handler": "get_boat",
        "path": "/boat",
        "prefix": "/api/titanic/boat",
        "tags": "boat",
        "response": "int",
        "returns": "0",
        "dep_fn": "get_lowe_boat",
        "router_var": "crew_lowe_boat_router",
    },
    {
        "base": "passenger_molly_scaler",
        "old": None,
        "use_case": "MollyScalerUseCase",
        "interactor": "MollyScalerInteractor",
        "repository": "MollyScalerRepository",
        "pg": "MollyScalerPgRepository",
        "method": "get_scaler",
        "handler": "get_scaler",
        "path": "/scaler",
        "prefix": "/api/titanic/scaler",
        "tags": "scaler",
        "response": "int",
        "returns": "0",
        "dep_fn": "get_molly_scaler",
        "router_var": "passenger_molly_scaler_router",
    },
]


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    for m in MODULES:
        base = m["base"]
        schema_class = "".join(part.capitalize() for part in base.split("_")) + "Schema"
        ret_ann = " -> None" if m["response"] == "None" else " -> int"
        pg_ret_stmt = "return None" if m["response"] == "None" else f"return {m['returns']}"
        resp_model = "" if m["response"] == "None" else f", response_model={m['response']}"

        write(
            ROOT / f"adapter/inbound/api/schemas/{base}_schema.py",
            f'''from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class {schema_class}(BaseModel):
    """{base} schema (extend later)."""

    model_config = ConfigDict(extra="allow")
''',
        )

        write(
            ROOT / f"app/ports/input/{base}_use_case.py",
            f'''from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class {m["use_case"]}(ABC):
    """{base} input port."""

    @abstractmethod
    async def {m["method"]}(self, request: dict[str, Any]){ret_ann}:
        pass
''',
        )

        write(
            ROOT / f"app/ports/output/{base}_repository.py",
            f'''from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class {m["repository"]}(ABC):
    """{base} output port."""

    @abstractmethod
    async def {m["method"]}(self, request: dict[str, Any]){ret_ann}:
        pass
''',
        )

        write(
            ROOT / f"app/use_cases/{base}_interactor.py",
            f'''from __future__ import annotations

import logging
from typing import Any

from titanic.app.ports.input.{base}_use_case import {m["use_case"]}
from titanic.app.ports.output.{base}_repository import {m["repository"]}

logger = logging.getLogger(__name__)


class {m["interactor"]}({m["use_case"]}):
    def __init__(self, repository: {m["repository"]}) -> None:
        self._repository = repository

    async def {m["method"]}(self, request: dict[str, Any]){ret_ann}:
        logger.info("[%s] %s", "{m['interactor']}", "{m['method']}")
        return await self._repository.{m["method"]}(request)
''',
        )

        write(
            ROOT / f"adapter/outbound/pg/{base}_pg_repository.py",
            f'''from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from titanic.app.ports.output.{base}_repository import {m["repository"]}

logger = logging.getLogger(__name__)


class {m["pg"]}({m["repository"]}):
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def {m["method"]}(self, request: dict[str, Any]){ret_ann}:
        logger.info("[%s] %s request=%s", "{m['pg']}", "{m['method']}", request)
        {pg_ret_stmt}
''',
        )

        write(
            ROOT / f"dependencies/{base}.py",
            f'''from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_db
from fastapi import Depends

from titanic.adapter.outbound.pg.{base}_pg_repository import {m["pg"]}
from titanic.app.ports.input.{base}_use_case import {m["use_case"]}
from titanic.app.ports.output.{base}_repository import {m["repository"]}
from titanic.app.use_cases.{base}_interactor import {m["interactor"]}


def {m["dep_fn"]}(db: AsyncSession = Depends(get_db)) -> {m["use_case"]}:
    repository: {m["repository"]} = {m["pg"]}(session=db)
    return {m["interactor"]}(repository=repository)
''',
        )

        write(
            ROOT / f"adapter/inbound/api/v1/{base}_router.py",
            f'''from __future__ import annotations

from fastapi import APIRouter, Depends

from titanic.app.ports.input.{base}_use_case import {m["use_case"]}
from titanic.dependencies.{base}_provider import {m["dep_fn"]}

{m["router_var"]} = APIRouter(prefix="{m["prefix"]}", tags=["{m["tags"]}"])


@{m["router_var"]}.get("{m["path"]}"{resp_model})
async def {m["handler"]}(
    use_case: {m["use_case"]} = Depends({m["dep_fn"]}),
) -> {m["response"]}:
    return await use_case.{m["method"]}({{}})
''',
        )

        entity_kind = "crew" if base.startswith("crew_") else "passenger"
        write(
            ROOT / f"domain/entities/{base}_entity.py",
            f'"""{base}_schema {entity_kind} entity (extend later)."""\n',
        )

        if m["old"]:
            for sub, name in [
                ("adapter/inbound/api/v1", f"{m['old']}_router.py"),
                ("app/ports/input", f"{m['old']}_use_case.py"),
                ("app/ports/output", f"{m['old']}_repository.py"),
                ("app/use_cases", f"{m['old']}_interactor.py"),
                ("adapter/outbound/pg", f"{m['old']}_pg_repository.py"),
            ]:
                path = ROOT / sub / name
                if path.exists():
                    path.unlink()

    routers = [
        "crew_james_director_router",
        "crew_walter_roaster_router",
        "crew_andrews_architect_router",
        "passenger_cal_tester_router",
        "crew_hartley_violin_router",
        "passenger_isidor_couple_router",
        "passenger_jack_trainer_router",
        "passenger_rose_model_router",
        "passenger_ruth_validation_router",
        "crew_smith_captain_router",
        "crew_lowe_boat_router",
        "passenger_molly_scaler_router",
    ]
    imports = "\n".join(
        f"from titanic.adapter.inbound.api.v1.{r} import {r}" for r in routers
    )
    includes = "\n".join(f"titanic_router.include_router({r})" for r in routers)
    write(
        ROOT / "adapter/inbound/api/__init__.py",
        f'''from fastapi import APIRouter

{imports}

titanic_router = APIRouter(prefix="/api/titanic", tags=["titanic"])
{includes}

__all__ = ["titanic_router"]
''',
    )

    # remove legacy duplicate entity name
    legacy_entity = ROOT / "domain/entities/passenger_rose_model_entity.py"
    if legacy_entity.exists():
        legacy_entity.unlink()

    print(f"generated {len(MODULES)} modules")


if __name__ == "__main__":
    main()
