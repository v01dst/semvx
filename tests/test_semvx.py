import io
import json
import unittest
from unittest import mock

import semvx
from semvx import InvalidVersion, Version, is_valid


class ParseTest(unittest.TestCase):
    def test_plain_version(self):
        version = Version.parse("1.2.3")
        self.assertEqual(version.core(), (1, 2, 3))
        self.assertEqual(version.prerelease, ())
        self.assertEqual(version.build, "")

    def test_prerelease(self):
        version = Version.parse("1.2.3-alpha.1")
        self.assertEqual(version.prerelease, ("alpha", "1"))
        self.assertTrue(version.is_prerelease())

    def test_build_metadata(self):
        version = Version.parse("1.2.3+build.5")
        self.assertEqual(version.build, "build.5")
        self.assertEqual(str(version), "1.2.3+build.5")

    def test_leading_zero_is_rejected(self):
        self.assertFalse(is_valid("01.2.3"))
        self.assertFalse(is_valid("1.02.3"))
        self.assertFalse(is_valid("1.2.03"))

    def test_missing_part_is_rejected(self):
        self.assertFalse(is_valid("1.2"))
        self.assertFalse(is_valid("1"))
        self.assertFalse(is_valid(""))

    def test_str_round_trip(self):
        for text in ("0.0.1", "1.0.0-alpha", "1.0.0-rc.1+exp.sha.5114f85"):
            self.assertEqual(str(Version.parse(text)), text)

    def test_invalid_raises(self):
        with self.assertRaises(InvalidVersion):
            Version.parse("not-a-version")


class ValidateTest(unittest.TestCase):
    def test_valid_and_invalid(self):
        self.assertTrue(is_valid("1.0.0"))
        self.assertFalse(is_valid("1.0"))

    def test_prerelease_numeric_identifier(self):
        self.assertTrue(is_valid("1.0.0-0"))
        self.assertTrue(is_valid("1.0.0-0.3.7"))


class CommandTest(unittest.TestCase):
    def run_main(self, argv, stdin=""):
        out = []
        with mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
            with mock.patch("sys.stdin", io.StringIO(stdin)):
                with mock.patch("sys.stderr", new_callable=io.StringIO):
                    code = semvx.main(argv)
        out.append(stdout.getvalue())
        return code, "".join(out)

    def test_parse_prints_version(self):
        code, output = self.run_main(["parse", "1.2.3"])
        self.assertEqual(code, 0)
        self.assertEqual(output.strip(), "1.2.3")

    def test_parse_json(self):
        code, output = self.run_main(["parse", "1.2.3-alpha.1", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(output)
        self.assertEqual(data["major"], 1)
        self.assertEqual(data["prerelease"], ["alpha", "1"])

    def test_parse_invalid_returns_one(self):
        code, _ = self.run_main(["parse", "nope"])
        self.assertEqual(code, 1)

    def test_validate_reads_stdin(self):
        code, output = self.run_main(["validate"], stdin="1.0.0\n2.0.0\nbad\n")
        self.assertEqual(code, 1)
        self.assertIn("1.0.0\tvalid", output)
        self.assertIn("bad\tinvalid", output)

    def test_unknown_command(self):
        code, _ = self.run_main(["nope"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
