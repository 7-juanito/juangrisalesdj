"""
Generador de pisador de DJ para freseo.
Voz: es-CO-GonzaloNeural (edge-tts), tono grave, volumen alto,
eco de 3 repeticiones y normalizacion con pydub.
Salida: pisador_freseo.mp3

Uso (Windows):  python pisador_freseo.py
"""

import asyncio
import os
import sys

import edge_tts
from pydub import AudioSegment
from pydub.effects import normalize

# ---------------- Configuracion ----------------
TEXTO = "¡Estás al mando de DJ Juan Grisales y Alek Coronado!"
VOZ = "es-CO-GonzaloNeural"
TONO = "-15Hz"        # negativo = mas grave
VOLUMEN = "+50%"      # volumen alto
VELOCIDAD = "-5%"     # un poco mas pausado para que pegue

ECO_REPETICIONES = 3
ECO_RETARDO_MS = 250  # separacion entre cada repeticion
ECO_ATENUACION_DB = 6 # cada repeticion baja estos dB

ARCHIVO_TEMP = "voz_temp.mp3"
ARCHIVO_SALIDA = "pisador_freseo.mp3"
# ------------------------------------------------


async def generar_voz() -> None:
    comunicador = edge_tts.Communicate(
        TEXTO, VOZ, rate=VELOCIDAD, volume=VOLUMEN, pitch=TONO
    )
    await comunicador.save(ARCHIVO_TEMP)


def aplicar_eco(audio: AudioSegment) -> AudioSegment:
    cola = ECO_RETARDO_MS * ECO_REPETICIONES
    resultado = audio + AudioSegment.silent(duration=cola, frame_rate=audio.frame_rate)
    for i in range(1, ECO_REPETICIONES + 1):
        repeticion = audio - (ECO_ATENUACION_DB * i)
        resultado = resultado.overlay(repeticion, position=ECO_RETARDO_MS * i)
    return resultado


def main() -> None:
    print(f"Generando voz con {VOZ}...")
    asyncio.run(generar_voz())

    print("Aplicando eco y normalizando...")
    voz = AudioSegment.from_file(ARCHIVO_TEMP, format="mp3")
    con_eco = aplicar_eco(voz)
    final = normalize(con_eco, headroom=0.1)

    final.export(ARCHIVO_SALIDA, format="mp3", bitrate="320k")
    os.remove(ARCHIVO_TEMP)
    print(f"Listo: {os.path.abspath(ARCHIVO_SALIDA)}")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        print("Error: no se encontro ffmpeg. Revisa que este instalado y en el PATH.")
        print(e)
        sys.exit(1)
