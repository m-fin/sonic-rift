"""Tests for the sketches gallery drift check and index link check."""

import os
import tempfile
import unittest

import numpy as np

from tools.check_sketches import (
    check_drift,
    check_links,
    check_sketches,
    load_build,
    repo_root,
)


def write_matching_gallery(root):
    sketches = os.path.join(root, "sketches")
    os.makedirs(sketches, exist_ok=True)
    load_build().write_gallery(sketches)
    return sketches


def song_with_noise():
    song = dict(load_build().SONGS["01-circuit-wake"])
    song["bars"] = 4
    return song


class DriftTests(unittest.TestCase):
    def test_committed_gallery_matches_build(self):
        self.assertEqual(check_drift(repo_root()), [])

    def test_rebuilding_twice_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            load_build().write_gallery(first)
            load_build().write_gallery(second)
            names = sorted(os.listdir(first))
            self.assertEqual(names, sorted(os.listdir(second)))
            self.assertGreaterEqual(len(names), 4)
            for name in names:
                with open(os.path.join(first, name), "rb") as handle:
                    left = handle.read()
                with open(os.path.join(second, name), "rb") as handle:
                    right = handle.read()
                self.assertEqual(left, right, name)

    def test_edited_page_fails_with_a_diff(self):
        with tempfile.TemporaryDirectory() as root:
            sketches = write_matching_gallery(root)
            path = os.path.join(sketches, "index.html")
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            self.assertIn("Circuit Wake", text)
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text.replace("Circuit Wake", "Circuit Brake"))
            failures = check_drift(root)
        self.assertEqual(len(failures), 1)
        self.assertIn("sketches/index.html differs from sketches/build.py output", failures[0])
        self.assertIn("--- sketches/index.html (committed)", failures[0])
        self.assertIn("+++ sketches/index.html (build.py)", failures[0])
        self.assertIn("Circuit Brake", failures[0])
        self.assertIn("Circuit Wake", failures[0])

    def test_missing_page_fails(self):
        with tempfile.TemporaryDirectory() as root:
            sketches = write_matching_gallery(root)
            os.remove(os.path.join(sketches, "03-bionic-dawn.html"))
            failures = check_drift(root)
        self.assertTrue(any("sketches/03-bionic-dawn.html is missing" in failure for failure in failures))
        self.assertTrue(all("index.html" not in failure for failure in failures))

    def test_loading_the_builder_does_not_change_directory_or_render_audio(self):
        before = os.getcwd()
        build = load_build()
        self.assertEqual(os.getcwd(), before)
        self.assertTrue(callable(build.render))
        self.assertTrue(callable(build.gallery_html))


class RenderTests(unittest.TestCase):
    def test_noise_render_ignores_the_global_rng(self):
        render = load_build().render
        song = song_with_noise()
        np.random.seed(0)
        first = render(song)
        np.random.seed(12345)
        second = render(song)
        self.assertGreater(first.size, 0)
        self.assertTrue(np.array_equal(first, second))

    def test_servo_pulse_v2_still_receives_a_seeded_render(self):
        # servo_pulse_v2.py execs build.py up to the pages=[] marker.
        path = os.path.join(repo_root(), "sketches", "build.py")
        with open(path, encoding="utf-8") as handle:
            src = handle.read().split("pages=[]")[0]
        self.assertEqual(src.count("pages=[]"), 0)
        self.assertIn("def render", src)
        self.assertNotIn("ffmpeg", src)
        namespace = {"__file__": path}
        exec(src, namespace)  # same load path as sketches/servo_pulse_v2.py
        self.assertIn("02-servo-pulse", namespace["SONGS"])
        song = dict(namespace["SONGS"]["02-servo-pulse"])
        song["bars"] = 4
        first = namespace["render"](song)
        second = namespace["render"](song)
        self.assertTrue(np.array_equal(first, second))


class LinkTests(unittest.TestCase):
    def test_committed_index_links_resolve(self):
        self.assertEqual(check_links(repo_root()), [])

    def test_missing_relative_link_fails(self):
        with tempfile.TemporaryDirectory() as root:
            sketches = os.path.join(root, "sketches")
            os.makedirs(sketches)
            with open(os.path.join(sketches, "index.html"), "w", encoding="utf-8") as handle:
                handle.write(
                    "<a href='missing.html'>gone</a>"
                    "<a href='https://example.com/tone.js'>cdn</a>"
                    "<a href='#top'>here</a>"
                )
            failures = check_links(root)
        self.assertEqual(len(failures), 1)
        self.assertIn("missing.html", failures[0])
        self.assertIn("not in the repo", failures[0])

    def test_local_src_and_query_string(self):
        with tempfile.TemporaryDirectory() as root:
            sketches = os.path.join(root, "sketches")
            os.makedirs(sketches)
            with open(os.path.join(sketches, "01.html"), "w", encoding="utf-8") as handle:
                handle.write("ok")
            with open(os.path.join(sketches, "index.html"), "w", encoding="utf-8") as handle:
                handle.write("<a href='01.html?play=1'>play</a><script src='vendor/tone.js'></script>")
            failures = check_links(root)
        self.assertEqual(len(failures), 1)
        self.assertIn("src='vendor/tone.js'", failures[0])

    def test_directory_link_resolves(self):
        with tempfile.TemporaryDirectory() as root:
            sketches = os.path.join(root, "sketches")
            os.makedirs(sketches)
            with open(os.path.join(sketches, "index.html"), "w", encoding="utf-8") as handle:
                handle.write("<a href='./'>all sketches</a>")
            self.assertEqual(check_links(root), [])

    def test_file_outside_the_repo_fails_even_when_it_exists(self):
        self.assertTrue(os.path.isfile("/etc/passwd"))
        with tempfile.TemporaryDirectory() as root:
            sketches = os.path.join(root, "sketches")
            os.makedirs(sketches)
            with open(os.path.join(sketches, "index.html"), "w", encoding="utf-8") as handle:
                handle.write("<a href='/etc/passwd'>nope</a>")
            failures = check_links(root)
        self.assertEqual(len(failures), 1)
        self.assertIn("outside the repo", failures[0])

    def test_drift_and_broken_link_are_both_reported(self):
        with tempfile.TemporaryDirectory() as root:
            sketches = write_matching_gallery(root)
            with open(os.path.join(sketches, "index.html"), "w", encoding="utf-8", newline="\n") as handle:
                handle.write("<a href='gone.html'>gone</a>")
            failures = check_sketches(root)
        self.assertTrue(any("differs from sketches/build.py output" in failure for failure in failures))
        self.assertTrue(any("gone.html" in failure and "not in the repo" in failure for failure in failures))

    def test_repo_check_passes(self):
        self.assertEqual(check_sketches(repo_root()), [])


if __name__ == "__main__":
    unittest.main()
