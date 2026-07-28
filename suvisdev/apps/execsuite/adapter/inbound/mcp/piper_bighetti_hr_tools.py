from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Piper")

@mcp.tool("/myself")
async def introduce_myself() -> str:
    return "파이퍼 HR 빅헤티 입니다"
