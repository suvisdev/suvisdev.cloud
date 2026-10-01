"""H5 Gate 검증용 MCP 클라이언트 — image_classifier_mcp_server를 stdio로 구동해
tool 목록 확인 + classify_image 호출까지 1회 실행한다.

Usage (suvisdev 폴더에서, 컨테이너 내부):
  python scripts/test_mcp_classifier_client.py <샘플 이미지 경로>
"""

from __future__ import annotations

import asyncio
import base64
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_BACKEND = Path(__file__).resolve().parents[1]


async def main() -> None:
    image_path = sys.argv[1]
    image_b64 = base64.b64encode(Path(image_path).read_bytes()).decode("ascii")

    server_params = StdioServerParameters(
        command="python3",
        args=["-m", "ontology.adapter.inbound.mcp.image_classifier_mcp_server"],
        cwd=str(_BACKEND),
        env={
            "PYTHONPATH": f"{_BACKEND}:{_BACKEND / 'apps'}",
            "INFERENCE_URL": "http://localhost:8000",
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print("tools:", tool_names)
            assert "classify_image" in tool_names, "classify_image tool이 목록에 없음"
            assert "list_supported_classes" in tool_names, (
                "list_supported_classes tool이 목록에 없음"
            )

            classes_result = await session.call_tool("list_supported_classes", {})
            print("list_supported_classes ->", classes_result.content[0].text)

            classify_result = await session.call_tool("classify_image", {"image_b64": image_b64})
            print("classify_image ->", classify_result.content[0].text)

    print("GATE_H5_PASS")


if __name__ == "__main__":
    asyncio.run(main())
