"""In-memory and tiny-file tests for tools/check_audio.py."""

import io
import os
import struct
import tempfile
import unittest
import wave
from contextlib import redirect_stdout

import numpy as np

from tools.check_audio import (
    MAX_FULL_SCALE_SAMPLES,
    MIN_DURATION_S,
    Spec,
    assess,
    check_tree,
    emit,
    expected_specs,
    format_markdown,
    format_table,
    read_wav,
    repo_root,
)


SR = 44100


def sine(frames, sr=SR, amp=0.5, freq=440.0):
    t = np.arange(frames) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float64)


def spec_for(frames, sr=SR, channels=1, note="test tone"):
    return Spec("tone.wav", sr, channels, frames, "test_gen.py", note)


def write_i16(path, codes, sr=SR, channels=1):
    codes = np.asarray(codes, dtype="<i2")
    with wave.open(path, "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(sr)
        handle.writeframes(codes.tobytes())


def write_f32(path, samples, sr=SR, channels=1):
    samples = np.asarray(samples, dtype="<f4")
    data = samples.tobytes()
    block = channels * 4
    fmt = struct.pack("<HHIIHH", 3, channels, sr, sr * block, block, 32)
    chunks = b"fmt " + struct.pack("<I", len(fmt)) + fmt
    chunks += b"data" + struct.pack("<I", len(data)) + data
    if len(data) % 2:
        chunks += b"\x00"
    body = b"WAVE" + chunks
    with open(path, "wb") as handle:
        handle.write(b"RIFF" + struct.pack("<I", len(body)) + body)


class AssessTests(unittest.TestCase):
    def test_good_tone_passes(self):
        frames = SR
        result = assess(sine(frames, amp=0.5), SR, spec_for(frames))
        self.assertTrue(result.ok, result.failures)
        self.assertAlmostEqual(result.peak_db, 20 * np.log10(0.5), places=2)
        self.assertGreater(result.rms_db, -60)
        self.assertEqual(result.sample_rate, SR)
        self.assertEqual(result.channels, 1)
        self.assertAlmostEqual(result.duration, 1.0, places=3)

    def test_silent_fails(self):
        result = assess(np.zeros(SR), SR, spec_for(SR))
        self.assertFalse(result.ok)
        self.assertTrue(any("silent" in failure for failure in result.failures))

    def test_clipped_fails(self):
        t = np.arange(SR) / SR
        clipped = np.clip(np.sin(2 * np.pi * 440 * t) * 4, -1, 1)
        result = assess(clipped, SR, spec_for(SR))
        self.assertFalse(result.ok)
        self.assertTrue(any("clip" in failure for failure in result.failures))
        self.assertGreater(np.count_nonzero(np.abs(clipped) >= 1.0), MAX_FULL_SCALE_SAMPLES)

    def test_peak_above_full_scale_fails(self):
        result = assess(sine(SR, amp=1.5), SR, spec_for(SR))
        self.assertFalse(result.ok)
        self.assertTrue(any("0 dBFS" in failure for failure in result.failures))

    def test_nan_fails(self):
        audio = sine(SR)
        audio[10] = np.nan
        result = assess(audio, SR, spec_for(SR))
        self.assertFalse(result.ok)
        self.assertTrue(any("NaN" in failure or "non-finite" in failure for failure in result.failures))

    def test_inf_fails(self):
        audio = sine(SR)
        audio[3] = np.inf
        result = assess(audio, SR, spec_for(SR))
        self.assertFalse(result.ok)
        self.assertTrue(any("non-finite" in failure for failure in result.failures))

    def test_wrong_sample_rate_fails(self):
        result = assess(sine(SR), 48000, spec_for(SR, sr=SR))
        self.assertFalse(result.ok)
        self.assertTrue(any("sample rate" in failure for failure in result.failures))

    def test_nonsense_sample_rate_fails(self):
        result = assess(sine(32), 7, spec_for(32, sr=7))
        self.assertFalse(result.ok)
        self.assertTrue(any("not a sane audio rate" in failure for failure in result.failures))

    def test_wrong_length_fails(self):
        result = assess(sine(int(0.2 * SR)), SR, spec_for(SR, note="t(1.0)"))
        self.assertFalse(result.ok)
        self.assertTrue(any("duration" in failure for failure in result.failures))

    def test_a_few_milliseconds_of_slack_passes(self):
        frames = SR + int(0.010 * SR)
        result = assess(sine(frames), SR, spec_for(SR))
        self.assertTrue(result.ok, result.failures)

    def test_fifty_milliseconds_off_fails(self):
        frames = SR + int(0.050 * SR)
        result = assess(sine(frames), SR, spec_for(SR))
        self.assertFalse(result.ok)

    def test_below_global_minimum_fails_even_if_spec_matches(self):
        frames = int(0.01 * SR)
        self.assertLess(frames / SR, MIN_DURATION_S)
        result = assess(sine(frames), SR, spec_for(frames))
        self.assertFalse(result.ok)
        self.assertTrue(any("minimum" in failure for failure in result.failures))

    def test_shortest_generator_length_passes(self):
        # neon-snake attempt is 0.04s, the shortest file the specs describe.
        frames = int(0.04 * SR)
        result = assess(sine(frames), SR, spec_for(frames))
        self.assertTrue(result.ok, result.failures)

    def test_channel_mismatch_fails(self):
        stereo = np.column_stack([sine(SR), sine(SR, amp=0.25)])
        result = assess(stereo, SR, spec_for(SR, channels=1))
        self.assertFalse(result.ok)
        self.assertEqual(result.channels, 2)
        self.assertTrue(any("channel" in failure for failure in result.failures))


class ReaderTests(unittest.TestCase):
    def test_pcm_good_tone_roundtrip(self):
        audio = sine(SR, amp=0.4)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "good.wav")
            write_i16(path, np.round(audio * 32767).astype("<i2"))
            samples, sample_rate, full = read_wav(path)
        self.assertEqual(sample_rate, SR)
        self.assertEqual(samples.shape, (SR, 1))
        self.assertEqual(full, 0)
        result = assess(samples, sample_rate, spec_for(SR), full_scale_count=full)
        self.assertTrue(result.ok, result.failures)

    def test_int16_full_scale_codes_count_as_clipping(self):
        # 32767/32768 is just under 1.0, so the float view is not above 0 dBFS.
        # The codes are still full scale and must fail the clip check.
        codes = np.full(200, 32767, dtype="<i2")
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "clipped.wav")
            write_i16(path, codes)
            samples, sample_rate, full = read_wav(path)
        self.assertGreater(full, MAX_FULL_SCALE_SAMPLES)
        self.assertLess(float(np.max(np.abs(samples))), 1.0)
        result = assess(samples, sample_rate, spec_for(len(codes)), full_scale_count=full)
        self.assertFalse(result.ok)
        self.assertTrue(any("clip" in failure for failure in result.failures))
        self.assertFalse(any("above 0 dBFS" in failure for failure in result.failures))

    def test_silent_pcm_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "silent.wav")
            write_i16(path, np.zeros(SR, dtype="<i2"))
            samples, sample_rate, full = read_wav(path)
        result = assess(samples, sample_rate, spec_for(SR), full_scale_count=full)
        self.assertFalse(result.ok)
        self.assertTrue(any("silent" in failure for failure in result.failures))

    def test_float_nan_and_inf_survive_the_reader(self):
        audio = sine(SR).astype(np.float32)
        audio[4] = np.nan
        audio[5] = np.inf
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "bad.wav")
            write_f32(path, audio)
            samples, sample_rate, _full = read_wav(path)
        self.assertTrue(np.isnan(samples).any())
        self.assertTrue(np.isinf(samples).any())
        result = assess(samples, sample_rate, spec_for(SR))
        self.assertFalse(result.ok)
        self.assertTrue(any("non-finite" in failure for failure in result.failures))

    def test_float_good_tone_passes(self):
        audio = sine(SR, amp=0.25)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "float.wav")
            write_f32(path, audio)
            samples, sample_rate, full = read_wav(path)
        self.assertEqual(full, 0)
        result = assess(samples, sample_rate, spec_for(SR), full_scale_count=full)
        self.assertTrue(result.ok, result.failures)

    def test_stereo_pcm_shape(self):
        left = np.full(100, 1000, dtype="<i2")
        right = np.full(100, -2000, dtype="<i2")
        interleaved = np.column_stack([left, right]).reshape(-1)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "stereo.wav")
            write_i16(path, interleaved, channels=2)
            samples, _sample_rate, _full = read_wav(path)
        self.assertEqual(samples.shape, (100, 2))
        self.assertGreater(samples[0, 0], 0)
        self.assertLess(samples[0, 1], 0)


