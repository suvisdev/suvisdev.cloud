"""어시스턴트 Entity."""

from __future__ import annotations

from dataclasses import dataclass

from mova.domain.value_objects.platform_assistants_vo import AssistantSlug


@dataclass(frozen=True)
class AssistantEntity:
    id: int
    slug: AssistantSlug
    display_name: str
    avatar_url: str
    system_prompt: str
    default_model: str
    is_active: bool

    @classmethod
    def from_orm(cls, row: object) -> AssistantEntity:
        return cls(
            id=row.id,
            slug=AssistantSlug(row.slug),
            display_name=row.display_name,
            avatar_url=row.avatar_url or "",
            system_prompt=row.system_prompt or "",
            default_model=row.default_model or "flash15",
            is_active=bool(row.is_active),
        )

    def is_active_assistant(self) -> bool:
        return self.is_active
