"""Cliente de prueba: hace lo mismo que haría Claude con el servidor."""
import asyncio
from pprint import pprint

from fastmcp import Client

from server import mcp


async def main():
    async with Client(mcp) as client:
        print("=== Tools disponibles ===")
        for tool in await client.list_tools():
            print(f"- {tool.name}")

        for fecha in ["2026-11-03", "2026-10-30", "2026-12-25"]:
            print(f"\n=== citas_del_dia({fecha}) ===")
            resultado = await client.call_tool("citas_del_dia", {"fecha": fecha})
            pprint(resultado.data)

        for nombre in ["pedro", "GOMEZ", "sergi", "'; DROP TABLE clientes; --"]:
            print(f"\n=== buscar_cliente({nombre!r}) ===")
            resultado = await client.call_tool("buscar_cliente", {"nombre": nombre})
            pprint(resultado.data)


asyncio.run(main())


async def prueba_fechas_al_reves():
    async with Client(mcp) as client:
        print("\n=== resumen_ventas(desde=2026-10-31, hasta=2026-10-01) ===")
        try:
            await client.call_tool("resumen_ventas", {"desde": "2026-10-31", "hasta": "2026-10-01"})
            print("FALLO: deberia haber dado error")
        except Exception as e:
            print("OK, error esperado:", e)


asyncio.run(prueba_fechas_al_reves())
