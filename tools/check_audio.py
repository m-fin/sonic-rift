#!/usr/bin/env python3
"""Check the WAVs the sonicrift generators render.

A file passes when it is a readable PCM or IEEE-float WAV, the sample rate and
channel count are sane and match what that generator writes (44100 Hz, mono),
the duration is longer than 20 ms and within 1% or 15 ms of the length derived
from the generator, RMS is above -60 dBFS, peak is at or below 0 dBFS, at most
8 samples sit at full scale, and float data has no NaN or infinity.

Durations are computed from the same expressions as the scripts (bar counts,
``t(seconds)``, and the Bitcoin block-size map). They are not guessed.

``bionic/`` is skipped: that piece needs the Kokoro model and is not part of CI.
"""

from __future__ import annotations

import json
import math
import os
import struct
import sys
import wave
from dataclasses import dataclass, field

import numpy as np

MIN_DURATION_S = 0.02
DURATION_TOLERANCE_RATIO = 0.01
DURATION_TOLERANCE_FLOOR_S = 0.015
RMS_FLOOR_DB = -60.0
MAX_FULL_SCALE_SAMPLES = 8
GLOBAL_MAX_DURATION_S = 600.0
SANE_SAMPLE_RATES = frozenset(
    {8000, 11025, 16000, 22050, 32000, 44100, 48000, 88200, 96000, 176400, 192000}
)
SANE_CHANNELS = frozenset({1, 2})

_IEEE_FLOAT = 0x0003
_PCM = 0x0001
_EXTENSIBLE = 0xFFFE
# GUID layout used in WAVEFORMATEXTENSIBLE (mixed endian).
_PCM_GUID = bytes.fromhex("0100000000001000800000aa00389b71")
_FLOAT_GUID = bytes.fromhex("0300000000001000800000aa00389b71")


@dataclass(frozen=True)
class Spec:
    """What one generator output is supposed to be."""

    path: str
    sample_rate: int
    channels: int
    frames: int
    generator: str
    note: str


@dataclass
class Result:
    path: str
    sample_rate: int | None = None
    channels: int | None = None
    duration: float | None = None
    peak_db: float | None = None
    rms_db: float | None = None
    failures: list[str] = field(default_factory=list)
    generator: str = ""

    @property
    def ok(self) -> bool:
        return not self.failures


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def duration_window(frames: int, sample_rate: int) -> tuple[float, float]:
    """Inclusive seconds around ``frames / sample_rate``.

    The slack is 1% of the expected length, or 15 ms, whichever is larger.
    A dropped bar fails. A one-frame rounding difference does not.
    """

    expected = frames / sample_rate
    slack = max(expected * DURATION_TOLERANCE_RATIO, DURATION_TOLERANCE_FLOOR_S)
    return expected - slack, expected + slack


def _btc_frames(root: str, sample_rate: int) -> int:
    """Note lengths in ``sounds/make_sounds.py``: size maps to 0.15–0.6 s."""

    path = os.path.join(root, "sounds", "btc_blocks.json")
    with open(path, encoding="utf-8") as handle:
        blocks = json.load(handle)
    total = 0
    for block in blocks:
        seconds = float(np.interp(block["size"], [5e5, 2.5e6], [0.15, 0.6]))
        total += int(seconds * sample_rate)
    return total


