"""
Genera los documentos D1-D5 como imágenes que simulan papeles escaneados (spec 04, R1).

Las imágenes no tienen capa de texto: extraer su contenido requiere OCR. El texto de referencia se
guarda aparte (ocr/referencia/) solo para medir la calidad del OCR.

Uso (desde la raíz del repositorio):
    uv run python -m ocr.generar_documentos
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ocr.contenido import CLINICA, DIRECCION, DOCUMENTOS, PIE, TELEFONO, archivo

CARPETA = Path(__file__).parent
SALIDA_IMAGENES = CARPETA / "documentos"
SALIDA_REFERENCIA = CARPETA / "referencia"

# Página tamaño carta a 150 ppp
ANCHO, ALTO_MIN = 1275, 1650
MARGEN = 100
PAPEL = (241, 236, 224)
TINTA = (32, 32, 40)
LINEA_TABLA = (120, 120, 120)
FONDO_CABECERA_TABLA = (222, 218, 208)

FUENTES = Path("/System/Library/Fonts/Supplemental")


def fuente(estilo: str, tamano: int) -> ImageFont.FreeTypeFont:
    nombres = {"normal": "Arial.ttf", "negrita": "Arial Bold.ttf", "cursiva": "Arial Italic.ttf"}
    try:
        return ImageFont.truetype(str(FUENTES / nombres[estilo]), tamano)
    except OSError:  # fuera de macOS
        return ImageFont.truetype("DejaVuSans.ttf", tamano)


ESTILOS = {
    "clinica": fuente("negrita", 34),
    "membrete": fuente("normal", 19),
    "titulo": fuente("negrita", 34),
    "subtitulo": fuente("negrita", 25),
    "parrafo": fuente("normal", 23),
    "lista": fuente("normal", 23),
    "nota": fuente("cursiva", 20),
    "tabla": fuente("normal", 21),
    "tabla_cabecera": fuente("negrita", 21),
    "pie": fuente("cursiva", 18),
}


def partir(texto: str, letra: ImageFont.FreeTypeFont, ancho: int) -> list[str]:
    """Reparte el texto en líneas que caben en `ancho` píxeles."""
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if letra.getlength(prueba) <= ancho:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    return lineas + [actual] if actual else lineas


class Pagina:
    """Dibuja bloques de arriba abajo y acumula el texto de referencia."""

    def __init__(self, alto: int):
        self.img = Image.new("RGB", (ANCHO, alto), PAPEL)
        self.dibujo = ImageDraw.Draw(self.img)
        self.y = MARGEN
        self.referencia: list[str] = []

    def texto(self, contenido: str, estilo: str, x: int = MARGEN, ancho: int = ANCHO - 2 * MARGEN,
              interlineado: float = 1.35, prefijo: str = "") -> None:
        letra = ESTILOS[estilo]
        alto_linea = int(letra.size * interlineado)
        sangria = int(letra.getlength(prefijo)) if prefijo else 0
        for i, linea in enumerate(partir(contenido, letra, ancho - sangria)):
            if prefijo and i == 0:
                self.dibujo.text((x, self.y), prefijo, font=letra, fill=TINTA)
            self.dibujo.text((x + sangria, self.y), linea, font=letra, fill=TINTA)
            self.y += alto_linea
        self.referencia.append(f"{prefijo}{contenido}".strip())

    def membrete(self) -> None:
        self.texto(CLINICA, "clinica")
        self.texto(f"{DIRECCION} · Tel. {TELEFONO}", "membrete")
        self.y += 6
        self.dibujo.line([(MARGEN, self.y), (ANCHO - MARGEN, self.y)], fill=TINTA, width=3)
        self.y += 28

    def tabla(self, cabeceras: list[str], filas: list[list[str]]) -> None:
        ancho_total = ANCHO - 2 * MARGEN
        # Ancho de cada columna proporcional a su texto más largo
        largos = [max(ESTILOS["tabla_cabecera"].getlength(c), *(ESTILOS["tabla"].getlength(f[i]) for f in filas))
                  for i, c in enumerate(cabeceras)]
        anchos = [int(ancho_total * largo / sum(largos)) for largo in largos]
        alto_fila, relleno = 44, 12
        for n, fila in enumerate([cabeceras, *filas]):
            x = MARGEN
            estilo = "tabla_cabecera" if n == 0 else "tabla"
            if n == 0:
                self.dibujo.rectangle([MARGEN, self.y, MARGEN + sum(anchos), self.y + alto_fila],
                                      fill=FONDO_CABECERA_TABLA)
            for celda, ancho in zip(fila, anchos):
                self.dibujo.rectangle([x, self.y, x + ancho, self.y + alto_fila], outline=LINEA_TABLA, width=2)
                self.dibujo.text((x + relleno, self.y + 10), celda, font=ESTILOS[estilo], fill=TINTA)
                x += ancho
            self.referencia.append(" ".join(fila))
            self.y += alto_fila
        self.y += 20

    def bloque(self, tipo: str, *datos) -> None:
        if tipo == "titulo":
            self.texto(datos[0], "titulo")
            self.y += 10
        elif tipo == "subtitulo":
            self.y += 12
            self.texto(datos[0], "subtitulo")
        elif tipo == "parrafo":
            self.texto(datos[0], "parrafo")
            self.y += 8
        elif tipo == "lista":
            for item in datos[0]:
                self.texto(item, "lista", x=MARGEN + 20, ancho=ANCHO - 2 * MARGEN - 20, prefijo="- ")
            self.y += 8
        elif tipo == "tabla":
            self.tabla(*datos)
        elif tipo == "nota":
            self.texto(datos[0], "nota")

    def pie(self, alto: int) -> None:
        letra = ESTILOS["pie"]
        self.dibujo.text(((ANCHO - letra.getlength(PIE)) / 2, alto - MARGEN + 20), PIE, font=letra, fill=TINTA)
        self.referencia.append(PIE)


def maquetar(bloques: list, alto: int) -> Pagina:
    pagina = Pagina(alto)
    pagina.membrete()
    for bloque in bloques:
        pagina.bloque(*bloque)
    return pagina


def escanear(img: Image.Image, semilla: int) -> Image.Image:
    """Simula un escaneo: pérdida de nitidez, inclinación, ruido y desenfoque. Reproducible por semilla."""
    azar = np.random.default_rng(semilla)
    ancho, alto = img.size
    img = img.resize((int(ancho * 0.8), int(alto * 0.8)), Image.BILINEAR).resize((ancho, alto), Image.BILINEAR)
    angulo = float(azar.uniform(0.5, 1.5)) * (1 if semilla % 2 else -1)
    img = img.rotate(angulo, resample=Image.BICUBIC, fillcolor=PAPEL)
    pixeles = np.asarray(img).astype(np.float32)
    pixeles += azar.normal(0, 9, pixeles.shape[:2])[..., None]
    img = Image.fromarray(np.clip(pixeles, 0, 255).astype(np.uint8))
    return img.filter(ImageFilter.GaussianBlur(0.6))


def generar() -> None:
    SALIDA_IMAGENES.mkdir(exist_ok=True)
    SALIDA_REFERENCIA.mkdir(exist_ok=True)
    for semilla, (doc_id, (titulo, bloques)) in enumerate(DOCUMENTOS.items(), start=1):
        # Primera pasada para medir el alto que necesita el contenido
        alto = max(ALTO_MIN, maquetar(bloques, 10_000).y + 2 * MARGEN)
        pagina = maquetar(bloques, alto)
        pagina.pie(alto)

        nombre = archivo(doc_id)
        # JPEG como un escáner real: pesa ~10 veces menos que PNG con el ruido y añade artefactos de compresión
        escanear(pagina.img, semilla).save(SALIDA_IMAGENES / f"{nombre}.jpg", quality=80)
        (SALIDA_REFERENCIA / f"{nombre}.txt").write_text(
            "\n".join([CLINICA, f"{DIRECCION} · Tel. {TELEFONO}", *pagina.referencia[2:]]) + "\n", encoding="utf-8")
        print(f"  {nombre}.jpg  ({ANCHO}x{alto})  {titulo}")


if __name__ == "__main__":
    print("Generando documentos sintéticos...")
    generar()
