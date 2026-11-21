"""
Pisador de DJ con produccion profesional a partir de una nota de voz.

Capas que construye:
  1. Riser: ruido rosa con filtro que se abre + tono ascendente (subida).
  2. Reverse reverb: la reverb de la primera palabra al reves, "chupando" hacia la voz.
  3. Impacto: boom sub grave + golpe con cola de reverb al entrar la voz.
  4. Voz: limpieza, EQ, de-esser, compresion, saturacion suave y doble
     estereo (dos copias levemente desafinadas a izquierda y derecha).
  5. Reverb de sala (convolucion) de fondo.
  6. Delay throw: la ultima palabra se repite rebotando de lado a lado,
     filtrada tipo radio, y se va perdiendo.
  7. Downlifter: barrido que baja al final.
  8. Master: compresion de bus, loudness ~-10 LUFS, limitador a -1.5 dBFS.

Uso:  python pisador_pro_fx.py nota.m4a [salida.mp3]
Requiere: ffmpeg en el PATH y  pip install numpy
"""

import subprocess
import sys

import numpy as np

SR = 48000
RNG = np.random.default_rng(7)

# ---------------- Ajustes ----------------
RISER_S = 2.0            # duracion de la subida
IMPACTO_DB = -3.0        # volumen del boom
REVERB_DB = -16.0        # cantidad de reverb de sala sobre la voz
DOBLE_DB = -10.0         # volumen de las voces dobladas a los lados
THROW_S = 0.55           # cuanto de la ultima palabra se repite
THROW_DELAY_S = 0.33     # tiempo entre rebotes
THROW_REPETICIONES = 4
COLA_S = 2.2             # cola final para el eco/reverb
# -----------------------------------------

LIMPIEZA_VOZ = ",".join([
    "aformat=sample_rates=48000:channel_layouts=mono",
    "highpass=f=90",
    "afftdn=nf=-28",
    "silenceremove=start_periods=1:start_threshold=-42dB",
    "areverse",
    "silenceremove=start_periods=1:start_threshold=-42dB",
    "areverse",
    "equalizer=f=250:t=q:w=1.0:g=-3.5",
    "equalizer=f=3500:t=q:w=1.2:g=4",
    "highshelf=f=9000:g=4",
    "deesser=i=0.4",
    "acompressor=threshold=-24dB:ratio=4:attack=4:release=90:makeup=7",
    "acompressor=threshold=-10dB:ratio=10:attack=1:release=40",
])

MASTER = ",".join([
    "acompressor=threshold=-16dB:ratio=2:attack=15:release=200:makeup=2",
    "loudnorm=I=-10:TP=-1.5:LRA=9",
    "alimiter=limit=0.84:attack=3:release=60:level=0",
    "aresample=44100",
])


# ---------- utilidades ----------
def db(x: float) -> float:
    return 10 ** (x / 20)


def leer_voz(ruta: str) -> np.ndarray:
    crudo = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", ruta, "-af", LIMPIEZA_VOZ,
         "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
        check=True, capture_output=True,
    ).stdout
    voz = np.frombuffer(crudo, dtype=np.float32).astype(np.float64)
    voz = recortar_frase(voz)
    return voz / (np.max(np.abs(voz)) + 1e-9) * 0.9


def recortar_frase(voz: np.ndarray) -> np.ndarray:
    """Deja solo la frase: ignora ruiditos cortos antes/despues (golpes, clicks)."""
    ventana = int(0.02 * SR)
    n = len(voz) // ventana
    rms = np.sqrt((voz[: n * ventana].reshape(n, ventana) ** 2).mean(axis=1))
    activo = rms > np.max(rms) * 0.08
    # una zona cuenta como voz si tiene al menos 150 ms seguidos activos
    minimo = 8
    seguidos = np.convolve(activo, np.ones(minimo), mode="valid") >= minimo
    idx = np.nonzero(seguidos)[0]
    if len(idx) == 0:
        return voz
    ini = max(idx[0] * ventana - int(0.03 * SR), 0)
    fin = min((idx[-1] + minimo) * ventana + int(0.12 * SR), len(voz))
    recorte = voz[ini:fin].copy()
    f = int(0.005 * SR)
    recorte[:f] *= np.linspace(0, 1, f)
    recorte[-f * 4:] *= np.linspace(1, 0, f * 4)
    return recorte


