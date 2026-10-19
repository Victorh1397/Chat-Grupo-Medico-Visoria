"""
Incorpora al repositorio un export del agente de Dialogflow sin secretos.

El export (⚙️ -> Export and Import -> Export as ZIP) incluye la configuración de Fulfillment con el
valor de la cabecera X-Visoria-Token. Este script lo sustituye por un marcador y escribe:
    agente/                     export descomprimido (se versiona)
    entrega/agente_dialogflow.zip   ZIP de entrega

Uso:
    uv run python scripts/preparar_export.py ~/Downloads/Grupo-Medico-Visoria.zip

Quien importe el ZIP debe poner su propio token en Fulfillment (README).
"""

import io
import json
import shutil
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CARPETA = RAIZ / "agente"
ZIP_ENTREGA = RAIZ / "entrega" / "agente_dialogflow.zip"
CABECERAS_SECRETAS = {"x-visoria-token"}
MARCADOR = "<WEBHOOK_TOKEN>"


def limpiar_agent_json(contenido: bytes) -> tuple[bytes, list[str]]:
    agente = json.loads(contenido)
    cabeceras = agente.get("webhook", {}).get("headers", {})
    limpiadas = [k for k in cabeceras if k.lower() in CABECERAS_SECRETAS]
    for clave in limpiadas:
        cabeceras[clave] = MARCADOR
    return (json.dumps(agente, indent=2, ensure_ascii=False) + "\n").encode(), limpiadas


def main(origen: Path) -> None:
    salida = io.BytesIO()
    with zipfile.ZipFile(origen) as entrada, zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as limpio:
        for item in entrada.infolist():
            datos = entrada.read(item.filename)
            if item.filename == "agent.json":
                datos, limpiadas = limpiar_agent_json(datos)
                print(f"Cabeceras sustituidas por {MARCADOR}: {limpiadas or 'ninguna'}")
            limpio.writestr(item.filename, datos)

    ZIP_ENTREGA.parent.mkdir(exist_ok=True)
    ZIP_ENTREGA.write_bytes(salida.getvalue())
    shutil.rmtree(CARPETA, ignore_errors=True)
    with zipfile.ZipFile(ZIP_ENTREGA) as limpio:
        limpio.extractall(CARPETA)
    print(f"Escrito {CARPETA.relative_to(RAIZ)}/ y {ZIP_ENTREGA.relative_to(RAIZ)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]).expanduser())
