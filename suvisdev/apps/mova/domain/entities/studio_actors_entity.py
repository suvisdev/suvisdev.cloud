"""배우/감독 도메인 Entity."""

from __future__ import annotations

from dataclasses import dataclass

from mova.domain.value_objects.studio_actors_vo import ActorName, RoleType


@dataclass(frozen=True)
class ActorEntity:
    """배우·감독 도메인 객체. ORM·Pydantic에 의존하지 않는다."""

    id: int
    name: ActorName
    role_type: RoleType
    profile_photo_url: str

    @classmethod
    def from_orm(cls, orm: object) -> ActorEntity:
        return cls(
            id=orm.id,
            name=ActorName(orm.name),
            role_type=RoleType.from_str(getattr(orm, "role_type", None)),
            profile_photo_url=getattr(orm, "profile_photo_url", "") or "",
        )

    def is_director(self) -> bool:
        return self.role_type == RoleType.DIRECTOR

    def role_label(self) -> str:
        return self.role_type.label_ko()


if __name__ == "__main__":
    from types import SimpleNamespace

    mock = SimpleNamespace(id=1, name="봉준호", role_type="director", profile_photo_url="")
    actor = ActorEntity.from_orm(mock)
    assert actor.is_director()
    assert actor.role_label() == "감독"
    assert str(actor.name) == "봉준호"
    print("studio_actors_entity OK")
