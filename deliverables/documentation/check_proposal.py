#!/usr/bin/env python3
"""Bind proposal.md's function table to flowchart.md.

Why this exists: `flowchart.md` defines the F-numbering the whole repository
cites, and `proposal.md` carries one row per F-number with its status. That is
two copies of the same list, and this repository has been bitten twice by a
second copy drifting from the first without anybody noticing. The list in
`proposal.md` is deliberately only the F-number, the flowchart's short name and
a status, so the drift this check can see is the drift that matters: a function
that exists in one file and not the other.

Three failures, each with its reason:

1. An F-number in `flowchart.md` and not in the table. A function nobody has
   given a status is a function nobody has decided about, and it disappears
   silently from the document a reader starts from.
2. An F-number in the table and not in `flowchart.md`. An invented number reads
   as real, and every other file in the repository cites these numbers.
3. A status that is not one of the four words. Four words were chosen so the
   table can be counted; a fifth word makes the counts meaningless, and the
   counts are the only summary of where the project stands.

Run it from anywhere; it resolves its own directory.

    python3 deliverables/documentation/check_proposal.py

Exit 0 means the two files agree. Exit 1 means they do not, and every
disagreement is printed with the F-number so it can be fixed without hunting.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLOWCHART = HERE / "flowchart.md"
PROPOSAL = HERE / "proposal.md"

# The four words, in the order they are counted in the document. Any other word
# in the status column is a failure, including a capitalised or padded variant,
# because a status that has to be interpreted cannot be counted.
STATUSES = ("built", "plumbing", "proposed", "open")

F_NUMBER = re.compile(r"^F[1-6]\.[0-9]+$")


def cells(line: str) -> list[str]:
    """Split one markdown table row into its cells, stripped of emphasis.

    Bold and code markers are removed so a status may be written as `built`,
    **built** or built without changing what this check reads. The word is what
    matters; how the document emphasises it is a presentation decision.
    """
    row = line.strip()
    if not row.startswith("|"):
        return []
    parts = [part.strip() for part in row.strip("|").split("|")]
    return [part.strip("*`_ ").strip() for part in parts]


def flowchart_numbers(text: str) -> list[str]:
    """Every F-number defined in flowchart.md, in the order it defines them.

    Read from the first cell of each table row, which is where section 3 puts
    the ID. Prose mentions elsewhere in the file are not definitions and must
    not be picked up, or a sentence citing F3.5 would define it.
    """
    found: list[str] = []
    for line in text.splitlines():
        row = cells(line)
        if row and F_NUMBER.match(row[0]) and row[0] not in found:
            found.append(row[0])
    return found


def proposal_rows(text: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Every (F-number, status) pair in proposal.md's function table.

    The status column is found by its header rather than by position, so adding
    a column to the table does not silently make this check read the wrong one.
    """
    problems: list[str] = []
    rows: list[tuple[str, str]] = []
    status_column: int | None = None

    for line in text.splitlines():
        row = cells(line)
        if not row:
            continue
        lowered = [cell.lower() for cell in row]
        if "status" in lowered and any("f-number" in cell for cell in lowered):
            status_column = lowered.index("status")
            continue
        if not F_NUMBER.match(row[0]):
            continue
        if status_column is None:
            problems.append(
                "%s: a function row appears before the table header naming a "
                "status column" % row[0]
            )
            continue
        if status_column >= len(row):
            problems.append("%s: the row has no status cell" % row[0])
            continue
        rows.append((row[0], row[status_column].lower()))
    return rows, problems


def main() -> int:
    for path in (FLOWCHART, PROPOSAL):
        if not path.exists():
            print("missing: %s" % path)
            return 1

    defined = flowchart_numbers(FLOWCHART.read_text(encoding="utf-8"))
    rows, problems = proposal_rows(PROPOSAL.read_text(encoding="utf-8"))

    listed = [number for number, _ in rows]
    seen: set[str] = set()
    for number in listed:
        if number in seen:
            problems.append("%s: listed more than once in the table" % number)
        seen.add(number)

    for number in defined:
        if number not in seen:
            problems.append(
                "%s: in flowchart.md and missing from the table" % number
            )
    for number in listed:
        if number not in defined:
            problems.append(
                "%s: in the table and not in flowchart.md" % number
            )
    for number, status in rows:
        if status not in STATUSES:
            problems.append(
                "%s: status %r is not one of %s"
                % (number, status, ", ".join(STATUSES))
            )

    if problems:
        print("proposal.md does not agree with flowchart.md:")
        for problem in problems:
            print("  %s" % problem)
        print()
        print("%d problem(s). Fix the table, or the flowchart, not both."
              % len(problems))
        return 1

    counts = {status: 0 for status in STATUSES}
    for _, status in rows:
        counts[status] += 1
    print(
        "%d F-numbers in flowchart.md, %d rows in proposal.md, all matched."
        % (len(defined), len(rows))
    )
    print("  " + ", ".join("%s %d" % (s, counts[s]) for s in STATUSES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
