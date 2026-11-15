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


class CompareTest(unittest.TestCase):
    def test_core_order(self):
        self.assertEqual(semvx.compare(Version.parse("1.0.0"), Version.parse("2.0.0")), -1)
        self.assertEqual(semvx.compare(Version.parse("2.0.0"), Version.parse("1.0.0")), 1)
        self.assertEqual(semvx.compare(Version.parse("1.2.3"), Version.parse("1.2.3")), 0)

    def test_prerelease_is_older(self):
        self.assertEqual(semvx.compare(Version.parse("1.0.0-alpha"), Version.parse("1.0.0")), -1)
        self.assertEqual(semvx.compare(Version.parse("1.0.0"), Version.parse("1.0.0-alpha")), 1)

    def test_prerelease_identifiers(self):
        self.assertEqual(semvx.compare(Version.parse("1.0.0-alpha"), Version.parse("1.0.0-beta")), -1)
        self.assertEqual(semvx.compare(Version.parse("1.0.0-1"), Version.parse("1.0.0-alpha")), -1)
        self.assertEqual(semvx.compare(Version.parse("1.0.0-alpha.1"), Version.parse("1.0.0-alpha.2")), -1)
        self.assertEqual(semvx.compare(Version.parse("1.0.0-alpha"), Version.parse("1.0.0-alpha.1")), -1)

    def test_build_metadata_is_ignored(self):
        self.assertEqual(semvx.compare(Version.parse("1.0.0+a"), Version.parse("1.0.0+b")), 0)

    def test_sorted_uses_comparison(self):
        versions = [Version.parse(v) for v in ("1.10.0", "1.2.0", "1.2.0-rc.1")]
        self.assertEqual([str(v) for v in sorted(versions)], ["1.2.0-rc.1", "1.2.0", "1.10.0"])


class BumpTest(unittest.TestCase):
    def test_core_bumps(self):
        version = Version.parse("1.2.3")
        self.assertEqual(str(semvx.bump(version, "major")), "2.0.0")
        self.assertEqual(str(semvx.bump(version, "minor")), "1.3.0")
        self.assertEqual(str(semvx.bump(version, "patch")), "1.2.4")

    def test_prerelease_bump(self):
        version = Version.parse("1.2.3-alpha.1")
        self.assertEqual(str(semvx.bump(version, "pre")), "1.2.3-alpha.2")

    def test_prerelease_bump_from_a_release(self):
        version = Version.parse("1.2.3")
        self.assertEqual(str(semvx.bump(version, "pre")), "1.2.4-0")

    def test_prerelease_bump_with_preid(self):
        version = Version.parse("1.2.3")
        self.assertEqual(str(semvx.bump(version, "pre", "beta")), "1.2.4-beta.0")

    def test_release_drops_the_prerelease(self):
        version = Version.parse("1.2.3-rc.1")
        self.assertEqual(str(semvx.bump(version, "release")), "1.2.3")

    def test_release_without_prerelease_fails(self):
        with self.assertRaises(semvx.InvalidVersion):
            semvx.bump(Version.parse("1.2.3"), "release")


