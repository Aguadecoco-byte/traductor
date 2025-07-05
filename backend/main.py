from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from gtts import gTTS
import random
import os
import uuid
from dotenv import load_dotenv

app = FastAPI()

# CORS para frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carpeta para audios generados
AUDIO_DIR = "audio_files"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Mensajes posibles para perros (puedes ampliar la lista)
BARK_MESSAGES = [
    "Tengo hambre, ¿me das algo de comer?",
    "¡Quiero salir a pasear!",
    "Ráscame la panza, por favor.",
    "¿Jugamos a la pelota?",
    "Estoy cansado, quiero dormir.",
    "¡Hay alguien en la puerta!",
    "¿Me das un premio?",
    "Solo quiero que me acaricies.",
    "¡Guau! ¡Estoy feliz de verte!",
    "¿Por qué los gatos son tan raros?"
]

# Cargar variables de entorno solo si existe .env (útil en local)
if os.path.exists('.env') or os.path.exists('backend/.env'):
    load_dotenv()

# Inicializa Groq usando variable de entorno (Render la provee en el panel)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("Falta la variable de entorno GROQ_API_KEY. Configúrala en Render.")
client = Groq(api_key=GROQ_API_KEY)

# Utilidad para generar traducción divertida
async def invent_translation(bark_text: str, animal: str = "perro") -> str:
    # Si el texto es muy corto o solo "guau guau", elige aleatorio
    if bark_text.strip().lower() in ["guau", "guau guau", "gua gua", "guau guao guao"] or len(bark_text.strip()) < 8:
        return random.choice(BARK_MESSAGES)
    # Si el usuario escribe algo más, usa la IA
    prompt = f"Eres un traductor de {animal}s a humano. Traduce el siguiente mensaje de {animal} a una frase divertida, natural y breve en español, como si el {animal} hablara: '{bark_text}'. No expliques, solo traduce."
    completion = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "user", "content": prompt}],
        temperature=1,
        max_completion_tokens=128,
        top_p=1,
        stream=False,
        stop=None,
    )
    return completion.choices[0].message.content.strip()

# Endpoint: traducir texto tipo "guau guau"
@app.post("/api/translate_bark")
async def translate_bark(text: str = Form(...), animal: str = Form("perro")):
    translation = await invent_translation(text, animal)
    # Generar audio
    tts = gTTS(translation, lang="es")
    filename = f"{uuid.uuid4().hex}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)
    tts.save(filepath)
    return {"translation": translation, "audio_url": f"/api/audio/{filename}"}

# Endpoint: subir audio (y opcionalmente imagen)
@app.post("/api/upload")
async def upload_audio(audio: UploadFile = File(...), image: UploadFile = File(None), animal: str = Form("perro")):
    # Aquí podrías procesar el audio o imagen si quieres
    # Por ahora, solo inventa traducción aleatoria
    translation = await invent_translation("guau guau", animal)
    tts = gTTS(translation, lang="es")
    filename = f"{uuid.uuid4().hex}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)
    tts.save(filepath)
    return {"translation": translation, "audio_url": f"/api/audio/{filename}"}

# Endpoint: servir audio generado
@app.get("/api/audio/{filename}")
def get_audio(filename: str):
    filepath = os.path.join(AUDIO_DIR, filename)
    if not os.path.exists(filepath):
        return JSONResponse(status_code=404, content={"error": "Audio not found"})
    return FileResponse(filepath, media_type="audio/mpeg")
