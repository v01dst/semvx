"""Semantic version parsing for the semvx command line tool."""

import json
import re
import sys

VERSION_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)"
    r"\.(?P<minor>0|[1-9]\d*)"
    r"\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)

IDENTIFIER_RE = re.compile(r"^(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)$")


class InvalidVersion(ValueError):
    """Raised when a string is not a valid semantic version."""


class Version:
    """A semantic version: major.minor.patch[-prerelease][+build]."""

    __slots__ = ("major", "minor", "patch", "prerelease", "build")

    def __init__(self, major, minor, patch, prerelease=(), build=""):
        self.major = major
        self.minor = minor
        self.patch = patch
        self.prerelease = tuple(prerelease)
        self.build = build

    @classmethod
    def parse(cls, text):
        raw = str(text).strip()
        match = VERSION_RE.match(raw)
        if not match:
            raise InvalidVersion(raw)
        prerelease = match.group("prerelease")
        return cls(
            int(match.group("major")),
            int(match.group("minor")),
            int(match.group("patch")),
            tuple(prerelease.split(".")) if prerelease else (),
            match.group("build") or "",
        )

    def is_prerelease(self):
        return bool(self.prerelease)

    def core(self):
        return (self.major, self.minor, self.patch)

    def __str__(self):
        text = "%d.%d.%d" % self.core()
        if self.prerelease:
            text += "-" + ".".join(self.prerelease)
        if self.build:
            text += "+" + self.build
        return text

    def __repr__(self):
        return "Version(%r)" % str(self)

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self.core() == other.core() and self.prerelease == other.prerelease

    def __hash__(self):
        return hash((self.core(), self.prerelease))

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return compare(self, other) < 0

    def __le__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return compare(self, other) <= 0

    def __gt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return compare(self, other) > 0

    def __ge__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return compare(self, other) >= 0


def compare_prerelease(left, right):
    """Order two prerelease identifier tuples."""
    if not left and not right:
        return 0
    if not left:
        return 1
    if not right:
        return -1
    for a, b in zip(left, right):
        a_num = a.isdigit()
        b_num = b.isdigit()
        if a_num and b_num:
            if int(a) != int(b):
                return -1 if int(a) < int(b) else 1
        elif a_num != b_num:
            return -1 if a_num else 1
        elif a != b:
            return -1 if a < b else 1
    if len(left) == len(right):
        return 0
    return -1 if len(left) < len(right) else 1


def compare(left, right):
    """-1 when left is older, 0 when equal, 1 when left is newer."""
    if left.core() != right.core():
        return -1 if left.core() < right.core() else 1
    return compare_prerelease(left.prerelease, right.prerelease)


def is_valid(text):
    """True when text is a valid semantic version."""
    try:
        Version.parse(text)
    except InvalidVersion:
        return False
    return True


def to_dict(version):
    return {
        "version": str(version),
        "major": version.major,
        "minor": version.minor,
        "patch": version.patch,
        "prerelease": list(version.prerelease),
        "build": version.build,
        "prerelease_release": version.is_prerelease(),
    }


def read_versions(args, opts=None, stdin_text=None):
    """Versions from the command line, a file, or stdin."""
    opts = opts or {}
    if args:
        return list(args)
    path = opts.get("file")
    if path:
        with open(path, "r", encoding="utf-8") as handle:
            stdin_text = handle.read()
    if stdin_text is None:
        stdin_text = sys.stdin.read()
    found = []
    for line in stdin_text.splitlines():
        for part in line.replace(",", " ").split():
            if part:
                found.append(part)
    return found


def split_versions(texts):
    """Split texts into valid versions and the ones that failed to parse."""
    good = []
    bad = []
    for text in texts:
        try:
            good.append(Version.parse(text))
        except InvalidVersion:
            bad.append(text)
    return good, bad


def cmd_parse(args, opts):
    if not args:
        raise SystemExit("parse needs a version")
    version = Version.parse(args[0])
    if opts.get("json"):
        print(json.dumps(to_dict(version), indent=2))
    else:
        print(str(version))
    return 0


