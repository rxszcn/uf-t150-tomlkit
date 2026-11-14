"""Generate reference outputs with the current implementation.

Parses a corpus of TOML documents and records, for each:
  - tomlkit.dumps(parsed)            (style-preserving round-trip rendering)
  - repr of the unwrapped structure  (semantic equivalence)
  - error string + line/col for invalid documents

Used to verify byte-for-byte equivalence before/after the parser optimization.

Usage:
    python benchmarks/gen_reference.py <out_dir>
"""

from __future__ import annotations

import json
import sys

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tomlkit
from tomlkit.exceptions import TOMLKitError

from bench_parse import make_document


def corpus() -> dict[str, str]:
    docs: dict[str, str] = {}
    # Synthetic catalog documents of increasing size
    for n in (50, 500, 2000):
        docs[f"catalog_{n}"] = make_document(n)
    # Repo example files
    examples = Path(__file__).resolve().parent.parent / "tests" / "examples"
    for f in sorted(examples.glob("*.toml")):
        docs[f"example_{f.stem}"] = f.read_text(encoding="utf-8")
    # A hand-written document stressing headers, dotted keys, AoT, comments
    docs["edge_cases"] = '''\
# leading comment
top = 1
[ a . b ]   # spaced header
k = "v"
[a.b.c.d]
deep = true
[[aot]]
x = 1
[[aot]]
x = 2
[aot.sub]
y = 3
[[aot]]
x = 3
[tables.dw.t1]  # c1
d = 1979-05-27T07:32:00Z
[tables.dw.t2]
arr = [1, 2, 3]
inline = {a = 1, b = "x"}
dotted.key.here = 5
[tables.dw.t2.more]
s = """multi
line"""
'''
    docs["crlf"] = "[a]\r\nk = 1  # comment\r\n[b.c]\r\nq = 2\r\n"
    docs["booleans"] = "[t]\na = true\nb = false\nc = truefalse\n"
    docs["numbers"] = (
        "[n]\n"
        "a = 1_000\nb = 0xDEAD_BEEF\nc = 0o755\nd = 0b1010\n"
        "e = 3.14\nf = 1e10\ng = -inf\nh = +nan\ni = inf\nj = nan\n"
        "k = +1.5\nl = -0.0\n"
    )
    docs["strings"] = (
        "[s]\n"
        "a = 'literal'\n"
        'b = "esc \\t \\u0041 \\U0001F600 \\x41"\n'
        "c = '''multi\nliteral'''\n"
        'd = """multi\nbasic \\n"""\n'
        'e = "backslash \\" quote"\n'
    )
    docs["invalid_double_eq"] = "k == 1\n"
    docs["invalid_no_eq"] = "k 1\n"
    docs["invalid_bool"] = "k = tru\n"
    docs["invalid_control_comment"] = "k = 1  # bad\x01comment\n"
    docs["invalid_table_name"] = "[a b]\n"
    docs["invalid_empty_table"] = "[]\n"
    docs["out_of_order"] = (
        "[a]\nx = 1\n[b]\ny = 2\n[a.z]\nw = 3\n"
    )
    docs["super_merge"] = (
        "[t.a.b]\nk1 = 1\n[t.a.c]\nk2 = 2\n[t.a.b.d]\nk3 = 3\n"
    )
    docs["aot_children"] = (
        "[[fruit]]\nname = 'apple'\n[fruit.physical]\ncolor = 'red'\n"
        "[[fruit.variety]]\nname = 'gala'\n[[fruit.variety]]\nname = 'fuji'\n"
        "[[fruit]]\nname = 'banana'\n"
    )
    return docs


def main() -> None:
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    index = {}
    for name, text in sorted(corpus().items()):
        record = {}
        try:
            doc = tomlkit.parse(text)
            record["dumps"] = tomlkit.dumps(doc)
            record["unwrapped"] = json.dumps(doc.unwrap(), sort_keys=True, default=str)
        except TOMLKitError as e:
            record["error"] = f"{type(e).__name__}: {e}"
        (out_dir / f"{name}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        index[name] = sorted(record)
    print(f"wrote {len(index)} reference files to {out_dir}")


if __name__ == "__main__":
    main()
