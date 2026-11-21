# Pisador de freseo — Juan Grisales y Alek Coronado

Genera `pisador_freseo.mp3` con voz de mujer **es-CO-SalomeNeural** (lenta y sensual; la de hombre es **es-CO-GonzaloNeural**),
volumen alto, eco de 3 repeticiones y volumen normalizado.

## Instalación en Windows

1. **Python 3.10+** — descárgalo de https://www.python.org/downloads/
   (marca la casilla **"Add Python to PATH"** al instalar).

2. **edge-tts y pydub** — en una terminal (PowerShell o CMD):
   ```
   pip install edge-tts pydub
   ```
   Si tienes **Python 3.13 o más nuevo**, instala también:
   ```
   pip install audioop-lts
   ```

3. **ffmpeg** (pydub lo necesita para leer/escribir mp3). La forma más fácil:
   ```
   winget install Gyan.FFmpeg
   ```
   Cierra y vuelve a abrir la terminal, y comprueba con:
   ```
   ffmpeg -version
   ```
   *(Alternativa manual: descarga el zip "release essentials" de
   https://www.gyan.dev/ffmpeg/builds/, descomprímelo en `C:\ffmpeg` y agrega
   `C:\ffmpeg\bin` a la variable de entorno PATH.)*

## Uso

Desde la carpeta donde está el script:
```
python pisador_freseo.py
```
Se crea `pisador_freseo.mp3` en esa misma carpeta. Necesita internet (edge-tts usa
el servicio de voces de Microsoft).

## Ajustes

Arriba del script puedes cambiar:
- `TEXTO` — la frase.
- `TONO` — más grave: `-20Hz`, `-25Hz`…
- `VOLUMEN` — hasta `+100%`.
- `ECO_RETARDO_MS` / `ECO_ATENUACION_DB` — separación y caída del eco.

## Versión profesional desde una nota de voz

```
python procesar_nota_pro.py nota.m4a          # solo voz procesada
python procesar_nota_pro.py nota.m4a --fx     # con subida (riser) e impacto grave
```
Cadena: filtro de graves, reducción de ruido, recorte de silencios, EQ (menos barro,
más presencia y brillo), de-esser, compresión, eco estéreo ping-pong + reverb corta,
limitador y loudness a -11 LUFS / pico -1.5 dBFS.