def cmd_validate(args, opts):
    versions = read_versions(args, opts)
    bad = []
    for text in versions:
        if not is_valid(text):
            bad.append(text)
    if opts.get("json"):
        print(json.dumps({"valid": len(versions) - len(bad), "invalid": bad}, indent=2))
    else:
        for text in versions:
            print("%s\t%s" % (text, "valid" if is_valid(text) else "invalid"))
    return 1 if bad else 0


def cmd_sort(args, opts):
    versions = read_versions(args, opts)
    good, bad = split_versions(versions)
    for text in bad:
        print("not a semantic version: %s" % text, file=sys.stderr)
    ordered = sorted(good, reverse=bool(opts.get("reverse")))
    if opts.get("json"):
        print(json.dumps([str(v) for v in ordered], indent=2))
    else:
        for version in ordered:
            print(version)
    return 1 if bad else 0


def cmd_latest(args, opts):
    versions = read_versions(args, opts)
    good, bad = split_versions(versions)
    for text in bad:
        print("not a semantic version: %s" % text, file=sys.stderr)
    if not good:
        print("no versions given", file=sys.stderr)
        return 1
    newest = max(good)
    if opts.get("json"):
        print(json.dumps(to_dict(newest), indent=2))
    else:
        print(newest)
    return 1 if bad else 0


def cmd_compare(args, opts):
    if len(args) != 2:
        raise SystemExit("compare needs two versions")
    left = Version.parse(args[0])
    right = Version.parse(args[1])
    result = compare(left, right)
    if opts.get("json"):
        print(json.dumps({
            "left": str(left),
            "right": str(right),
            "result": result,
            "relation": "greater" if result > 0 else ("less" if result < 0 else "equal"),
        }, indent=2))
    else:
        print(result)
    return 0


XCHARS = ("x", "X", "*")
OPERATORS = (">=", "<=", ">", "<", "=")


class Comparator:
    """One condition in a range, such as >=1.2.3."""

    __slots__ = ("op", "version")

    def __init__(self, op, version=None):
        self.op = op
        self.version = version

    def test(self, version):
        if self.version is None:
            return True
        result = compare(version, self.version)
        if self.op in ("", "="):
            return result == 0
        if self.op == ">=":
            return result >= 0
        if self.op == ">":
            return result > 0
        if self.op == "<=":
            return result <= 0
        if self.op == "<":
            return result < 0
        raise InvalidVersion("unknown operator: %s" % self.op)


def partial_parts(token):
    """Split 1.2.x into (1, 2, None); a missing part is None."""
    parts = token.split(".")
    out = []
    for index in range(3):
        if index < len(parts):
            piece = parts[index]
            if piece in XCHARS or piece == "":
                out.append(None)
            else:
                try:
                    out.append(int(piece))
                except ValueError:
                    raise InvalidVersion(token)
        else:
            out.append(None)
    return out


def partial_version(parts):
    return Version(parts[0] or 0, parts[1] or 0, parts[2] or 0)


def caret_upper(parts):
    major, minor, patch = parts
    if major is None:
        return Version(0, 0, 0)
    if major > 0:
        return Version(major + 1, 0, 0)
    if minor is None:
        return Version(1, 0, 0)
    if minor > 0:
        return Version(0, minor + 1, 0)
    if patch is None:
        return Version(0, 1, 0)
    if patch > 0:
        return Version(0, 0, patch + 1)
    return Version(0, 0, 1)


def tilde_upper(parts):
    major, minor, patch = parts
    if major is None:
        return Version(0, 0, 0)
    if minor is None:
        return Version(major + 1, 0, 0)
    return Version(major, minor + 1, 0)


def xrange_upper(parts):
    major, minor, patch = parts
    if major is None:
        return Version(0, 0, 0)
    if minor is None:
        return Version(major + 1, 0, 0)
    return Version(major, minor + 1, 0)


