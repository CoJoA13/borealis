"""Borealis sound theme: soft, glassy chimes in E-major pentatonic.

Additive bell synthesis (inharmonic partials, per-partial decay), a touch of
stereo width and a small Schroeder reverb, all in plain Python; encoded to
Ogg Vorbis with ffmpeg when available (WAV otherwise; both are valid in an
XDG sound theme). Anything not provided falls back to Ocean.
"""
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tokens import IDS, NAME  # noqa: E402

SR = 48000

# E major pentatonic, a few octaves
NOTE = {
    "B3": 246.94, "E4": 329.63, "G#4": 415.30, "A4": 440.00, "B4": 493.88,
    "C5": 523.25, "C#5": 554.37, "E5": 659.25, "F#5": 739.99, "G#5": 830.61,
    "B5": 987.77, "C#6": 1108.73, "E6": 1318.51, "G#6": 1661.22, "B6": 1975.53,
}
# glassy bell: (ratio, amplitude, decay multiplier)
BELL = ((1.0, 1.0, 1.0), (2.0, 0.42, 0.62), (2.76, 0.22, 0.45),
        (5.40, 0.10, 0.28), (8.93, 0.04, 0.18))


def silence(seconds):
    return [0.0] * int(SR * seconds)


def mix_into(buf, sig, at, gain=1.0):
    start = int(at * SR)
    need = start + len(sig)
    if need > len(buf):
        buf.extend([0.0] * (need - len(buf)))
    for i, v in enumerate(sig):
        buf[start + i] += v * gain


def bell(freq, dur=1.2, decay=0.55, attack=0.004, detune=0.0, bright=1.0):
    n = int(SR * dur)
    out = [0.0] * n
    f = freq * (2 ** (detune / 1200))
    for ratio, amp, dmul in BELL:
        fr = f * ratio
        if fr > SR / 2.2:
            continue
        tau = decay * dmul
        a = amp * (bright if ratio > 1 else 1.0)
        w = 2 * math.pi * fr / SR
        for i in range(n):
            t = i / SR
            env = math.exp(-t / tau)
            if t < attack:
                env *= t / attack
            out[i] += a * env * math.sin(w * i)
    # never stop a ringing partial dead: cosine fade over the last 80 ms
    m = min(n, int(SR * 0.08))
    for k in range(m):
        out[n - m + k] *= 0.5 * (1 + math.cos(math.pi * k / m))
    return out


def pad(freqs, dur, attack=0.35, release=0.8, level=0.18):
    n = int(SR * dur)
    out = [0.0] * n
    for k, fr in enumerate(freqs):
        w = 2 * math.pi * fr / SR
        w2 = 2 * math.pi * fr * 1.003 / SR
        for i in range(n):
            t = i / SR
            env = min(1.0, t / attack) * min(1.0, max(0.0, (dur - t) / release))
            out[i] += level * env * (math.sin(w * i) + 0.5 * math.sin(w2 * i + k))
    return out


def tick(freq=2200, dur=0.07):
    n = int(SR * dur)
    w = 2 * math.pi * freq / SR
    return [math.exp(-i / (SR * 0.012)) * math.sin(w * i) * 0.6 for i in range(n)]


def whoosh(dur=0.7, f0=5000, f1=500, seed=3):
    """Band-passed noise sweeping downwards (state-variable filter)."""
    rnd = random.Random(seed)
    n = int(SR * dur)
    low = band = 0.0
    out = []
    for i in range(n):
        t = i / n
        fc = f0 * (f1 / f0) ** t
        fcoef = 2 * math.sin(math.pi * fc / SR)
        x = rnd.uniform(-1, 1)
        high = x - low - 0.9 * band
        band += fcoef * high
        low += fcoef * band
        env = math.sin(math.pi * t) ** 1.2
        out.append(band * env * 0.5)
    return out


def glide(f0, f1, dur=0.35):
    n = int(SR * dur)
    out, phase = [], 0.0
    for i in range(n):
        t = i / n
        fr = f0 * (f1 / f0) ** t
        phase += 2 * math.pi * fr / SR
        env = math.sin(math.pi * t) ** 1.2
        out.append(0.45 * env * (math.sin(phase) + 0.3 * math.sin(2 * phase)))
    return out


# ------------------------------------------------------------- effects -----
def reverb(sig, wet=0.2, room=0.74):
    combs = [(int(SR * d), room) for d in (0.0297, 0.0371, 0.0411, 0.0437)]
    tail = int(SR * 0.9)
    x = sig + [0.0] * tail
    n = len(x)
    acc = [0.0] * n
    for delay, g in combs:
        buf = [0.0] * n
        for i in range(n):
            y = x[i] + (g * buf[i - delay] if i >= delay else 0.0)
            buf[i] = y
            acc[i] += y * 0.25
    for delay, g in ((int(SR * 0.005), 0.7), (int(SR * 0.0017), 0.7)):
        out = [0.0] * n
        for i in range(n):
            xd = acc[i - delay] if i >= delay else 0.0
            yd = out[i - delay] if i >= delay else 0.0
            out[i] = -g * acc[i] + xd + g * yd
        acc = out
    return [x[i] * (1 - wet) + acc[i] * wet for i in range(n)]


