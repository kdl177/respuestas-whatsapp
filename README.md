# Respuestas de WhatsApp · SIMBAI Lab

Pegas el mensaje de un cliente y te da tres borradores de respuesta (directa, cercana y breve) con los datos de tu negocio y tu tono. Lo redacta una IA en tu ordenador con [Ollama](https://ollama.com): ni los mensajes ni los datos salen de él. Tú revisas, copias y envías.

- **Solo usa tus datos.** Lo que no está en la ficha no se lo inventa: lo deja como `[CONSULTAR: ...]` y te avisa de qué falta.
- **Tu tono.** De usted o de tú, con tu firma, sin emojis ni lenguaje de venta.
- **Contesta en el idioma del cliente.**
- **Sin instalar nada más.** Solo Python, sin dependencias.

## Instalar (Windows)

1. Python 3.11 o superior.
2. [Ollama](https://ollama.com) y el modelo: `ollama pull qwen3:14b`.
3. Doble clic en `iniciar.bat`: se abre en `http://127.0.0.1:8412`.

La primera vez rellena **Tu negocio**: servicios y precios, horario, dirección, normas. Se guarda en `ficha.json`, en esta carpeta.

## Configuración

| Variable | Por defecto |
|---|---|
| `RESPUESTAS_PUERTO` | `8412` |
| `OLLAMA_URL` | `http://localhost:11434` |
| `RESPUESTAS_MODELO` | `qwen3:14b` |

Con menos de 12 GB de memoria de vídeo, `qwen3:8b` va más rápido.