class TreeTests(unittest.TestCase):
    def test_missing_and_unexpected_and_good(self):
        audio = sine(SR, amp=0.3)
        with tempfile.TemporaryDirectory() as directory:
            write_i16(os.path.join(directory, "good.wav"), np.round(audio * 32767).astype("<i2"))
            write_i16(os.path.join(directory, "extra.wav"), np.zeros(SR, dtype="<i2"))
            specs = [spec_for(SR)]
            specs[0] = Spec("good.wav", SR, 1, SR, "test_gen.py", "1s")
            missing = Spec("gone.wav", SR, 1, SR, "test_gen.py", "1s")
            results = check_tree(directory, [specs[0], missing])
        by_path = {result.path: result for result in results}
        self.assertTrue(by_path["good.wav"].ok, by_path["good.wav"].failures)
        self.assertFalse(by_path["gone.wav"].ok)
        self.assertTrue(any("missing" in failure for failure in by_path["gone.wav"].failures))
        self.assertFalse(by_path["extra.wav"].ok)
        self.assertTrue(any("unexpected" in failure for failure in by_path["extra.wav"].failures))

    def test_inconsistent_rates_fail_the_group(self):
        with tempfile.TemporaryDirectory() as directory:
            write_i16(os.path.join(directory, "a.wav"), np.round(sine(SR, amp=0.4) * 32767).astype("<i2"), sr=SR)
            write_i16(
                os.path.join(directory, "b.wav"),
                np.round(sine(22050, sr=22050, amp=0.4) * 32767).astype("<i2"),
                sr=22050,
            )
            specs = [
                Spec("a.wav", SR, 1, SR, "gen.py", "1s"),
                Spec("b.wav", 22050, 1, 22050, "gen.py", "1s"),
            ]
            results = check_tree(directory, specs)
        self.assertTrue(all(not result.ok for result in results))
        self.assertTrue(any("not consistent" in failure for result in results for failure in result.failures))

    def test_garbage_is_unreadable(self):
        with tempfile.TemporaryDirectory() as directory:
            with open(os.path.join(directory, "nope.wav"), "wb") as handle:
                handle.write(b"this is not a wav")
            results = check_tree(directory, [Spec("nope.wav", SR, 1, SR, "gen.py", "1s")])
        self.assertFalse(results[0].ok)
        self.assertTrue(any("unreadable" in failure for failure in results[0].failures))

    def test_table_columns_and_summary(self):
        good = assess(sine(SR), SR, spec_for(SR))
        bad = assess(np.zeros(SR), SR, spec_for(SR))
        text = format_table([good, bad])
        for column in ("file", "sr", "ch", "duration", "peak dBFS", "RMS dBFS", "PASS/FAIL"):
            self.assertIn(column, text)
        self.assertIn("PASS", text)
        self.assertIn("FAIL", text)
        markdown = format_markdown([good, bad])
        self.assertIn("| file | sr | ch | duration | peak dBFS | RMS dBFS | PASS/FAIL |", markdown)
        self.assertIn("tone.wav", markdown)

    def test_step_summary_is_appended_when_set(self):
        good = assess(sine(SR), SR, spec_for(SR))
        with tempfile.TemporaryDirectory() as directory:
            summary = os.path.join(directory, "summary.md")
            previous = os.environ.get("GITHUB_STEP_SUMMARY")
            os.environ["GITHUB_STEP_SUMMARY"] = summary
            try:
                with redirect_stdout(io.StringIO()):
                    code = emit([good])
            finally:
                if previous is None:
                    os.environ.pop("GITHUB_STEP_SUMMARY", None)
                else:
                    os.environ["GITHUB_STEP_SUMMARY"] = previous
            self.assertEqual(code, 0)
            with open(summary, encoding="utf-8") as handle:
                body = handle.read()
        self.assertIn("Rendered audio", body)
        self.assertIn("PASS", body)


