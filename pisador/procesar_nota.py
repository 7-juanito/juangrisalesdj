"""
Convierte una nota de voz grabada (m4a, ogg, opus, wav, mp3...) en pisador:
recorta silencios, aplica el mismo eco suave y normaliza.

Uso:  python procesar_nota.py nota.m4a  [salida.mp3]
"""

import sys

from pydub import AudioSegment
from pydub.effects import normalize, high_pass_filter
from pydub.silence import detect_leading_silence

from pisador_freseo import aplicar_eco


def recortar_silencios(audio: AudioSegment, umbral_db: float = -40.0) -> AudioSegment:
    inicio = detect_leading_silence(audio, silence_threshold=umbral_db)
    fin = detect_leading_silence(audio.reverse(), silence_threshold=umbral_db)
    return audio[max(inicio - 50, 0): len(audio) - max(fin - 150, 0)]


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    entrada = sys.argv[1]
    salida = sys.argv[2] if len(sys.argv) > 2 else "pisador_freseo_paisa.mp3"

    voz = AudioSegment.from_file(entrada)
    voz = high_pass_filter(voz, 80)          # quita ruido grave del celular
    voz = recortar_silencios(voz)
    final = normalize(aplicar_eco(normalize(voz)), headroom=0.1)
    final.export(salida, format="mp3", bitrate="320k")
    print(f"Listo: {salida}")


if __name__ == "__main__":
    main()