def expected_specs(root: str) -> list[Spec]:
    """One spec per WAV the CI generators leave on disk."""

    sr = 44100
    specs: list[Spec] = []

    def add(path: str, frames: int, generator: str, note: str) -> None:
        specs.append(Spec(path, sr, 1, int(frames), generator, note))

    sounds = "sounds/make_sounds.py"
    add("sounds/servo_whir.wav", int(1.2 * sr), sounds, "t(1.2)")
    add("sounds/machine_hum.wav", int(4 * sr), sounds, "t(4)")
    add("sounds/heartbeat.wav", int(sr * 1.0), sounds, "int(SR * 1.0) samples")
    add("sounds/mech_breath.wav", int(3 * sr), sounds, "t(3)")
    add("sounds/metal_hit.wav", int(2 * sr), sounds, "t(2)")
    add("sounds/circuit_glitch.wav", int(2 * sr), sounds, "t(2)")
    add("sounds/granular_cloud.wav", sr * 4, sounds, "SR * 4 samples")
    add(
        "sounds/btc_blocks_melody.wav",
        _btc_frames(root, sr),
        sounds,
        "sum of notes, duration = interp(block size, [5e5, 2.5e6] -> [0.15, 0.6])",
    )

    def sketch_frames(bpm: int, bars: int) -> int:
        # sketches/build.py: L = int(bars * 4 * (60/bpm) * SR) + 2 seconds.
        beat = 60 / bpm
        return int(bars * (4 * beat) * sr) + sr * 2

    built = "sketches/build.py"
    add("sketches/01-circuit-wake.wav", sketch_frames(124, 36), built, "124 BPM, 36 bars, plus 2s tail")
    add("sketches/02-servo-pulse.wav", sketch_frames(132, 40), built, "132 BPM, 40 bars, plus 2s tail")
    add("sketches/03-bionic-dawn.wav", sketch_frames(110, 30), built, "110 BPM, 30 bars, plus 2s tail")
    add(
        "sketches/02-servo-pulse-v2.wav",
        sketch_frames(132, 40),
        "sketches/servo_pulse_v2.py",
        "same length as 02-servo-pulse (132 BPM, 40 bars, plus 2s tail)",
    )

    sixteenth = 60 / 150 / 4
    add(
        "game/title_loop.wav",
        int(16 * 16 * sixteenth * sr),
        "game/title_loop.py",
        "16 bars of 16th notes at 150 BPM",
    )

    beat = 60 / 75
    bar = 4 * beat
    premiere = "game/premiere/make.py"
    add("game/premiere/theme_musicbox.wav", int((6 * (beat / 2) + 2) * sr), premiere, "6 steps plus 2s tail")
    theme_full = int((8 * beat + 4) * sr)
    add("game/premiere/theme_full.wav", theme_full, premiere, "8 beats plus 4s tail")
    add("game/premiere/window_look.wav", theme_full, premiere, "same buffer as theme_full")
    cabin = int(45 * bar * sr)
    add("game/premiere/cabin_loop.wav", cabin, premiere, "45 bars at 75 BPM")
    add("game/premiere/zero_g_layer.wav", cabin, premiere, "45 bars at 75 BPM")
    add("game/premiere/wake.wav", int(2.5 * sr), premiere, "2.5s rise")
    add("game/premiere/float_start.wav", int(2 * sr), premiere, "2s pad")
    add("game/premiere/cockpit_reach.wav", int(1.2 * sr), premiere, "1.2s arpeggio")

    neon = "game/neon-snake/make.py"
    add("game/neon-snake/level1_loop.wav", int(48 * 16 * sixteenth * sr), neon, "48 bars of 16th notes at 150 BPM")
    add("game/neon-snake/speedup.wav", 7 * int(0.045 * sr), neon, "7 notes of 0.045s")
    add("game/neon-snake/death.wav", int(0.5 * sr), neon, "0.5s fall")
    add("game/neon-snake/pickup.wav", int(0.05 * sr) + int(0.18 * sr), neon, "0.05s blip plus 0.18s blip")
    add("game/neon-snake/win.wav", 3 * int(0.09 * sr) + int(0.6 * sr), neon, "3 notes of 0.09s plus 0.6s")
    add("game/neon-snake/attempt.wav", int(0.04 * sr), neon, "0.04s hit")
    neon2 = "game/neon-snake/make2.py"
    add("game/neon-snake/level2_loop.wav", int(48 * 16 * sixteenth * sr), neon2, "48 bars of 16th notes at 150 BPM")
    add("game/neon-snake/montage_loop.wav", int(16 * 16 * sixteenth * sr), neon2, "16 bars of 16th notes at 150 BPM")

    def ambient_frames(bpm: int, chords: int) -> int:
        # ambient/make.py: b4 = 4 * 60/bpm * 4; L = int(b4 * len(prog) * SR)
        four_bars = 4 * 60 / bpm * 4
        return int(four_bars * chords * sr)

    ambient = "ambient/make.py"
    add("ambient/space_drift.wav", ambient_frames(60, 8), ambient, "8 chords of 4 bars at 60 BPM")
    add("ambient/machine_sleep.wav", ambient_frames(54, 8), ambient, "8 chords of 4 bars at 54 BPM")
    return specs


