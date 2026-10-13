import json
import os
import sys
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PUERTO = int(os.environ.get("RESPUESTAS_PUERTO", "8412"))
OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODELO = os.environ.get("RESPUESTAS_MODELO", "qwen3:14b")
CARPETA = Path(__file__).parent
FICHA = CARPETA / "ficha.json"
HTML = CARPETA / "index.html"
CAMPOS_FICHA = ("negocio", "sector", "servicios", "horario", "ubicacion", "contacto", "normas", "trato", "firma")
MAX_TEXTO = 8000

ESQUEMA = {
    "type": "object",
    "properties": {
        "respuestas": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {"estilo": {"type": "string"}, "texto": {"type": "string"}},
                "required": ["estilo", "texto"],
            },
        },
        "falta": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["respuestas", "falta"],
}


def leer_ficha() -> dict:
    try:
        datos = json.loads(FICHA.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        datos = {}
    return {c: str(datos.get(c, ""))[:MAX_TEXTO] for c in CAMPOS_FICHA}


def instrucciones(ficha: dict) -> str:
    trato = "de usted" if ficha["trato"] != "tu" else "de tú"
    datos = "\n".join(f"- {c.upper()}: {ficha[c]}" for c in CAMPOS_FICHA if ficha[c] and c not in ("trato", "firma"))
    return f"""Redactas respuestas de WhatsApp para el negocio "{ficha['negocio'] or 'el negocio'}". Las envía una persona del equipo después de revisarlas.

DATOS DEL NEGOCIO (lo único que sabes):
{datos or '- (sin datos todavía)'}

REGLAS:
- Usa solo los datos de arriba. Si el cliente pregunta algo que no está (un precio, una fecha, un dato), no lo inventes: escribe [CONSULTAR: lo que falta] en ese punto y añádelo a "falta".
- Trata al cliente {trato}. Escribe en el idioma del cliente.
- Mensajes cortos, como se escribe por WhatsApp: una idea por párrafo, sin listas largas ni lenguaje de venta.
- Nada de urgencia, descuentos ni promesas que no estén en los datos.
- No des consejo legal, médico ni financiero: ofrece que lo atienda la persona responsable.
- Si hace falta, cierra con una sola pregunta concreta y fácil de contestar.
- Sin emojis.{f' Firma con: {ficha["firma"]}' if ficha['firma'] else ''}

Devuelve tres versiones distintas en "respuestas": estilo "directa", estilo "cercana" y estilo "breve" (una o dos frases)."""


def redactar(conversacion: str, nota: str) -> dict:
    ficha = leer_ficha()
    usuario = f"CONVERSACIÓN CON EL CLIENTE (el último mensaje es el que hay que contestar):\n{conversacion}"
    if nota:
        usuario += f"\n\nINDICACIÓN DE QUIEN RESPONDE: {nota}"
    cuerpo = json.dumps({
        "model": MODELO,
        "messages": [{"role": "system", "content": instrucciones(ficha)}, {"role": "user", "content": usuario}],
        "stream": False,
        "think": False,
        "format": ESQUEMA,
        "options": {"temperature": 0.5, "num_ctx": 8192},
    }).encode()
    pet = urllib.request.Request(f"{OLLAMA}/api/chat", data=cuerpo, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(pet, timeout=300) as r:
        return json.loads(json.load(r)["message"]["content"])


class Manejador(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def responder(self, codigo: int, datos, tipo="application/json"):
        cuerpo = datos if isinstance(datos, bytes) else json.dumps(datos, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", f"{tipo}; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def leer_json(self) -> dict:
        tam = min(int(self.headers.get("Content-Length") or 0), 200_000)
        try:
            datos = json.loads(self.rfile.read(tam) or b"{}")
        except json.JSONDecodeError:
            return {}
        return datos if isinstance(datos, dict) else {}

    def do_GET(self):
        if self.path == "/":
            return self.responder(200, HTML.read_bytes(), "text/html")
        if self.path == "/ficha":
            return self.responder(200, leer_ficha())
        self.responder(404, {"error": "No existe"})

    def do_POST(self):
        # Solo desde la propia página: otra web abierta en el navegador no puede usarlo.
        if self.headers.get("Origin") not in (None, f"http://127.0.0.1:{PUERTO}", f"http://localhost:{PUERTO}"):
            return self.responder(403, {"error": "Origen no permitido"})
        datos = self.leer_json()
        if self.path == "/ficha":
            ficha = {c: str(datos.get(c, ""))[:MAX_TEXTO] for c in CAMPOS_FICHA}
            FICHA.write_text(json.dumps(ficha, ensure_ascii=False, indent=2), encoding="utf-8")
            return self.responder(200, {"ok": True})
        if self.path == "/redactar":
            conversacion = str(datos.get("conversacion", "")).strip()[:MAX_TEXTO]
            if not conversacion:
                return self.responder(400, {"error": "Pega el mensaje del cliente."})
            try:
                return self.responder(200, redactar(conversacion, str(datos.get("nota", "")).strip()[:500]))
            except Exception as e:
                return self.responder(502, {"error": f"No se pudo hablar con Ollama ({OLLAMA}). ¿Está abierto y tiene {MODELO}? Detalle: {e}"})
        self.responder(404, {"error": "No existe"})


def main():
    servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador)
    url = f"http://127.0.0.1:{PUERTO}"
    print(f"Respuestas de WhatsApp en {url}  (Ctrl+C para cerrar)")
    if "--sin-navegador" not in sys.argv:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
