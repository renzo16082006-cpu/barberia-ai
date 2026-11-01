"""Cliente de prueba: hace lo mismo que haría Claude con el servidor."""
import asyncio
from pprint import pprint

from fastmcp import Client

from server import mcp


async def main():
    async with Client(mcp) as client:
        print("=== Tools disponibles ===")
        for tool in await client.list_tools():
            print(f"- {tool.name}: {tool.description}")

        for fecha in ["2026-11-03", "2026-10-30", "2026-12-25"]:
            print(f"\n=== citas_del_dia({fecha}) ===")
            resultado = await client.call_tool("citas_del_dia", {"fecha": fecha})
            pprint(resultado.data)


asyncio.run(main())