def find_wavs(root: str) -> list[str]:
    """Relative POSIX paths of WAVs under ``root``, excluding ``bionic/``."""

    root = os.path.abspath(root)
    skip = {".git", "__pycache__", "bionic"}
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in skip and not name.startswith(".")]
        for name in filenames:
            if name.lower().endswith(".wav"):
                rel = os.path.relpath(os.path.join(dirpath, name), root)
                found.append(rel.replace(os.sep, "/"))
    return sorted(found)


def _pcm_audio(raw: bytes, width: int) -> tuple[np.ndarray, int]:
    """Map integer PCM bytes to float in [-1, 1] and count full-scale codes."""

    if width == 1:
        codes = np.frombuffer(raw, dtype=np.uint8)
        full = int(np.count_nonzero((codes == 0) | (codes == 255)))
        return (codes.astype(np.float64) - 128.0) / 128.0, full
    if width == 2:
        codes = np.frombuffer(raw, dtype="<i2")
        full = int(np.count_nonzero((codes == -32768) | (codes == 32767)))
        return codes.astype(np.float64) / 32768.0, full
    if width == 3:
        packed = np.frombuffer(raw, dtype=np.uint8)
        if packed.size % 3:
            raise wave.Error("truncated 24-bit frames")
        triples = packed.reshape(-1, 3).astype(np.int32)
        codes = triples[:, 0] | (triples[:, 1] << 8) | (triples[:, 2] << 16)
        codes = np.where(codes >= 0x800000, codes - 0x1000000, codes)
        full = int(np.count_nonzero((codes == -8388608) | (codes == 8388607)))
        return codes.astype(np.float64) / 8388608.0, full
    if width == 4:
        codes = np.frombuffer(raw, dtype="<i4")
        full = int(np.count_nonzero((codes == -2147483648) | (codes == 2147483647)))
        return codes.astype(np.float64) / 2147483648.0, full
    raise wave.Error(f"unsupported sample width {width}")


def _read_pcm_wave(path: str) -> tuple[np.ndarray, int, int]:
    with wave.open(path, "rb") as handle:
        channels = handle.getnchannels()
        sample_rate = handle.getframerate()
        width = handle.getsampwidth()
        raw = handle.readframes(handle.getnframes())
    if channels < 1 or len(raw) % (channels * width):
        raise wave.Error("truncated frames")
    audio, full = _pcm_audio(raw, width)
    if audio.size % channels:
        raise wave.Error("truncated frames")
    return audio.reshape(-1, channels), sample_rate, full


def _riff_chunks(path: str) -> tuple[bytes, bytes]:
    with open(path, "rb") as handle:
        blob = handle.read()
    if len(blob) < 12 or blob[:4] != b"RIFF" or blob[8:12] != b"WAVE":
        raise wave.Error("not a RIFF WAVE file")
    fmt = data = None
    offset = 12
    while offset + 8 <= len(blob):
        chunk_id, size = struct.unpack_from("<4sI", blob, offset)
        start = offset + 8
        end = start + size
        if end > len(blob):
            raise wave.Error(f"truncated {chunk_id!r} chunk")
        payload = blob[start:end]
        if chunk_id == b"fmt ":
            fmt = payload
        elif chunk_id == b"data":
            data = payload
        offset = end + (size & 1)
    if fmt is None or data is None:
        raise wave.Error("missing fmt or data chunk")
    return fmt, data


