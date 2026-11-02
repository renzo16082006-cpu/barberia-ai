"""Exporta las tools del servidor MCP a evals/tools.json (formato OpenAI) para promptfoo.

Así el eval usa EXACTAMENTE las mismas descripciones y parámetros que ve Claude Desktop.
Si cambias una tool en server.py, vuelve a ejecutar este script.
"""
import asyncio
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "mcp_server"))

from fastmcp import Client  # noqa: E402

from server import mcp  # noqa: E402


async def main():
    async with Client(mcp) as client:
        tools = await client.list_tools()

    salida = [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.input_schema,
            },
        }
        for t in tools
    ]

    destino = RAIZ / "evals" / "tools.json"
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(salida)} tools exportadas a {destino}:")
    for t in salida:
        print(" -", t["function"]["name"])


asyncio.run(main())
