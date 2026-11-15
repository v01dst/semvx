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


def read_versions(args, stdin_text=None):
    """Versions from the command line, a file, or stdin."""
    if args:
        return list(args)
    if stdin_text is None:
        stdin_text = sys.stdin.read()
    found = []
    for line in stdin_text.splitlines():
        for part in line.replace(",", " ").split():
            if part:
                found.append(part)
    return found


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
    versions = read_versions(args)
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


COMMANDS = {
    "parse": cmd_parse,
    "validate": cmd_validate,
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    opts = {}
    args = []
    command = None
    for item in argv:
        if item in ("--json", "-j"):
            opts["json"] = True
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