def _read_float_wave(path: str) -> tuple[np.ndarray, int, int]:
    fmt, data = _riff_chunks(path)
    if len(fmt) < 16:
        raise wave.Error("short fmt chunk")
    tag, channels, sample_rate, _byte_rate, _align, bits = struct.unpack("<HHIIHH", fmt[:16])
    audio_format = tag
    if tag == _EXTENSIBLE:
        if len(fmt) < 40:
            raise wave.Error("short extensible fmt chunk")
        guid = fmt[24:40]
        if guid == _FLOAT_GUID:
            audio_format = _IEEE_FLOAT
        elif guid == _PCM_GUID:
            audio_format = _PCM
        else:
            raise wave.Error("unsupported extensible subtype")
    if audio_format == _PCM:
        return _read_pcm_wave(path)
    if audio_format != _IEEE_FLOAT:
        raise wave.Error(f"unsupported format {tag}")
    if bits == 32:
        samples = np.frombuffer(data, dtype="<f4").astype(np.float64)
    elif bits == 64:
        samples = np.frombuffer(data, dtype="<f8").astype(np.float64)
    else:
        raise wave.Error(f"unsupported float width {bits}")
    if channels < 1 or samples.size % channels:
        raise wave.Error("truncated float frames")
    audio = samples.reshape(-1, channels)
    finite = audio[np.isfinite(audio)]
    full = int(np.count_nonzero(np.abs(finite) >= 1.0)) if finite.size else 0
    return audio, sample_rate, full


def read_wav(path: str) -> tuple[np.ndarray, int, int]:
    """Return ``(samples, sample_rate, full_scale_count)``.

    ``samples`` is float64 with shape ``(frames, channels)`` and nominal range
    [-1, 1]. PCM is read with the stdlib ``wave`` module. IEEE float (which
    ``wave`` rejects) is decoded directly so NaNs survive for the checker.
    ``full_scale_count`` counts integer codes at the format's extremes, or
    float samples with absolute value at or above 1.
    """

    try:
        return _read_pcm_wave(path)
    except wave.Error as exc:
        message = str(exc).lower()
        if "unknown format" not in message and "extended format" not in message:
            raise
        try:
            return _read_float_wave(path)
        except wave.Error as float_exc:
            raise wave.Error(f"{exc}; {float_exc}") from float_exc


def _db(level: float) -> float:
    if level > 0:
        return float(20.0 * math.log10(level))
    return float("-inf")


