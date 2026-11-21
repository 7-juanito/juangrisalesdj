"""
Procesado profesional de una nota de voz para pisador de DJ (cadena tipo radio).

Voz: filtro de graves, reduccion de ruido, recorte de silencios, EQ
(menos "barro" en 300 Hz, mas presencia en 4 kHz y brillo en 10 kHz),
de-esser y compresion fuerte. Luego eco estereo ping-pong + reverb corta,
limitador y loudness a ~-11 LUFS (nivel de drop de DJ).

Con --fx agrega un riser (subida) antes de la voz y un impacto grave al entrar.

Uso:  python procesar_nota_pro.py nota.m4a [salida.mp3] [--fx]
Requiere ffmpeg en el PATH.
"""

import subprocess
import sys

RISER_S = 1.4  # duracion de la subida antes de la voz

CADENA_VOZ = ",".join([
    "aformat=sample_rates=48000:channel_layouts=mono",
    "highpass=f=90",
    "afftdn=nf=-28",
    # recorta silencio al inicio y al final
    "silenceremove=start_periods=1:start_threshold=-42dB",
    "areverse",
    "silenceremove=start_periods=1:start_threshold=-42dB",
    "areverse",
    "equalizer=f=300:t=q:w=1.0:g=-3",
    "equalizer=f=4000:t=q:w=1.2:g=4",
    "highshelf=f=10000:g=3",
    "deesser=i=0.4",
    "acompressor=threshold=-22dB:ratio=4:attack=4:release=90:makeup=6",
    "acompressor=threshold=-10dB:ratio=8:attack=1:release=40",
])

ESPACIO = (
    "[v]asplit=3[dry][e1][e2];"
    "[e1]adelay=230|0,pan=stereo|c0=0.30*c0|c1=0*c0,"
    "aecho=0.8:0.5:230:0.35[l];"
    "[e2]adelay=0|460,pan=stereo|c0=0*c0|c1=0.22*c0,"
    "aecho=0.8:0.5:460:0.3[r];"
    "[dry]pan=stereo|c0=c0|c1=c0,aecho=0.9:0.7:35|60:0.18|0.10[d];"
    "[d][l][r]amix=inputs=3:normalize=0:duration=longest,apad=pad_dur=1.0[esp]"
)

RISER = (
    # barrido de seno ascendente + ruido que se abre, con fade in
    f"aevalsrc='0.25*sin(2*PI*(150*t+900*t*t/{RISER_S}))|"
    f"0.25*sin(2*PI*(152*t+900*t*t/{RISER_S}))':s=48000:d={RISER_S}[sw];"
    f"anoisesrc=d={RISER_S}:c=pink:a=0.35:r=48000,aformat=channel_layouts=stereo,"
    "highpass=f=2000[nz];"
    f"[sw][nz]amix=inputs=2:normalize=0,afade=t=in:d={RISER_S}:curve=exp[riser]"
)

IMPACTO = (
    # golpe grave: seno que cae de 110 a 35 Hz con decaimiento + ataque de ruido
    "aevalsrc='0.9*sin(2*PI*(35*t+75*(1-exp(-6*t))/6))*exp(-2.6*t)':"
    "s=48000:d=1.8,aformat=channel_layouts=stereo[sub];"
    "anoisesrc=d=0.25:c=white:a=0.5:r=48000,aformat=channel_layouts=stereo,"
    "lowpass=f=3000,afade=t=out:d=0.25[hit];"
    "[sub][hit]amix=inputs=2:normalize=0,"
    f"adelay={int(RISER_S*1000)}|{int(RISER_S*1000)}[imp]"
)

MASTER = (
    "acompressor=threshold=-14dB:ratio=2:attack=10:release=150,"
    "loudnorm=I=-11:TP=-1.5:LRA=9,"
    "alimiter=limit=0.84:attack=3:release=50:level=0,"
    "aresample=44100"
)


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--fx"]
    con_fx = "--fx" in sys.argv
    if not args:
        print(__doc__)
        sys.exit(1)
    entrada = args[0]
    salida = args[1] if len(args) > 1 else (
        "pisador_freseo_paisa_pro_fx.mp3" if con_fx else "pisador_freseo_paisa_pro.mp3"
    )

    grafo = f"[0:a]{CADENA_VOZ}[v];{ESPACIO};"
    if con_fx:
        ms = int(RISER_S * 1000)
        grafo += (
            f"[esp]adelay={ms}|{ms}[vozd];{RISER};{IMPACTO};"
            "[riser]apad=pad_dur=10[rp];"
            "[vozd][rp][imp]amix=inputs=3:normalize=0:duration=first,"
        )
    else:
        grafo += "[esp]"
    grafo += f"{MASTER}[out]"

    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", entrada,
         "-filter_complex", grafo, "-map", "[out]",
         "-c:a", "libmp3lame", "-b:a", "320k", salida],
        check=True,
    )
    print(f"Listo: {salida}")


if __name__ == "__main__":
    main()
