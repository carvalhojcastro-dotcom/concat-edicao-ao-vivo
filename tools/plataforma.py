"""O que muda entre Mac e Windows, num lugar só. O resto das ferramentas é igual nos dois.

- Transcrição: no Mac (Apple Silicon) mlx-whisper; no Windows faster-whisper com o mesmo modelo
  (large-v3-turbo), na placa NVIDIA se houver (CUDA), senão no processador.
- HEVC: no Mac VideoToolbox; no Windows NVENC / Quick Sync / AMF se o ffmpeg tiver, senão libx265.
- Helvetica: é da Apple e não pode ir para o Windows. Lá entra a Arimo (OFL), desenhada com
  as mesmas medidas da Helvetica/Arial, e a Archivo Condensed Black (OFL) no lugar da Helvetica Neue
  Condensed Black. As duas já vêm em fonts/.
- Preferências e recentes do Concat: ~/Library/Application Support no Mac, %APPDATA% no Windows.
- Mesa: no Windows ela muitas vezes fica dentro do OneDrive; vem da pasta conhecida do sistema.
"""
import os
import shutil
import subprocess
import sys

# CONCAT_PLATAFORMA=windows força o modo Windows (fontes Arimo, faster-whisper, libx265) para testar no Mac
_FORCA = os.environ.get("CONCAT_PLATAFORMA", "").lower()
MAC = sys.platform == "darwin" and _FORCA != "windows"
WINDOWS = os.name == "nt"
RAIZ = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FONTES = os.path.join(RAIZ, "fonts")


def _f(nome):
    return os.path.join(FONTES, nome)


# ───────────────────────────── fontes "Helvetica" ─────────────────────────────

def faces_helvetica():
    """face -> (família CSS no Concat, peso, itálico, arquivo para medir, índice no arquivo)."""
    if MAC:
        helv = "/System/Library/Fonts/Helvetica.ttc"
        return {
            "helv": ('"Helvetica Neue Medium"', 500, False, _f("HelveticaNeue-Medium.ttf"), 0),
            "helv-regular": ("Helvetica", 400, False, helv, 0),  # legendas simples antigas
            "helv-bold": ("Helvetica", 700, False, helv, 1),
            "helv-oblique": ("Helvetica", 400, True, helv, 2),
            "helv-bold-oblique": ("Helvetica", 700, True, helv, 3),
            "helv-light-oblique": ("Helvetica", 300, True, helv, 5),
            "helv-cond-black": ('"Helvetica Neue Condensed Black"', 900, False, _f("HelveticaNeue-CondensedBlack.ttf"), 0),
        }
    return {
        "helv": ("Arimo", 500, False, _f("Arimo-Medium.ttf"), 0),
        "helv-regular": ("Arimo", 400, False, _f("Arimo-Medium.ttf"), 0),
        "helv-bold": ("Arimo", 700, False, _f("Arimo-Bold.ttf"), 0),
        "helv-oblique": ("Arimo", 400, True, _f("Arimo-Italic.ttf"), 0),
        "helv-bold-oblique": ("Arimo", 700, True, _f("Arimo-BoldItalic.ttf"), 0),
        "helv-light-oblique": ("Arimo", 400, True, _f("Arimo-Italic.ttf"), 0),
        "helv-cond-black": ('"Archivo Condensed Black"', 900, False, _f("Archivo-CondensedBlack.ttf"), 0),
    }


def registrar_helvetica():
    """(família, arquivo) que o projeto precisa registrar com addFont."""
    if MAC:  # a Helvetica do sistema o Concat acha sozinho; as faces extraídas da Neue, não
        return [("Helvetica Neue Medium", "HelveticaNeue-Medium.ttf"),
                ("Helvetica Neue Condensed Black", "HelveticaNeue-CondensedBlack.ttf")]
    return [("Arimo", n) for n in ("Arimo-Medium.ttf", "Arimo-Bold.ttf", "Arimo-Italic.ttf", "Arimo-BoldItalic.ttf")] + \
        [("Archivo Condensed Black", "Archivo-CondensedBlack.ttf")]


def legenda_simples():
    """(família CSS, peso, arquivo) da legenda simples semibold."""
    if MAC:
        return '"Helvetica Neue Medium"', 500, _f("HelveticaNeue-Medium.ttf")
    return "Arimo", 500, _f("Arimo-Medium.ttf")


def familia_helvetica():
    return "Helvetica" if MAC else "Arimo"


# ─────────────────────────────── transcrição ───────────────────────────────

MODELO_MLX = "mlx-community/whisper-large-v3-turbo"
MODELO_CT2 = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"