def assess(
    samples,
    sample_rate: int,
    spec: Spec | None = None,
    full_scale_count: int | None = None,
    path: str | None = None,
) -> Result:
    """Judge an in-memory signal. ``samples`` is float, shape (frames,) or (frames, channels)."""

    name = path or (spec.path if spec else "?")
    generator = spec.generator if spec else ""
    failures: list[str] = []
    try:
        audio = np.asarray(samples, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        return Result(name, failures=[f"unreadable: {exc}"], generator=generator)
    if audio.ndim == 1:
        audio = audio.reshape(-1, 1)
    if audio.ndim != 2 or audio.shape[1] < 1:
        return Result(name, failures=[f"unreadable: bad shape {audio.shape}"], generator=generator)

    frames, channels = int(audio.shape[0]), int(audio.shape[1])
    duration = (frames / sample_rate) if sample_rate else None
    finite = bool(audio.size) and bool(np.isfinite(audio).all())
    peak_db = None
    rms_db = None
    if finite and audio.size:
        peak = float(np.max(np.abs(audio)))
        rms = float(np.sqrt(np.mean(np.square(audio))))
        peak_db = _db(peak)
        rms_db = _db(rms)
        if full_scale_count is None:
            full_scale_count = int(np.count_nonzero(np.abs(audio) >= 1.0))
        if peak > 1.0:
            failures.append(f"peak {peak_db:.2f} dBFS is above 0 dBFS")
        if full_scale_count > MAX_FULL_SCALE_SAMPLES:
            failures.append(
                f"hard clipping: {full_scale_count} samples at full scale "
                f"(limit {MAX_FULL_SCALE_SAMPLES})"
            )
        if rms_db < RMS_FLOOR_DB:
            shown = "-inf" if math.isinf(rms_db) else f"{rms_db:.2f}"
            failures.append(f"silent: RMS {shown} dBFS is below {RMS_FLOOR_DB:.1f} dBFS")
    else:
        if not finite:
            bad = int(audio.size - np.isfinite(audio).sum()) if audio.size else 0
            failures.append(f"non-finite samples: {bad} NaN/inf")
        elif frames == 0:
            failures.append("no audio frames")

    if not isinstance(sample_rate, (int, np.integer)) or sample_rate <= 0:
        failures.append(f"sample rate {sample_rate} is not a sane audio rate")
    elif sample_rate not in SANE_SAMPLE_RATES:
        failures.append(f"sample rate {sample_rate} is not a sane audio rate")
    if spec is not None and sample_rate != spec.sample_rate:
        failures.append(
            f"sample rate {sample_rate} does not match {spec.generator} "
            f"(expected {spec.sample_rate})"
        )
    if channels not in SANE_CHANNELS:
        failures.append(f"channel count {channels} is not sane (expected 1 or 2)")
    if spec is not None and channels != spec.channels:
        failures.append(
            f"channel count {channels} does not match {spec.generator} "
            f"(expected {spec.channels})"
        )

    if duration is None:
        failures.append("duration is unknown")
    else:
        if not duration > MIN_DURATION_S:
            failures.append(
                f"duration {duration:.3f}s is not above the {MIN_DURATION_S:.3f}s minimum"
            )
        if spec is not None and spec.sample_rate > 0:
            low, high = duration_window(spec.frames, spec.sample_rate)
            if not low <= duration <= high:
                failures.append(
                    f"duration {duration:.3f}s outside {max(low, 0):.3f}-{high:.3f}s ({spec.note})"
                )
        elif spec is None and duration > GLOBAL_MAX_DURATION_S:
            failures.append(f"duration {duration:.3f}s is longer than {GLOBAL_MAX_DURATION_S:.0f}s")

    return Result(name, int(sample_rate) if sample_rate else None, channels, duration, peak_db, rms_db, failures, generator)


def _check_unexpected(root: str, rel: str) -> Result:
    path = os.path.join(root, rel)
    try:
        samples, sample_rate, full = read_wav(path)
    except Exception as exc:
        return Result(rel, failures=[f"unexpected WAV and unreadable: {exc}"])
    result = assess(samples, sample_rate, spec=None, full_scale_count=full, path=rel)
    result.failures.insert(0, "unexpected WAV (no duration bound from a generator)")
    return result


def _mark_inconsistent(results: list[Result]) -> None:
    groups: dict[str, list[Result]] = {}
    for result in results:
        if result.generator and result.sample_rate is not None and result.channels is not None:
            groups.setdefault(result.generator, []).append(result)
    for generator, items in groups.items():
        rates = sorted({item.sample_rate for item in items})
        channels = sorted({item.channels for item in items})
        if len(rates) == 1 and len(channels) == 1:
            continue
        message = (
            f"{generator} outputs are not consistent "
            f"(sample rates {rates}, channels {channels})"
        )
        for item in items:
            item.failures.append(message)


def check_tree(root: str, specs: list[Spec] | None = None) -> list[Result]:
    root = os.path.abspath(root)
    if specs is None:
        specs = expected_specs(root)
    found = set(find_wavs(root))
    results: list[Result] = []
    for spec in specs:
        if spec.path not in found:
            results.append(
                Result(spec.path, failures=[f"missing WAV from {spec.generator}"], generator=spec.generator)
            )
            continue
        try:
            samples, sample_rate, full = read_wav(os.path.join(root, spec.path))
        except Exception as exc:
            results.append(Result(spec.path, failures=[f"unreadable: {exc}"], generator=spec.generator))
            continue
        results.append(assess(samples, sample_rate, spec, full_scale_count=full))
    known = {spec.path for spec in specs}
    for rel in sorted(found - known):
        results.append(_check_unexpected(root, rel))
    _mark_inconsistent(results)
    return results


def _fmt_db(value: float | None) -> str:
    if value is None:
        return "-"
    if math.isinf(value):
        return "-inf"
    return f"{value:.2f}"


def _fmt_duration(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.3f}"


def format_table(results: list[Result]) -> str:
    headers = ("file", "sr", "ch", "duration", "peak dBFS", "RMS dBFS", "PASS/FAIL")
    rows = []
    for result in results:
        rows.append(
            (
                result.path,
                "-" if result.sample_rate is None else str(result.sample_rate),
                "-" if result.channels is None else str(result.channels),
                _fmt_duration(result.duration),
                _fmt_db(result.peak_db),
                _fmt_db(result.rms_db),
                "PASS" if result.ok else "FAIL",
            )
        )
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def line(columns: tuple[str, ...]) -> str:
        parts = []
        for index, (cell, width) in enumerate(zip(columns, widths)):
            parts.append(cell.ljust(width) if index == 0 else cell.rjust(width))
        return "  ".join(parts)

    passed = sum(result.ok for result in results)
    failed = len(results) - passed
    lines = [line(headers), line(tuple("-" * width for width in widths))]
    lines.extend(line(row) for row in rows)
    lines.append(f"{passed} passed, {failed} failed")
    if failed:
        lines.append("")
        for result in results:
            if result.ok:
                continue
            for failure in result.failures:
                lines.append(f"FAIL {result.path}: {failure}")
    return "\n".join(lines)


def format_markdown(results: list[Result]) -> str:
    passed = sum(result.ok for result in results)
    failed = len(results) - passed
    lines = [
        "### Rendered audio",
        "",
        f"{passed} passed, {failed} failed. "
        f"RMS above {RMS_FLOOR_DB:.0f} dBFS, peak at or below 0 dBFS, "
        f"at most {MAX_FULL_SCALE_SAMPLES} full-scale samples, "
        f"duration above {MIN_DURATION_S * 1000:.0f} ms and within "
        f"{DURATION_TOLERANCE_RATIO:.0%} or {DURATION_TOLERANCE_FLOOR_S * 1000:.0f} ms "
        "of the length each generator writes.",
        "",
        "| file | sr | ch | duration | peak dBFS | RMS dBFS | PASS/FAIL |",
        "|---|---:|---:|---:|---:|---:|:---:|",
    ]
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        cells = (
            f"`{result.path}`",
            "-" if result.sample_rate is None else str(result.sample_rate),
            "-" if result.channels is None else str(result.channels),
            _fmt_duration(result.duration),
            _fmt_db(result.peak_db),
            _fmt_db(result.rms_db),
            status,
        )
        lines.append("| " + " | ".join(cells) + " |")
    if failed:
        lines.extend(["", "### Failures", ""])
        for result in results:
            if result.ok:
                continue
            for failure in result.failures:
                lines.append(f"- `{result.path}`: {failure}")
    lines.append("")
    return "\n".join(lines)


def emit(results: list[Result]) -> int:
    print(format_table(results))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(format_markdown(results))
    return 0 if all(result.ok for result in results) else 1


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) > 1 or (argv and argv[0] in {"-h", "--help"}):
        print("usage: python tools/check_audio.py [root]", file=sys.stderr)
        return 2
    root = argv[0] if argv else repo_root()
    return emit(check_tree(root))


if __name__ == "__main__":
    sys.exit(main())
