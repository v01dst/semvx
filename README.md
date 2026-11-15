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
```

## License

MIT
