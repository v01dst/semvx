# Changelog

All notable changes to semvx are recorded here.

## 0.1.0

- `parse` reads a semantic version and prints it back, with `--json` for the parts.
- `validate` reports whether each version is valid, reading from arguments, a file or stdin.
- `compare` orders two versions the way the semver spec does.
- `sort` orders a list of versions, `latest` prints the highest one.
- `bump` gives the next major, minor, patch, prerelease or release.
- `satisfies` checks a version against a range, including caret, tilde, x ranges, hyphen ranges and `||` branches.
- `diff` says what changed between two versions.
- `filter` keeps the versions from a list that fall inside a range.