class SatisfiesTest(unittest.TestCase):
    def check(self, version, range_text, expected):
        self.assertEqual(semvx.satisfies(Version.parse(version), range_text), expected)

    def test_exact(self):
        self.check("1.2.3", "1.2.3", True)
        self.check("1.2.4", "1.2.3", False)

    def test_comparators(self):
        self.check("1.2.3", ">=1.2.3", True)
        self.check("1.2.2", ">1.2.3", False)
        self.check("1.2.3", "<=1.2.3", True)
        self.check("1.2.3", "<1.2.4", True)

    def test_caret(self):
        self.check("1.2.3", "^1.2.3", True)
        self.check("1.9.9", "^1.2.3", True)
        self.check("2.0.0", "^1.2.3", False)
        self.check("0.2.9", "^0.2.3", True)
        self.check("0.3.0", "^0.2.3", False)
        self.check("0.0.3", "^0.0.3", True)
        self.check("0.0.4", "^0.0.3", False)

    def test_tilde(self):
        self.check("1.2.9", "~1.2.3", True)
        self.check("1.3.0", "~1.2.3", False)

    def test_wildcards(self):
        self.check("1.2.9", "1.2.x", True)
        self.check("1.3.0", "1.2.x", False)
        self.check("1.9.0", "1.x", True)
        self.check("2.0.0", "1.x", False)

    def test_partial_comparators(self):
        self.check("1.2.5", ">=1.2", True)
        self.check("1.1.9", ">=1.2", False)
        self.check("1.2.5", ">1.2", False)
        self.check("1.3.0", ">1.2", True)
        self.check("1.2.5", "<=1.2", True)
        self.check("1.3.0", "<=1.2", False)
        self.check("1.1.9", "<1.2", True)
        self.check("1.2.0", "<1.2", False)

    def test_any(self):
        self.check("9.9.9", "*", True)
        self.check("9.9.9", "", True)

    def test_and_ranges(self):
        self.check("1.5.0", ">=1.2.0 <2.0.0", True)
        self.check("2.1.0", ">=1.2.0 <2.0.0", False)

    def test_or_ranges(self):
        self.check("2.1.0", "^1.0.0 || ^2.0.0", True)
        self.check("3.1.0", "^1.0.0 || ^2.0.0", False)

    def test_hyphen_range(self):
        self.check("1.5.0", "1.2.0 - 2.0.0", True)
        self.check("2.0.1", "1.2.0 - 2.0.0", False)

    def test_prerelease_needs_a_matching_comparator(self):
        self.check("1.5.0-beta", "^1.2.0", False)
        self.check("1.5.0-beta", ">=1.5.0-alpha", True)
        self.check("1.5.0-beta", ">=1.5.0-alpha <2.0.0", True)


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

    def test_compare_prints_number(self):
        code, output = self.run_main(["compare", "1.2.3", "1.2.4"])
        self.assertEqual(code, 0)
        self.assertEqual(output.strip(), "-1")

    def test_compare_json(self):
        code, output = self.run_main(["compare", "2.0.0", "1.0.0", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(output)
        self.assertEqual(data["relation"], "greater")
        self.assertEqual(data["result"], 1)

    def test_sort_orders_numerically(self):
        code, output = self.run_main(["sort", "1.10.0", "1.2.0", "1.2.0-rc.1"])
        self.assertEqual(code, 0)
        self.assertEqual(output.split(), ["1.2.0-rc.1", "1.2.0", "1.10.0"])

    def test_sort_reverse(self):
        code, output = self.run_main(["sort", "1.2.0", "2.0.0", "--reverse"])
        self.assertEqual(code, 0)
        self.assertEqual(output.split(), ["2.0.0", "1.2.0"])

    def test_sort_reports_bad_versions(self):
        code, output = self.run_main(["sort", "1.0.0", "bad"])
        self.assertEqual(code, 1)
        self.assertEqual(output.strip(), "1.0.0")

    def test_latest_picks_the_newest(self):
        code, output = self.run_main(["latest", "1.2.0", "1.10.0", "1.9.0"])
        self.assertEqual(code, 0)
        self.assertEqual(output.strip(), "1.10.0")

    def test_latest_skips_prereleases_when_a_release_is_present(self):
        code, output = self.run_main(["latest", "2.0.0-rc.1", "1.9.0"])
        self.assertEqual(code, 0)
        self.assertEqual(output.strip(), "2.0.0-rc.1")

    def test_bump_prints_the_next_version(self):
        code, output = self.run_main(["bump", "1.2.3", "minor"])
        self.assertEqual(code, 0)
        self.assertEqual(output.strip(), "1.3.0")

    def test_bump_with_preid(self):
        code, output = self.run_main(["bump", "1.2.3", "pre", "--preid=rc"])
        self.assertEqual(code, 0)
        self.assertEqual(output.strip(), "1.2.4-rc.0")

    def test_satisfies_prints_yes(self):
        code, output = self.run_main(["satisfies", "1.5.0", "^1.2.0"])
        self.assertEqual(code, 0)
        self.assertEqual(output.strip(), "yes")

    def test_satisfies_prints_no_and_fails(self):
        code, output = self.run_main(["satisfies", "2.5.0", "^1.2.0"])
        self.assertEqual(code, 1)
        self.assertEqual(output.strip(), "no")

    def test_satisfies_json(self):
        code, output = self.run_main(["satisfies", "1.5.0", "^1.2.0", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(output)
        self.assertTrue(data["satisfies"])
        self.assertEqual(data["range"], "^1.2.0")


if __name__ == "__main__":
    unittest.main()
