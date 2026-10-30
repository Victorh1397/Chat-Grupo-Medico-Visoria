"""
Genera docs/arquitectura.png, el diagrama de arquitectura del README (spec 99).

Se dibuja con Pillow para que el diagrama sea reproducible y se pueda versionar el código que lo produce:
    uv run python docs/generar_diagrama.py

Las coordenadas son "lógicas" (lienzo de 1800 x 1140) y se multiplican por ESCALA para obtener una imagen nítida.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SALIDA = Path(__file__).resolve().parent / "arquitectura.png"
ANCHO, ALTO = 1800, 1140
ESCALA = 2

# Colores por tipo de componente: (relleno, borde)
CANAL = ("#E3EEFB", "#2F6DB5")
DIALOGFLOW = ("#FDEBD8", "#D9822B")
WEBHOOK = ("#E2F4E6", "#2E8B48")
LLM = ("#EFE5FA", "#7B4DB8")
OFFLINE = ("#EEEFF1", "#6B7280")
FICHERO = ("#FFF7D6", "#B08900")
TEXTO = "#1F2937"
TEXTO_SUAVE = "#4B5563"
FLECHA = "#374151"

FUENTES = {
    False: ["/System/Library/Fonts/Supplemental/Arial.ttf", "DejaVuSans.ttf"],
    True: ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "DejaVuSans-Bold.ttf"],
}


def fuente(tamano: int, negrita: bool = False) -> ImageFont.FreeTypeFont:
    for ruta in FUENTES[negrita]:
        try:
            return ImageFont.truetype(ruta, tamano * ESCALA)
        except OSError:
            continue
    return ImageFont.load_default(tamano * ESCALA)


def s(*valores: float) -> list[float]:
    return [v * ESCALA for v in valores]


class Lienzo:
    def __init__(self) -> None:
        self.imagen = Image.new("RGB", (ANCHO * ESCALA, ALTO * ESCALA), "white")
        self.d = ImageDraw.Draw(self.imagen)

    def texto(self, x: float, y: float, texto: str, tamano: int = 16, negrita: bool = False,
              color: str = TEXTO, ancla: str = "la") -> None:
        self.d.text(s(x, y), texto, font=fuente(tamano, negrita), fill=color, anchor=ancla)

    def ancho_texto(self, texto: str, tamano: int, negrita: bool = False) -> float:
        return self.d.textlength(texto, font=fuente(tamano, negrita)) / ESCALA

    def caja(self, x1: float, y1: float, x2: float, y2: float, colores: tuple[str, str], titulo: str,
             lineas: list[str] = (), tamano_titulo: int = 20, tamano: int = 16, centrado: bool = False) -> None:
        relleno, borde = colores
        self.d.rounded_rectangle(s(x1, y1, x2, y2), radius=12 * ESCALA, fill=relleno, outline=borde, width=3 * ESCALA)
        # Comprobación: ningún texto se sale de su caja
        for linea, tam, negrita in [(titulo, tamano_titulo, True)] + [(lin, tamano, False) for lin in lineas]:
            if self.ancho_texto(linea, tam, negrita) > x2 - x1 - 28:
                raise ValueError(f"El texto no cabe en la caja: {linea!r}")
        if centrado:
            alto = tamano_titulo + len(lineas) * (tamano + 8)
            y = (y1 + y2) / 2 - alto / 2
            self.texto((x1 + x2) / 2, y, titulo, tamano_titulo, True, borde, "ma")
            for i, linea in enumerate(lineas):
                self.texto((x1 + x2) / 2, y + tamano_titulo + 8 + i * (tamano + 8), linea, tamano, ancla="ma")
        else:
            self.texto(x1 + 16, y1 + 16, titulo, tamano_titulo, True, borde)
            for i, linea in enumerate(lineas):
                self.texto(x1 + 16, y1 + 24 + tamano_titulo + i * (tamano + 11), linea, tamano)

    def linea(self, puntos: list[tuple[float, float]], color: str = FLECHA, discontinua: bool = False,
              grosor: float = 2.5) -> None:
        for (xa, ya), (xb, yb) in zip(puntos, puntos[1:]):
            if not discontinua:
                self.d.line(s(xa, ya, xb, yb), fill=color, width=round(grosor * ESCALA))
                continue
            largo = ((xb - xa) ** 2 + (yb - ya) ** 2) ** 0.5
            trazo, hueco = 10, 7
            t = 0.0
            while t < largo:
                fin = min(t + trazo, largo)
                self.d.line(s(xa + (xb - xa) * t / largo, ya + (yb - ya) * t / largo,
                              xa + (xb - xa) * fin / largo, ya + (yb - ya) * fin / largo),
                            fill=color, width=round(grosor * ESCALA))
                t += trazo + hueco

    def punta(self, desde: tuple[float, float], hasta: tuple[float, float], color: str = FLECHA) -> None:
        (xa, ya), (xb, yb) = desde, hasta
        largo = ((xb - xa) ** 2 + (yb - ya) ** 2) ** 0.5
        ux, uy = (xb - xa) / largo, (yb - ya) / largo
        tam, abertura = 14, 7
        base = (xb - ux * tam, yb - uy * tam)
        self.d.polygon([tuple(s(xb, yb)), tuple(s(base[0] - uy * abertura, base[1] + ux * abertura)),
                        tuple(s(base[0] + uy * abertura, base[1] - ux * abertura))], fill=color)

    def flecha(self, puntos: list[tuple[float, float]], doble: bool = False, discontinua: bool = False,
               color: str = FLECHA) -> None:
        self.linea(puntos, color, discontinua)
        self.punta(puntos[-2], puntos[-1], color)
        if doble:
            self.punta(puntos[1], puntos[0], color)

    def etiqueta(self, x: float, y: float, lineas: list[str], tamano: int = 14, ancla: str = "ma",
                 color: str = TEXTO_SUAVE) -> None:
        for i, linea in enumerate(lineas):
            self.texto(x, y + i * (tamano + 5), linea, tamano, color=color, ancla=ancla)

    def rectangulo_discontinuo(self, x1: float, y1: float, x2: float, y2: float, color: str) -> None:
        esquinas = [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]
        self.linea(esquinas, color, discontinua=True, grosor=2)


def dibujar() -> Image.Image:
    c = Lienzo()

    c.texto(ANCHO / 2, 28, "Vicky · Arquitectura del asistente de Grupo Médico Visoria", 32, True, ancla="ma")
    c.texto(ANCHO / 2, 74, "Canales  →  Dialogflow ES  →  webhook FastAPI  →  Gemini     ·     línea offline de OCR",
            18, color=TEXTO_SUAVE, ancla="ma")

    # Canales de entrada
    c.caja(40, 150, 380, 270, CANAL, "Usuario por voz",
           ["voz/cliente_voz.py", "micrófono · fin por silencio", "reproduce el audio de Vicky"])
    c.caja(40, 300, 380, 400, CANAL, "Telegram", ["integración nativa de Dialogflow", "menús con botones"])
    c.caja(40, 430, 380, 510, CANAL, "Simulador de la consola", ["texto (pruebas)"])

    # Dialogflow ES
    c.caja(580, 150, 1120, 510, DIALOGFLOW, "Dialogflow ES · agente Grupo-Medico-Visoria", [
        "• STT nativo: audio → texto",
        "• 13 intenciones (12 llaman al webhook)",
        "• Entidades",
        "   (@cedula con regex, @especialidad, @nacionalidad)",
        "• Contextos ctx_cita_en_curso y ctx_recogida_cita",
        "• Follow-ups sí / no de la confirmación",
        "• Respuestas estáticas de reserva si el webhook falla",
        "• TTS nativo: texto o SSML → audio",
    ], tamano=17)

    c.flecha([(380, 210), (580, 210)], doble=True)
    c.etiqueta(480, 168, ["detect_intent", "audio → texto + audio"])
    c.flecha([(380, 350), (580, 350)], doble=True)
    c.etiqueta(480, 308, ["mensajes", "y botones"])
    c.flecha([(380, 470), (580, 470)], doble=True)
    c.etiqueta(480, 445, ["texto"])

    # Leyenda
    c.texto(1340, 150, "Leyenda", 20, True)
    for i, (colores, nombre) in enumerate([
        (CANAL, "Canales de entrada"),
        (DIALOGFLOW, "Dialogflow ES (configurado en la consola)"),
        (WEBHOOK, "Webhook (código propio, Python)"),
        (LLM, "LLM (Gemini)"),
        (OFFLINE, "Línea offline (OCR, se ejecuta una vez)"),
        (FICHERO, "Fichero generado"),
    ]):
        y = 190 + i * 34
        c.d.rounded_rectangle(s(1340, y, 1368, y + 22), radius=4 * ESCALA, fill=colores[0], outline=colores[1],
                              width=2 * ESCALA)
        c.texto(1380, y + 2, nombre, 16)
    y = 190 + 6 * 34 + 6
    c.flecha([(1340, y + 10), (1400, y + 10)])
    c.texto(1412, y + 1, "petición en tiempo real (≤ 5 s por turno)", 16)
    c.flecha([(1340, y + 44), (1400, y + 44)], discontinua=True)
    c.texto(1412, y + 35, "lectura o escritura de fichero", 16)

    # Webhook
    c.caja(580, 620, 1120, 880, WEBHOOK, "Webhook FastAPI · POST /webhook", [
        "• Validación de la cédula con regex (dos niveles)",
        "• Agenda: disponibilidad, reserva y código de cita",
        "• Respuestas dinámicas y SSML (solo canal de voz)",
        "• Transferencia a recepción y botones de Telegram",
        "• Base vectorial FAISS: fragmentos de la pregunta",
        "• Respuesta de reserva si algo falla",
    ], tamano=17)

    c.flecha([(850, 510), (850, 620)], doble=True)
    c.etiqueta(870, 534, ["ngrok (HTTPS) · cabecera X-Visoria-Token", "Dialogflow espera como máximo 5 s"],
               tamano=15, ancla="la")

    # Gemini
    c.caja(1340, 620, 1760, 880, LLM, "Gemini 3.5 Flash-Lite", [
        "• Responde solo con los documentos",
        "• Si el dato no está: NO_DISPONIBLE",
        "   → «No tengo esa información…»",
        "• Límite de 4 s en el webhook",
        "• Petición de respaldo a los 1,5 s",
    ], tamano=17)

    c.flecha([(1120, 700), (1340, 700)])
    c.etiqueta(1230, 655, ["pregunta + fragmentos", "(o texto completo)"])
    c.flecha([(1340, 800), (1120, 800)])
    c.etiqueta(1230, 757, ["respuesta breve", "o NO_DISPONIBLE"])

    # Cola de recepción
    c.caja(40, 700, 380, 800, FICHERO, "logs/transferencias.jsonl", ["cola de recepción: caso + resumen"],
           tamano_titulo=18)
    c.flecha([(580, 750), (380, 750)], discontinua=True)
    c.etiqueta(480, 722, ["caso"])

    # Línea offline
    c.rectangulo_discontinuo(30, 950, 1770, 1120, OFFLINE[1])
    c.texto(50, 962, "LÍNEA OFFLINE  ·  se ejecuta una vez antes de arrancar, nunca dentro de una petición", 16, True,
            OFFLINE[1])
    pasos = [
        (60, 275, OFFLINE, "webhook/datos.py", ["fuente de los datos"]),
        (304, 519, OFFLINE, "Documentos", ["D1–D5 · JPG escaneados"]),
        (548, 763, OFFLINE, "OCR Tesseract", ["(spa) + preprocesado"]),
        (792, 1007, OFFLINE, "Regex", ["y validación de datos"]),
        (1036, 1251, FICHERO, "documentos.json", ["ocr/salida/ · texto"]),
        (1280, 1495, OFFLINE, "ocr.indexar", ["trocea + embeddings"]),
        (1524, 1739, FICHERO, "indice.json", ["fragmentos y vectores"]),
    ]
    for x1, x2, colores, titulo, lineas in pasos:
        c.caja(x1, 1000, x2, 1095, colores, titulo, lineas, tamano_titulo=18, tamano=15, centrado=True)
    for (_, fin, *_), (inicio, *_) in zip(pasos, pasos[1:]):
        c.flecha([(fin, 1047), (inicio, 1047)])

    c.flecha([(1631, 1000), (1631, 918), (1000, 918), (1000, 880)], discontinua=True)
    c.etiqueta(1300, 896, ["se carga una vez al arrancar el webhook"], tamano=15)

    return c.imagen


if __name__ == "__main__":
    dibujar().save(SALIDA, optimize=True)
    print(f"Diagrama guardado en {SALIDA}")
