# Pisador de freseo — Juan Grisales y Alek Coronado

Genera `pisador_freseo.mp3` con la voz **es-CO-GonzaloNeural**, tono grave,
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
