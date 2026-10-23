"""Makes an MP4 lesson video from a saved AI lesson.

The video has a cartoon teacher whose mouth moves with the voice, a board with the
heading and key points, and a spoken narration. It is made in three steps:
1. edge-tts turns every narration into speech (needs the internet),
2. Pillow draws the pictures (3 mouth shapes x 2 arm positions for each part),
3. ffmpeg (from the imageio-ffmpeg package, nothing to install) joins pictures and voice.
"""
import asyncio
import subprocess
import tempfile
import wave
from array import array
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1280, 720, 10
VOICE = "en-IN-NeerjaNeural"  # an Indian English voice
RATE = 16000


def ffmpeg_exe() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def speak_to_file(text: str, out: Path) -> None:
    """Turn text into speech (an MP3 file) with edge-tts."""
    import edge_tts
    asyncio.run(edge_tts.Communicate(text, VOICE).save(str(out)))


def _to_wav(src: Path, dst: Path) -> None:
    subprocess.run([ffmpeg_exe(), "-y", "-i", str(src), "-ar", str(RATE), "-ac", "1", str(dst)],
                   check=True, capture_output=True)


def _read_wav(path: Path) -> array:
    with wave.open(str(path), "rb") as w:
        samples = array("h")
        samples.frombytes(w.readframes(w.getnframes()))
    return samples


def mouth_levels(samples: array) -> list[int]:
    """0 closed, 1 half open, 2 open: one value for every video frame, from how loud the voice is."""
    step = RATE // FPS
    loud = []
    for i in range(0, len(samples), step):
        part = samples[i:i + step]
        loud.append((sum(s * s for s in part) / max(1, len(part))) ** 0.5)
    top = max(loud, default=0) or 1
    return [2 if v > 0.45 * top else 1 if v > 0.12 * top else 0 for v in loud]


# ---------------- drawing ----------------
def _font(size: int, bold: bool = False):
    for name in (["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"]):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size)


def _wrap(d: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=font) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + [cur] if cur else lines


def _teacher(d: ImageDraw.ImageDraw, ox: int, oy: int, s: float, mouth: int, arm_up: bool) -> None:
    def P(x, y):
        return (ox + x * s, oy + y * s)

    def box(x1, y1, x2, y2):
        return [*P(x1, y1), *P(x2, y2)]

    skin, hair, ink = "#f1c9a5", "#2b2118", "#1f4d4a"
    d.polygon([P(44, 252), P(52, 188), P(80, 168), P(140, 168), P(168, 188), P(176, 252)], fill="#e8a317")
    d.line([P(62, 190), P(54, 240)], fill=skin, width=int(14 * s))
    end = [P(188, 176), P(197, 132)] if arm_up else [P(190, 186), P(207, 160)]
    d.line([P(150, 190), *end], fill=skin, width=int(14 * s), joint="curve")
    d.ellipse(box(end[-1][0] / s - ox / s - 10, end[-1][1] / s - oy / s - 10,
                  end[-1][0] / s - ox / s + 10, end[-1][1] / s - oy / s + 10), fill=skin)
    d.rectangle(box(98, 138, 122, 170), fill="#e0b08a")
    d.ellipse(box(68, 60, 152, 144), fill=skin)
    d.pieslice(box(66, 52, 154, 140), 190, 350, fill=hair)
    for cx in (94, 126):
        d.ellipse(box(cx - 12, 92, cx + 12, 116), outline=ink, width=max(2, int(3 * s)))
        d.ellipse(box(cx - 3.4, 100.6, cx + 3.4, 107.4), fill="#222222")
    d.line([P(106, 104), P(114, 104)], fill=ink, width=max(2, int(3 * s)))
    ry = (2, 5, 9)[mouth]
    d.ellipse(box(101, 128 - ry, 119, 128 + ry), fill="#8a2f2f")


def _frame(heading: str, points: list[str], label: str, mouth: int, arm_up: bool, path: Path) -> None:
    img = Image.new("RGB", (W, H), "#e4efed")
    d = ImageDraw.Draw(img)
    _teacher(d, 40, 110, 2.1, mouth, arm_up)
    d.rounded_rectangle([560, 50, W - 40, H - 50], radius=28, fill="#1f4d4a")
    y = 90
    for line in _wrap(d, heading, _font(46, True), W - 700)[:3]:
        d.text((600, y), line, font=_font(46, True), fill="#e8a317")
        y += 58
    y += 14
    for p in points[:4]:
        lines = _wrap(d, p, _font(32), W - 740)[:3]
        for i, line in enumerate(lines):
            d.text((600, y), ("•  " if i == 0 else "    ") + line, font=_font(32), fill="#ffffff")
            y += 42
        y += 12
    d.text((600, H - 100), label, font=_font(24), fill="#a8c4bb")
    img.save(path)


# ---------------- the whole video ----------------
def make_video(lesson: dict, out_path: Path, speak=None) -> None:
    speak = speak or speak_to_file
    sections = lesson["sections"]
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        pcm, schedule = array("h"), []  # schedule: (picture file, seconds)
        silence = array("h", [0] * (RATE * 6 // 10))
        for n, sec in enumerate(sections):
            raw = tmp / f"s{n}.mp3"
            speak(sec["narration"], raw)
            wav = tmp / f"s{n}.wav"
            _to_wav(raw, wav)
            samples = _read_wav(wav)
            pcm.extend(samples)
            pcm.extend(silence)
            levels = mouth_levels(samples) + [0] * 6  # the pause after the part: mouth closed
            pics = {}
            for i, level in enumerate(levels):
                arm_up = (i // 6) % 2 == 0
                key = (level, arm_up)
                if key not in pics:
                    pics[key] = tmp / f"s{n}_{level}_{int(arm_up)}.png"
                    _frame(sec["heading"], sec.get("key_points", []), f"Part {n + 1} of {len(sections)}  ·  ClassMitra",
                           level, arm_up, pics[key])
                schedule.append((pics[key], 1 / FPS))
        master = tmp / "voice.wav"
        with wave.open(str(master), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(pcm.tobytes())
        lst = tmp / "frames.txt"
        rows = []
        for pic, sec in schedule:
            rows += [f"file '{pic.as_posix()}'", f"duration {sec}"]
        rows.append(f"file '{schedule[-1][0].as_posix()}'")  # the concat reader needs the last picture twice
        lst.write_text("\n".join(rows), encoding="utf-8")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        done = subprocess.run(
            [ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(master),
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "128k",
             "-shortest", str(out_path)], capture_output=True)
        if done.returncode != 0:
            raise RuntimeError("ffmpeg could not make the video: " + done.stderr.decode(errors="replace")[-300:])