def parse_token(token):
    """Turn one range token into a list of comparators."""
    op = ""
    rest = token
    for candidate in OPERATORS:
        if rest.startswith(candidate):
            op = candidate
            rest = rest[len(candidate):]
            break
    mode = ""
    if rest.startswith("^"):
        mode = "caret"
        rest = rest[1:]
    elif rest.startswith("~"):
        mode = "tilde"
        rest = rest[1:]
    if rest in XCHARS:
        return [Comparator("*", None)]
    if "-" in rest or "+" in rest:
        version = Version.parse(rest)
        return [Comparator(op or "=", version)]
    parts = partial_parts(rest)
    lower = partial_version(parts)
    if mode == "caret":
        return [Comparator(">=", lower), Comparator("<", caret_upper(parts))]
    if mode == "tilde":
        return [Comparator(">=", lower), Comparator("<", tilde_upper(parts))]
    if parts[2] is None:
        if op in ("", "="):
            return [Comparator(">=", lower), Comparator("<", xrange_upper(parts))]
        if op == ">=":
            return [Comparator(">=", lower)]
        if op == ">":
            return [Comparator(">=", xrange_upper(parts))]
        if op == "<=":
            return [Comparator("<", xrange_upper(parts))]
        if op == "<":
            return [Comparator("<", lower)]
    return [Comparator(op or "=", lower)]


def parse_range(text):
    """A range is a list of comparator sets, one per || branch."""
    raw = str(text).strip()
    if raw == "" or raw in XCHARS:
        return [[Comparator("*", None)]]
    sets = []
    for branch in raw.split("||"):
        branch = branch.strip()
        if " - " in branch:
            sets.append(parse_hyphen(branch))
        else:
            comparators = []
            for token in branch.split():
                comparators.extend(parse_token(token))
            sets.append(comparators)
    return sets


def parse_hyphen(branch):
    left, right = branch.split(" - ", 1)
    comparators = [Comparator(">=", partial_version(partial_parts(left.strip())))]
    right_parts = partial_parts(right.strip())
    if right_parts[2] is None:
        comparators.append(Comparator("<", xrange_upper(right_parts)))
    else:
        comparators.append(Comparator("<=", partial_version(right_parts)))
    return comparators


def satisfies(version, range_text):
    """True when the version falls inside the range."""
    for comparators in parse_range(range_text):
        if not all(c.test(version) for c in comparators):
            continue
        if not version.prerelease:
            return True
        for comparator in comparators:
            other = comparator.version
            if other is not None and other.prerelease and other.core() == version.core():
                return True
    return False


def cmd_satisfies(args, opts):
    if len(args) != 2:
        raise SystemExit("satisfies needs a version and a range")
    version = Version.parse(args[0])
    result = satisfies(version, args[1])
    if opts.get("json"):
        print(json.dumps({
            "version": str(version),
            "range": args[1],
            "satisfies": result,
        }, indent=2))
    else:
        print("yes" if result else "no")
    return 0 if result else 1


def change_kind(left, right):
    """What changed between two versions: major, minor, patch, prerelease or none."""
    if left.major != right.major:
        return "major"
    if left.minor != right.minor:
        return "minor"
    if left.patch != right.patch:
        return "patch"
    if left.prerelease != right.prerelease:
        return "prerelease"
    return "none"


def cmd_diff(args, opts):
    if len(args) != 2:
        raise SystemExit("diff needs two versions")
    left = Version.parse(args[0])
    right = Version.parse(args[1])
    kind = change_kind(left, right)
    if opts.get("json"):
        print(json.dumps({
            "from": str(left),
            "to": str(right),
            "change": kind,
            "direction": "up" if compare(left, right) < 0 else ("down" if compare(left, right) > 0 else "same"),
        }, indent=2))
    else:
        print(kind)
    return 0


def cmd_filter(args, opts):
    if not args:
        raise SystemExit("filter needs a range")
    range_text = args[0]
    versions = read_versions(args[1:], opts)
    good, bad = split_versions(versions)
    for text in bad:
        print("not a semantic version: %s" % text, file=sys.stderr)
    matched = [v for v in good if satisfies(v, range_text)]
    if opts.get("json"):
        print(json.dumps([str(v) for v in matched], indent=2))
    else:
        for version in matched:
            print(version)
    return 1 if bad else 0