class SpecTests(unittest.TestCase):
    def test_expected_frames_match_the_generator_math(self):
        specs = {item.path: item for item in expected_specs(repo_root())}
        expected = {
            "sounds/servo_whir.wav": 52920,
            "sounds/machine_hum.wav": 176400,
            "sounds/heartbeat.wav": 44100,
            "sounds/mech_breath.wav": 132300,
            "sounds/metal_hit.wav": 88200,
            "sounds/circuit_glitch.wav": 88200,
            "sounds/granular_cloud.wav": 176400,
            "sounds/btc_blocks_melody.wav": 260269,
            "sketches/01-circuit-wake.wav": 3160974,
            "sketches/02-servo-pulse.wav": 3295472,
            "sketches/03-bionic-dawn.wav": 2974745,
            "sketches/02-servo-pulse-v2.wav": 3295472,
            "game/title_loop.wav": 1128960,
            "game/premiere/theme_musicbox.wav": 194040,
            "game/premiere/theme_full.wav": 458640,
            "game/premiere/window_look.wav": 458640,
            "game/premiere/cabin_loop.wav": 6350400,
            "game/premiere/zero_g_layer.wav": 6350400,
            "game/premiere/wake.wav": 110250,
            "game/premiere/float_start.wav": 88200,
            "game/premiere/cockpit_reach.wav": 52920,
            "game/neon-snake/level1_loop.wav": 3386880,
            "game/neon-snake/speedup.wav": 13888,
            "game/neon-snake/death.wav": 22050,
            "game/neon-snake/pickup.wav": 10143,
            "game/neon-snake/win.wav": 38367,
            "game/neon-snake/attempt.wav": 1764,
            "game/neon-snake/level2_loop.wav": 3386880,
            "game/neon-snake/montage_loop.wav": 1128960,
            "ambient/space_drift.wav": 5644800,
            "ambient/machine_sleep.wav": 6272000,
        }
        self.assertEqual(set(specs), set(expected))
        for path, frames in expected.items():
            self.assertEqual(specs[path].frames, frames, path)
            self.assertEqual(specs[path].sample_rate, 44100, path)
            self.assertEqual(specs[path].channels, 1, path)
            self.assertTrue(specs[path].note, path)
            self.assertTrue(specs[path].generator.endswith(".py"), path)


if __name__ == "__main__":
    unittest.main()
