from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from dispatch.adapter.inbound.api.schemas.receive_schema import (
    ReceiveItemSchema,
    ReceiveRequestSchema,
)
from dispatch.app.dtos.receive_dto import ReceiveSaveCommand
from dispatch.app.ports.input.receive_use_case import ReceiveUseCase
from dispatch.app.ports.output.dispatch_errors import DispatchError
from dispatch.dependencies.receive_provider import get_receive_use_case

receive_router = APIRouter(prefix="/receive", tags=["dispatch-receive"])


@receive_router.post("", response_model=ReceiveItemSchema)
async def receive_item(
    req: ReceiveRequestSchema,
    use_case: ReceiveUseCase = Depends(get_receive_use_case),
) -> ReceiveItemSchema:
    try:
        item = await use_case.save(
            ReceiveSaveCommand(sender=req.sender, subject=req.subject, body=req.body)
        )
    except DispatchError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return ReceiveItemSchema(
        id=item.id,
        sender=item.sender,
        subject=item.subject,
        body=item.body,
        received_at=item.received_at,
    )

    # 여기에 들어오면 로그를 작성해줘.
    # 여기에 들어오면 텔레그램으로 전송해줘


@receive_router.get("", response_model=list[ReceiveItemSchema])
async def list_receive(
    limit: int = Query(default=50, le=200),
    use_case: ReceiveUseCase = Depends(get_receive_use_case),
) -> list[ReceiveItemSchema]:
    items = await use_case.list_all(limit)
    return [
        ReceiveItemSchema(
            id=i.id, sender=i.sender, subject=i.subject, body=i.body, received_at=i.received_at
        )
        for i in items
    ]


@receive_router.delete("/{item_id}", status_code=204)
async def delete_receive(
    item_id: int,
    use_case: ReceiveUseCase = Depends(get_receive_use_case),
) -> Response:
    await use_case.delete(item_id)
    return Response(status_code=204)