def bump(version, part, preid=None):
    """The next version after the given bump."""
    if part == "major":
        return Version(version.major + 1, 0, 0)
    if part == "minor":
        return Version(version.major, version.minor + 1, 0)
    if part == "patch":
        return Version(version.major, version.minor, version.patch + 1)
    if part == "pre":
        if version.prerelease:
            ids = list(version.prerelease)
            if ids[-1].isdigit():
                ids[-1] = str(int(ids[-1]) + 1)
            else:
                ids.append("0")
            return Version(version.major, version.minor, version.patch, ids)
        tag = [preid, "0"] if preid else ["0"]
        return Version(version.major, version.minor, version.patch + 1, tag)
    if part == "release":
        if not version.prerelease:
            raise InvalidVersion("%s has no prerelease to release" % version)
        return Version(version.major, version.minor, version.patch)
    raise InvalidVersion("unknown bump: %s" % part)


def cmd_bump(args, opts):
    if len(args) != 2:
        raise SystemExit("bump needs a version and a part")
    version = Version.parse(args[0])
    result = bump(version, args[1], opts.get("preid"))
    if opts.get("json"):
        print(json.dumps(to_dict(result), indent=2))
    else:
        print(result)
    return 0


COMMANDS = {
    "parse": cmd_parse,
    "validate": cmd_validate,
    "compare": cmd_compare,
    "sort": cmd_sort,
    "latest": cmd_latest,
    "bump": cmd_bump,
    "satisfies": cmd_satisfies,
    "diff": cmd_diff,
    "filter": cmd_filter,
}

DESCRIPTIONS = {
    "parse": "parse a version and print it back",
    "validate": "report whether each version is valid",
    "compare": "compare two versions (-1, 0, 1)",
    "sort": "sort versions by semver precedence",
    "latest": "print the highest version of a list",
    "bump": "print the next major, minor, patch or prerelease",
    "satisfies": "check a version against a range",
    "diff": "say what changed between two versions",
    "filter": "keep the versions that fall inside a range",
}

USAGE = {
    "parse": "semvx parse VERSION [--json]",
    "validate": "semvx validate [VERSION...] [--file PATH] [--json]",
    "compare": "semvx compare VERSION VERSION [--json]",
    "sort": "semvx sort [VERSION...] [--file PATH] [--reverse] [--json]",
    "latest": "semvx latest [VERSION...] [--file PATH] [--json]",
    "bump": "semvx bump VERSION major|minor|patch|pre|release [--preid TAG] [--json]",
    "satisfies": "semvx satisfies VERSION RANGE [--json]",
    "diff": "semvx diff VERSION VERSION [--json]",
    "filter": "semvx filter RANGE [VERSION...] [--file PATH] [--json]",
}

VERSION = "0.1.0"


def print_help():
    print("semvx %s - semantic versions from your terminal" % VERSION)
    print()
    print("usage: semvx <command> [args]")
    print()
    print("commands:")
    for name in sorted(COMMANDS):
        print("  %-10s %s" % (name, DESCRIPTIONS[name]))
    print()
    print("options:")
    print("  --json      print JSON instead of plain text")
    print("  --file      read versions from a file")
    print("  --reverse   sort from newest to oldest")
    print("  --preid     tag used by the pre bump")
    print("  --help      show this text")
    print("  --version   show the version")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    opts = {}
    args = []
    command = None
    for item in argv:
        if item in ("--json", "-j"):
            opts["json"] = True
        elif item == "--reverse":
            opts["reverse"] = True
        elif item in ("--help", "-h"):
            print_help()
            return 0
        elif item == "--version":
            print(VERSION)
            return 0
        elif item.startswith("--") and "=" in item:
            key, value = item[2:].split("=", 1)
            opts[key.replace("-", "_")] = value
        elif command is None:
            command = item
        else:
            args.append(item)
    if not command or command not in COMMANDS:
        if command:
            print("unknown command: %s" % command, file=sys.stderr)
        print_help()
        return 2
    try:
        return COMMANDS[command](args, opts)
    except InvalidVersion as error:
        print("not a semantic version: %s" % error.args[0], file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
