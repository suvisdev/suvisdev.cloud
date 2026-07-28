from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Piper")

@mcp.tool("/myself")
async def introduce_myself() -> str:
    return "파이퍼 CEO 헨드릭스 입니다"