def stereo(sig_l, sig_r=None, width_ms=0.35):
    if sig_r is None:
        d = int(SR * width_ms / 1000)
        sig_r = [0.0] * d + sig_l[:len(sig_l) - d] if d else sig_l
    return sig_l, sig_r


def finish(left, right, peak=0.62, fade=0.02):
    n = max(len(left), len(right))
    left = left + [0.0] * (n - len(left))
    right = right + [0.0] * (n - len(right))
    # trim the tail once it is 60 dB below the peak, then fade the last few ms
    thresh = 1e-3 * max(1e-9, max(max(map(abs, left)), max(map(abs, right))))
    end = n
    while end > 1 and abs(left[end - 1]) < thresh and abs(right[end - 1]) < thresh:
        end -= 1
    left, right = left[:end], right[:end]
    m = max(1e-9, max(max(map(abs, left)), max(map(abs, right))))
    k = peak / m
    f = int(SR * fade)
    for i in range(max(0, end - f), end):
        g = (end - i) / f
        left[i] *= g
        right[i] *= g
    return [v * k for v in left], [v * k for v in right]


def render(events, dur, wet=0.2, room=0.74, peak=0.62):
    """events: list of (time, signal_l, signal_r or None, gain)."""
    L, R = silence(dur), silence(dur)
    for at, sl, sr_, g in events:
        l, r = stereo(sl, sr_)
        mix_into(L, l, at, g)
        mix_into(R, r, at, g)
    return finish(reverb(L, wet, room), reverb(R, wet, room * 0.98), peak)


def chime(notes, gap=0.11, dur=1.3, decay=0.55, spread=True, gain=1.0):
    ev = []
    for k, name in enumerate(notes):
        f = NOTE[name]
        det = (-3 + 6 * (k % 2)) if spread else 0
        ev.append((k * gap, bell(f, dur, decay, detune=det), bell(f, dur, decay, detune=-det), gain))
    return ev