def convolucion(x: np.ndarray, ir: np.ndarray) -> np.ndarray:
    n = len(x) + len(ir) - 1
    tam = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, tam) * np.fft.rfft(ir, tam), tam)[:n]


def impulso_reverb(segundos: float, brillo: float = 0.5) -> np.ndarray:
    """IR estereo sintetica: ruido con decaimiento exponencial y agudos que mueren antes."""
    n = int(segundos * SR)
    t = np.arange(n) / SR
    canales = []
    for _ in range(2):
        ruido = RNG.standard_normal(n)
        ruido = lowpass_variable(ruido, 9000 * brillo * np.exp(-2.5 * t) + 800)
        canales.append(ruido * np.exp(-6.9 * t / segundos))
    ir = np.stack(canales)
    ir[:, : int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))  # pre-delay suave
    return ir / np.max(np.abs(ir))


def lowpass_variable(x: np.ndarray, cortes_hz) -> np.ndarray:
    """Filtro pasa-bajos de un polo con frecuencia de corte que cambia en el tiempo."""
    cortes = np.broadcast_to(cortes_hz, x.shape)
    a = 1 - np.exp(-2 * np.pi * cortes / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def highpass(x: np.ndarray, hz: float) -> np.ndarray:
    return x - lowpass_variable(x, hz)


def ruido_rosa(n: int) -> np.ndarray:
    espectro = np.fft.rfft(RNG.standard_normal(n))
    f = np.maximum(np.fft.rfftfreq(n), 1 / n)
    r = np.fft.irfft(espectro / np.sqrt(f), n)
    return r / np.max(np.abs(r))


def desafinar(x: np.ndarray, cents: float) -> np.ndarray:
    factor = 2 ** (cents / 1200)
    idx = np.arange(0, len(x) - 1, factor)
    return np.interp(idx, np.arange(len(x)), x)


def colocar(destino: np.ndarray, señal: np.ndarray, inicio: int) -> None:
    """Suma una señal estereo (2, n) en destino a partir de 'inicio' (muestras)."""
    fin = min(destino.shape[1], inicio + señal.shape[1])
    destino[:, inicio:fin] += señal[:, : fin - inicio]


def a_estereo(x: np.ndarray, pan: float = 0.0) -> np.ndarray:
    """pan: -1 izquierda, 0 centro, 1 derecha (ley de potencia constante)."""
    ang = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(ang), x * np.sin(ang)]) * np.sqrt(2)


# ---------- capas ----------
def riser(segundos: float) -> np.ndarray:
    n = int(segundos * SR)
    t = np.arange(n) / SR
    curva = (t / segundos) ** 2.2
    capas = []
    for lado in range(2):
        ruido = ruido_rosa(n)
        ruido = lowpass_variable(ruido, 300 + 14000 * curva)
        ruido = highpass(ruido, 200)
        freq = 180 * 2 ** (3 * curva) * (1 + 0.004 * lado)  # 3 octavas hacia arriba
        tono = np.sin(2 * np.pi * np.cumsum(freq) / SR) * 0.35
        capas.append((ruido * 0.8 + tono) * curva)
    return np.stack(capas)


def impacto() -> np.ndarray:
    dur = 2.5
    n = int(dur * SR)
    t = np.arange(n) / SR
    freq = 32 + 90 * np.exp(-18 * t)                      # cae de ~120 Hz a 32 Hz
    sub = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-2.2 * t)
    sub = np.tanh(sub * 1.8) / np.tanh(1.8)               # un poco de saturacion
    golpe = RNG.standard_normal(n) * np.exp(-40 * t)
    golpe = lowpass_variable(golpe, 5000)
    cola = convolucion(golpe * 0.6, impulso_reverb(2.0, 0.35)[0])[:n]
    cola_d = convolucion(golpe * 0.6, impulso_reverb(2.0, 0.35)[1])[:n]
    izq = sub + golpe * 0.5 + cola * 0.10
    der = sub + golpe * 0.5 + cola_d * 0.10
    return np.stack([izq, der]) * db(IMPACTO_DB)


def downlifter(segundos: float) -> np.ndarray:
    n = int(segundos * SR)
    t = np.arange(n) / SR
    curva = 1 - t / segundos
    capas = []
    for _ in range(2):
        ruido = lowpass_variable(ruido_rosa(n), 200 + 9000 * curva ** 2)
        capas.append(ruido * curva ** 1.5 * 0.35)
    return np.stack(capas)