def transcrever(wav, language="pt", initial_prompt=None):
    """Whisper com tempo por palavra. Devolve o mesmo formato do mlx-whisper:
    {"text", "segments": [{"start", "end", "text", "words": [{"word", "start", "end"}]}]}."""
    if MAC:
        import mlx_whisper
        return mlx_whisper.transcribe(wav, path_or_hf_repo=MODELO_MLX, language=language, word_timestamps=True,
                                      condition_on_previous_text=False, initial_prompt=initial_prompt)
    from faster_whisper import WhisperModel
    try:
        import ctranslate2
        cuda = ctranslate2.get_cuda_device_count() > 0
    except Exception:
        cuda = False
    modelo = WhisperModel(MODELO_CT2, device="cuda" if cuda else "cpu", compute_type="float16" if cuda else "int8")
    segs, _ = modelo.transcribe(wav, language=language, word_timestamps=True, beam_size=5,
                                condition_on_previous_text=False, initial_prompt=initial_prompt)
    out = []
    for s in segs:
        # float(): o faster-whisper devolve numpy.float64, que o json não grava
        out.append({"start": float(s.start), "end": float(s.end), "text": s.text,
                    "words": [{"word": w.word, "start": float(w.start), "end": float(w.end),
                               "probability": float(w.probability)} for w in s.words]})
    return {"text": "".join(s["text"] for s in out), "segments": out, "language": language}


# ─────────────────────────────── codificação ───────────────────────────────

_enc = None


def hevc(bitrate="80M"):
    """Argumentos do ffmpeg para gravar HEVC (hvc1) no codificador mais rápido da máquina."""
    global _enc
    if MAC:
        return ["-c:v", "hevc_videotoolbox", "-b:v", bitrate, "-tag:v", "hvc1"]
    if _enc is None:
        lista = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
        _enc = next((e for e in ("hevc_nvenc", "hevc_qsv", "hevc_amf") if e in lista and _funciona(e)), "libx265")
    if _enc == "libx265":
        return ["-c:v", "libx265", "-preset", "medium", "-b:v", bitrate, "-tag:v", "hvc1"]
    return ["-c:v", _enc, "-b:v", bitrate, "-tag:v", "hvc1"]


def _funciona(enc):
    """O ffmpeg lista o codificador mesmo sem a placa: testa um quadro."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.1", "-frames:v", "1",
                        "-c:v", enc, "-f", "null", "-"], capture_output=True)
    return r.returncode == 0


# ──────────────────────────────── caminhos ────────────────────────────────

def mesa():
    """A pasta da Mesa (Desktop) de verdade - no Windows pode estar no OneDrive."""
    if WINDOWS:
        try:
            import ctypes
            from ctypes import wintypes
            FOLDERID_Desktop = ctypes.c_char_p(bytes.fromhex("3accbfb42cdb4c42b0297fe99a87c641"))
            caminho = ctypes.c_wchar_p()
            ctypes.windll.shell32.SHGetKnownFolderPath(FOLDERID_Desktop, 0, None, ctypes.byref(caminho))
            if caminho.value:
                return caminho.value
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Desktop")


def h264(bitrate="30M"):
    """Argumentos do ffmpeg para H.264 no codificador mais rápido da máquina."""
    if MAC:
        return ["-c:v", "h264_videotoolbox", "-b:v", bitrate]
    lista = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    enc = next((e for e in ("h264_nvenc", "h264_qsv", "h264_amf") if e in lista and _funciona(e)), "libx264")
    return ["-c:v", enc, "-b:v", bitrate] + (["-preset", "medium"] if enc == "libx264" else [])


def pasta_concat_app():
    """Onde o Concat guarda preferências (settings.json) e a lista de recentes (recents.json)."""
    if WINDOWS:
        return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "app.concat.editor")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/app.concat.editor")
    return os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "app.concat.editor")


def recentes():
    return os.path.join(pasta_concat_app(), "recents.json")


def _garantir_ffmpeg():
    """O winget põe o ffmpeg no PATH só de janelas novas: um terminal (ou o Claude Code) aberto antes da
    instalação não o acharia. Procura nas pastas do winget e põe no PATH deste processo."""
    if not WINDOWS or shutil.which("ffmpeg"):
        return
    local = os.environ.get("LOCALAPPDATA", "")
    candidatas = [os.path.join(local, "Microsoft", "WinGet", "Links")]
    pacotes = os.path.join(local, "Microsoft", "WinGet", "Packages")
    if os.path.isdir(pacotes):
        for nome in os.listdir(pacotes):
            if nome.lower().startswith("gyan.ffmpeg"):
                for raiz, _, arquivos in os.walk(os.path.join(pacotes, nome)):
                    if "ffmpeg.exe" in arquivos:
                        candidatas.append(raiz)
    for pasta in candidatas:
        if os.path.exists(os.path.join(pasta, "ffmpeg.exe")):
            os.environ["PATH"] = pasta + os.pathsep + os.environ.get("PATH", "")
            return


_garantir_ffmpeg()


def python_venv():
    sub = ("Scripts", "python.exe") if WINDOWS else ("bin", "python")
    return os.path.join(RAIZ, "tools", ".venv", *sub)


def ffmpeg_ok():
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
