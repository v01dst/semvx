# semvx

Semantic versions from your terminal. Parse, compare, sort, bump, and check ranges. Zero dependencies, pure Python stdlib.

## Install

```bash
pip install semvx
```

Or run directly:

```bash
python semvx.py --help
```

## Commands

| Command | What it does |
|---|---|
| `parse` | read a version and print it back |
| `validate` | report whether each version is valid |
| `compare` | order two versions (`-1`, `0`, `1`) |
| `sort` | sort versions by semver precedence |
| `latest` | print the highest version of a list |
| `bump` | the next major, minor, patch, prerelease or release |
| `satisfies` | check a version against a range |
| `diff` | what changed between two versions |
| `filter` | keep the versions that fall inside a range |

Every command takes `--json` for machine-readable output.

## Usage

```bash
# Parse a version
semvx parse 1.2.3-alpha.1

# JSON output
semvx parse 1.2.3 --json

# Check which of these are valid
semvx validate 1.2.3 2.0.0 broken

# Read versions from stdin
cat versions.txt | semvx validate

# Compare two versions (-1, 0, 1)
semvx compare 1.2.3 1.2.4

# Sort a list of versions
semvx sort 1.10.0 1.2.0 1.2.0-rc.1

# Highest version in a list
semvx latest 1.2.0 1.10.0 1.9.0

# Next version
semvx bump 1.2.3 minor       # 1.3.0
semvx bump 1.2.3 pre         # 1.2.4-0
semvx bump 1.2.4-rc.1 release # 1.2.4

# Does a version fall inside a range?
semvx satisfies 1.5.0 "^1.2.0"   # yes
semvx satisfies 2.0.0 "^1.2.0"   # no

# What changed between two versions
semvx diff 1.2.3 2.0.0          # major

# Keep only the versions inside a range
semvx filter "^1.2.0" 1.2.0 2.0.0 1.9.0
```

## Ranges

`satisfies` understands the range syntax people already use:

| Range | Means |
|---|---|
| `1.2.3` | exactly that version |
| `>=1.2.3` `>1.2.3` `<=1.2.3` `<1.2.3` | comparisons |
| `^1.2.3` | `>=1.2.3 <2.0.0` (`^0.2.3` stops at `0.3.0`) |
| `~1.2.3` | `>=1.2.3 <1.3.0` |
| `1.2.x` `1.x` | any patch in that line |
| `*` | any version |
| `>=1.2.0 <2.0.0` | both, in that order |
| `^1.0.0 \|\| ^2.0.0` | either branch |
| `1.2.0 - 2.0.0` | from one version to another |

A prerelease only fits a range when the range itself names a prerelease of the same
`major.minor.patch`, which is the same rule npm follows.

## License

MIT
