from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Piper")

@mcp.tool("/myself")
async def introduce_myself() -> str:
    return "파이퍼 대시 디네시 입니다"