# --------------------------------------------------------------- sounds ----
def sounds():
    s = {}
    login = chime(["E5", "B5", "E6", "G#6"], gap=0.16, dur=1.8, decay=0.7)
    login.append((0.0, pad([NOTE["E4"], NOTE["B4"], NOTE["G#5"]], 2.4), None, 1.0))
    s["desktop-login"] = render(login, 2.8, wet=0.28, room=0.8)
    s["theme-demo"] = s["desktop-login"]
    logout = chime(["G#6", "E6", "B5", "E5"], gap=0.15, dur=1.6, decay=0.6, gain=0.9)
    logout.append((0.0, pad([NOTE["E4"], NOTE["B4"]], 1.9), None, 0.8))
    s["desktop-logout"] = render(logout, 2.4, wet=0.28, room=0.8)
    s["service-login"] = render(chime(["B5", "E6"], gap=0.1, dur=1.0), 1.3)
    s["service-logout"] = render(chime(["E6", "B5"], gap=0.1, dur=1.0), 1.3)
    s["message-new-instant"] = render(chime(["B5", "E6"], gap=0.09, dur=0.9, decay=0.42), 1.1, peak=0.55)
    s["message-new-email"] = render(chime(["G#5", "C#6", "E6"], gap=0.08, dur=0.9, decay=0.4), 1.2,
                                    peak=0.55)
    s["message-attention"] = render(chime(["B5", "B5"], gap=0.14, dur=0.8, decay=0.35), 1.1, peak=0.55)
    s["message-highlight"] = s["message-attention"]
    s["dialog-information"] = render(chime(["E6"], dur=1.0, decay=0.5), 1.1, peak=0.5)
    s["dialog-question"] = render(chime(["E5", "B5"], gap=0.12, dur=1.0, decay=0.45), 1.2, peak=0.52)
    warn = [(0.0, bell(NOTE["A4"], 1.2, 0.5), None, 1.0), (0.0, bell(NOTE["C5"], 1.2, 0.5), None, 0.8)]
    s["dialog-warning"] = render(warn, 1.3, peak=0.55)
    s["dialog-warning-auth"] = s["dialog-warning"]
    err = [(0.0, bell(NOTE["E5"], 0.9, 0.35), None, 1.0),
           (0.16, bell(NOTE["B4"], 1.2, 0.5), None, 1.0),
           (0.16, bell(NOTE["B3"], 1.2, 0.6, bright=0.5), None, 0.6)]
    s["dialog-error"] = render(err, 1.5, peak=0.58)
    s["dialog-error-serious"] = s["dialog-error"]
    s["dialog-error-critical"] = s["dialog-error"]
    s["audio-volume-change"] = render([(0.0, bell(NOTE["C#6"], 0.25, 0.08), None, 1.0)], 0.3,
                                      wet=0.08, peak=0.4)
    s["device-added"] = render(chime(["B5", "E6"], gap=0.07, dur=0.7, decay=0.3), 0.9, peak=0.5)
    s["device-removed"] = render(chime(["E6", "B5"], gap=0.07, dur=0.7, decay=0.3), 0.9, peak=0.5)
    s["power-plug"] = render([(0.0, glide(420, 980, 0.3), None, 1.0),
                              (0.22, bell(NOTE["E6"], 0.8, 0.35), None, 0.7)], 1.0, peak=0.5)
    s["power-unplug"] = render([(0.0, glide(980, 420, 0.3), None, 1.0),
                                (0.22, bell(NOTE["E5"], 0.8, 0.35), None, 0.7)], 1.0, peak=0.5)
    low = chime(["C#5", "A4"], gap=0.16, dur=0.9, decay=0.4, spread=False)
    low += [(0.55 + e[0], e[1], e[2], e[3]) for e in chime(["C#5", "A4"], gap=0.16, dur=0.9, decay=0.4,
                                                         spread=False)]
    s["battery-low"] = render(low, 1.8, peak=0.55)
    s["battery-caution"] = s["battery-low"]
    s["battery-full"] = render(chime(["E5", "G#5", "B5", "E6"], gap=0.07, dur=1.2, decay=0.5), 1.5)
    s["completion-success"] = render(chime(["E5", "G#5", "B5"], gap=0.07, dur=1.0, decay=0.42), 1.3)
    s["outcome-success"] = s["completion-success"]
    s["complete-media-burn"] = s["completion-success"]
    fail = [(0.0, bell(NOTE["C5"], 0.8, 0.35), None, 1.0), (0.15, bell(NOTE["B4"], 1.0, 0.45), None, 1.0)]
    s["completion-fail"] = render(fail, 1.3, peak=0.55)
    s["outcome-failure"] = s["completion-fail"]
    s["complete-media-error"] = s["completion-fail"]
    s["completion-partial"] = render(chime(["B5", "G#5"], gap=0.1, dur=0.9, decay=0.4), 1.1, peak=0.52)
    sparkle = [(0.42, bell(NOTE["B6"], 0.5, 0.18), None, 0.25)]
    s["trash-empty"] = render([(0.0, whoosh(), None, 1.0)] + sparkle, 1.0, wet=0.15, peak=0.45)
    s["bell"] = render(chime(["B5"], dur=0.7, decay=0.28), 0.8, peak=0.5)
    s["bell-window-system"] = s["bell"]
    alarm = []
    for rep in range(3):
        alarm += [(rep * 0.9 + e[0], e[1], e[2], e[3]) for e in chime(["E6", "B5", "E6"], gap=0.12,
                                                                    dur=0.8, decay=0.35)]
    s["alarm-clock-elapsed"] = render(alarm, 3.2, peak=0.6)
    call = []
    for rep in range(2):
        call += [(rep * 1.3 + e[0], e[1], e[2], e[3]) for e in chime(["E5", "B5", "E6", "B5"], gap=0.13,
                                                                    dur=0.9, decay=0.4)]
    s["phone-incoming-call"] = render(call, 3.0, peak=0.6)
    s["button-pressed"] = render([(0.0, tick(2400), None, 1.0)], 0.1, wet=0.0, peak=0.35)
    s["button-pressed-modifier"] = render([(0.0, tick(1800), None, 1.0)], 0.1, wet=0.0, peak=0.35)
    return s


# ----------------------------------------------------------------- write ---
def write_wav(path, left, right):
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        frames = bytearray()
        for a, b in zip(left, right):
            frames += struct.pack("<hh", int(max(-1, min(1, a)) * 32767), int(max(-1, min(1, b)) * 32767))
        w.writeframes(bytes(frames))


def build(out_root):
    base = os.path.join(out_root, "sounds", IDS["sounds"])
    if os.path.exists(base):
        shutil.rmtree(base)
    stereo_dir = os.path.join(base, "stereo")
    os.makedirs(stereo_dir)
    ffmpeg = shutil.which("ffmpeg")
    done = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, (left, right) in sounds().items():
            key = id(left)
            if key in done:           # aliases share one rendering
                src, ext = done[key]
                os.symlink(os.path.basename(src), os.path.join(stereo_dir, f"{name}.{ext}"))
                continue
            wav = os.path.join(tmp, name + ".wav")
            write_wav(wav, left, right)
            if ffmpeg:
                dst = os.path.join(stereo_dir, name + ".oga")
                subprocess.run([ffmpeg, "-loglevel", "error", "-y", "-i", wav, "-c:a", "libvorbis",
                                "-q:a", "5", "-f", "ogg", dst], check=True)
                done[key] = (dst, "oga")
            else:
                dst = os.path.join(stereo_dir, name + ".wav")
                shutil.copy(wav, dst)
                done[key] = (dst, "wav")
    with open(os.path.join(base, "index.theme"), "w") as f:
        f.write("[Sound Theme]\n"
                f"Name={NAME}\n"
                f"Comment=Soft glassy chimes from the {NAME} theme\n"
                "Inherits=ocean,freedesktop\n"
                "Directories=stereo\n\n"
                "[stereo]\nOutputProfile=stereo\n")
    return base


if __name__ == "__main__":
    print(build(sys.argv[1]))