def voz_produccion(voz: np.ndarray) -> np.ndarray:
    sat = np.tanh(voz * 1.6) / np.tanh(1.6)               # calidez/presencia
    centro = a_estereo(sat)
    izq = np.concatenate([np.zeros(int(0.014 * SR)), desafinar(sat, -9)])
    der = np.concatenate([np.zeros(int(0.021 * SR)), desafinar(sat, +9)])
    n = len(sat) + int(0.03 * SR)
    doble = np.zeros((2, n))
    doble[0, : len(izq)] += highpass(izq, 200)[:n]
    doble[1, : len(der)] += highpass(der, 200)[:n]
    salida = np.zeros((2, n))
    salida[:, : centro.shape[1]] += centro
    return salida + doble * db(DOBLE_DB)


def reverb_sala(voz: np.ndarray) -> np.ndarray:
    ir = impulso_reverb(2.4, 0.55)
    envio = highpass(voz, 300)
    return np.stack([convolucion(envio, ir[0]), convolucion(envio, ir[1])]) * db(REVERB_DB)


def reverse_reverb(voz: np.ndarray) -> np.ndarray:
    inicio = voz[: int(0.45 * SR)]
    ir = impulso_reverb(1.6, 0.6)
    capas = np.stack([convolucion(inicio, ir[0]), convolucion(inicio, ir[1])])
    capas = highpass(capas[0], 250), highpass(capas[1], 250)
    rev = np.stack(capas)[:, ::-1]
    rev *= np.linspace(0, 1, rev.shape[1]) ** 1.5          # crece hacia la voz
    return rev / (np.max(np.abs(rev)) + 1e-9) * 0.45


def delay_throw(voz: np.ndarray) -> np.ndarray:
    ultima = voz[-int(THROW_S * SR):].copy()
    ultima *= np.linspace(1, 0, len(ultima)) ** 0.3
    radio = lowpass_variable(highpass(ultima, 700), 3500)   # sonido tipo radio
    paso = int(THROW_DELAY_S * SR)
    n = paso * THROW_REPETICIONES + 2 * len(radio)
    out = np.zeros((2, n))
    for k in range(THROW_REPETICIONES):
        pan = -0.85 if k % 2 == 0 else 0.85
        colocar(out, a_estereo(radio * 0.55 * (0.6 ** k), pan), len(radio) + paso * k)
    ir = impulso_reverb(1.8, 0.4)
    mono = out.mean(axis=0)
    out += np.stack([convolucion(mono, ir[0]), convolucion(mono, ir[1])])[:, :n] * 0.15
    return out


# ---------- armado ----------
def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    entrada = sys.argv[1]
    salida = sys.argv[2] if len(sys.argv) > 2 else "pisador_freseo_paisa_pro_fx_v2.mp3"

    print("Limpiando voz...")
    voz = leer_voz(entrada)
    inicio_voz = int(RISER_S * SR)
    fin_voz = inicio_voz + len(voz)
    total = fin_voz + int(COLA_S * SR) + int(THROW_DELAY_S * SR * THROW_REPETICIONES)
    mezcla = np.zeros((2, total))

    print("Construyendo capas...")
    colocar(mezcla, riser(RISER_S) * 0.55, 0)
    rr = reverse_reverb(voz)
    colocar(mezcla, rr, max(inicio_voz - rr.shape[1], 0))
    colocar(mezcla, impacto(), inicio_voz)
    colocar(mezcla, voz_produccion(voz), inicio_voz)
    colocar(mezcla, reverb_sala(voz), inicio_voz)
    colocar(mezcla, delay_throw(voz), fin_voz - int(THROW_S * SR))
    colocar(mezcla, downlifter(1.6), fin_voz - int(0.2 * SR))

    # recorta silencio sobrante al final y hace fade-out corto
    energia = np.max(np.abs(mezcla), axis=0)
    ultimo = np.nonzero(energia > 1e-3)[0][-1] + int(0.05 * SR)
    mezcla = mezcla[:, :ultimo]
    fade = int(0.3 * SR)
    mezcla[:, -fade:] *= np.linspace(1, 0, fade)
    mezcla /= np.max(np.abs(mezcla)) + 1e-9

    print("Masterizando...")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2",
         "-i", "-", "-af", MASTER, "-c:a", "libmp3lame", "-b:a", "320k", salida],
        input=mezcla.T.astype(np.float32).tobytes(), check=True,
    )
    print(f"Listo: {salida}")


if __name__ == "__main__":
    main()
