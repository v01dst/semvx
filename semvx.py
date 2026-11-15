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
}


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
        elif item.startswith("--") and "=" in item:
            key, value = item[2:].split("=", 1)
            opts[key.replace("-", "_")] = value
        elif command is None:
            command = item
        else:
            args.append(item)
    if not command or command not in COMMANDS:
        names = ", ".join(sorted(COMMANDS))
        print("usage: semvx <command> [args]\n\ncommands: %s" % names, file=sys.stderr)
        return 2
    try:
        return COMMANDS[command](args, opts)
    except InvalidVersion as error:
        print("not a semantic version: %s" % error.args[0], file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
