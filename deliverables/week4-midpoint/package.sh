#!/usr/bin/env bash
# Build the Week 4 midpoint submission: deliverable A as one zip, deliverable B
# as a folder and a zip, and a manifest of what was found and what was not.
#
# Why a script and not a list of steps in a runbook: most of deliverable A is
# raw material that is not in git and never will be, so whoever packages it is
# copying files by hand minutes before a deadline. One command that always
# writes the same layout, and says out loud what it could not find, is the
# difference between a submission with a known gap and one with a silent gap.
#
# Nothing raw ever enters the repository. Everything is written under
# .local/submission/<timestamp>/, and .local carries an ignore file of its own
# so git never sees any of it. The script copies at run time from wherever the
# material actually is on the group's machine.
set -euo pipefail

# The script's own location, not $PWD, decides where the repository root is. It
# is meant to be run from the root, but a run from the wrong directory should
# still write to the right place instead of half way through somebody's tree.
# Two levels up from deliverables/week4-midpoint/ is the root, and it is checked
# against a file that only the root has: getting this wrong once already wrote a
# submission folder into the home directory, silently, and every item reported
# missing because nothing was where it looked.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/../.." && pwd)"
if [ ! -f "${ROOT}/AGENTS.md" ]; then
  printf 'package.sh: %s does not look like the repository root (no AGENTS.md).\n' "${ROOT}" >&2
  exit 1
fi
W4="${ROOT}/deliverables/week4-midpoint"

STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="${ROOT}/.local/submission/${STAMP}"
# Two runs inside the same second would otherwise write into each other. A
# submission gets rebuilt the moment somebody fixes one file, so a collision
# adds a suffix rather than overwriting the previous attempt: the earlier
# folder is evidence of what was handed in, and it stays.
attempt=1
while [ -e "${OUT}" ]; do
  attempt=$((attempt + 1))
  OUT="${ROOT}/.local/submission/${STAMP}-${attempt}"
done
mkdir -p "${OUT}"

# .local is not in the repository's ignore file, and adding it there would mean
# editing a tracked file outside this folder. An ignore file inside .local keeps
# everything written here out of git status without touching anything tracked.
# This is the same line demo/start.sh writes, on purpose: two scripts write into
# .local and either one may run first.
printf '*\n' > "${ROOT}/.local/.gitignore"

# One archiver is enough, but which one exists varies by machine. zip is
# preferred because it records empty directories without being asked, and the
# three empty folders under evidence/raw/week3/ are themselves part of the
# record: they say the intake step has not happened.
if command -v zip >/dev/null 2>&1; then
  ZIP_TOOL="zip"
elif command -v python3 >/dev/null 2>&1; then
  ZIP_TOOL="python3"
else
  printf 'package.sh: neither zip nor python3 is available, so no archive can be written.\n' >&2
  exit 1
fi

FOUND=()
MISSING=()

found() {
  FOUND+=("$1")
  printf '  found    %s\n' "$1"
}

missing() {
  MISSING+=("$1: $2")
  printf '  MISSING  %s: %s\n' "$1" "$2"
}

# cp -R and then a prune, rather than a filtered copy, because the excluded
# names are the brief's own check on the zips: nothing from .git, node_modules
# or .local may be inside them. Pruning after the copy means a newly appearing
# one is removed too, instead of silently riding along in a pattern nobody
# updated.
copy_tree() {
  local source="$1" destination="$2"
  mkdir -p "$(dirname "${destination}")"
  cp -R "${source}" "${destination}"
  find "${destination}" \
    \( -name '.git' -o -name 'node_modules' -o -name '__pycache__' \
       -o -name '.local' -o -name '.DS_Store' \) \
    -prune -exec rm -rf {} + 2>/dev/null || true
}

# Archive a directory so that the directory's own name is the single top level
# folder inside the zip. Unzipping into an empty directory then gives one
# folder, not a scatter of loose files, which is what the marker does with it.
make_zip() {
  local archive="$1" source_dir="$2" parent base
  parent="$(dirname "${source_dir}")"
  base="$(basename "${source_dir}")"
  rm -f "${archive}"
  if [ "${ZIP_TOOL}" = "zip" ]; then
    # -X drops uid, gid and extra timestamps, so two runs of this script differ
    # only in the archive's own mtimes and not in per file system noise.
    ( cd "${parent}" && zip -q -r -X "${archive}" "${base}" )
  else
    ( cd "${parent}" && python3 - "${archive}" "${base}" <<'PY'
import os
import sys
import zipfile

archive, base = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
    # Sorted walk, so the listing is in the same order every run and two runs
    # can be compared line by line.
    for directory, subdirs, names in os.walk(base):
        subdirs.sort()
        if not subdirs and not names:
            # An empty folder is a statement here, not an accident, so it is
            # written explicitly; zip -r would have carried it for free.
            info = zipfile.ZipInfo(directory.rstrip("/") + "/")
            info.external_attr = (0o40755 << 16) | 0x10
            bundle.writestr(info, "")
        for name in sorted(names):
            path = os.path.join(directory, name)
            bundle.write(path, path)
PY
    )
  fi
}

# Every file in a staged deliverable, relative to it, in a stable order. Used
# both for CONTENTS.md and for the closing report. find's -printf is a GNU
# extension and this may be run on a Mac, so the leading "./" is stripped in
# bash instead.
list_files() {
  ( cd "$1" && find . -type f -print | LC_ALL=C sort ) | while IFS= read -r file; do
    printf '%s\n' "${file#./}"
  done
}

say() { printf '%s\n' "$*"; }

say "Packaging the Week 4 midpoint submission"
say "----------------------------------------"
say "  output ${OUT#"${ROOT}/"}"
say "  archiver ${ZIP_TOOL}"
say ""

# --- deliverable A ----------------------------------------------------------
say "Deliverable A: annotated Week 3 material, the raw material, the summary"

A_DIR="${OUT}/deliverable-A"
mkdir -p "${A_DIR}"

# 1. The annotations. These are in git, so they are the one part of A that is
# certain to be here.
if [ -d "${W4}/annotations" ]; then
  copy_tree "${W4}/annotations" "${A_DIR}/annotations"
  found "annotations/ from deliverables/week4-midpoint/annotations/"
else
  missing "annotations/" "deliverables/week4-midpoint/annotations/ does not exist"
fi

# 2. The group's one-page summary. It is looked for in the place the repository
# rule says raw material lives first, and in the main branch folder second,
# because at submission time it may still be in either. Its name is the group's
# own and is not normalised: renaming somebody's file is how a marker ends up
# unable to match it against what the group described.
SUMMARY_NAME="one-page summary V2.md"
SUMMARY_FROM=""
for candidate in "${ROOT}/evidence/raw/week3/${SUMMARY_NAME}" \
                 "${ROOT}/week 3 materials/${SUMMARY_NAME}"; do
  if [ -f "${candidate}" ]; then
    SUMMARY_FROM="${candidate}"
    break
  fi
done
if [ -n "${SUMMARY_FROM}" ]; then
  # Also placed at the top of the zip, even though the copy below may carry it
  # again in its original folder. A marker opening the zip should not have to go
  # looking for the one page the brief asks for by name.
  cp "${SUMMARY_FROM}" "${A_DIR}/${SUMMARY_NAME}"
  found "${SUMMARY_NAME} from ${SUMMARY_FROM#"${ROOT}/"}"
else
  missing "${SUMMARY_NAME}" "not in evidence/raw/week3/ and not in 'week 3 materials/'"
fi

# 3. Everything under evidence/raw/week3/, which is the intended home of the raw
# material and is gitignored. Reported one top level entry at a time, because an
# empty folder here is the gap GAPS.md describes and must not read as a success.
RAW="${ROOT}/evidence/raw/week3"
if [ -d "${RAW}" ]; then
  copy_tree "${RAW}" "${A_DIR}/raw/week3"
  # A glob rather than find, so no GNU-only find flag is relied on; nullglob
  # keeps an empty week3/ from reporting a literal asterisk, dotglob catches a
  # file whose name starts with a dot.
  shopt -s nullglob dotglob
  for path in "${RAW}"/*; do
    entry="$(basename "${path}")"
    if [ -d "${path}" ] && [ -z "$(ls -A "${path}" 2>/dev/null)" ]; then
      missing "raw/week3/${entry}/" "the folder exists but is empty, so nothing of this kind is submitted"
    else
      found "raw/week3/${entry}"
    fi
  done
  shopt -u nullglob dotglob
else
  missing "raw/week3/" "evidence/raw/week3/ does not exist on this machine"
fi

# 4. The "week 3 materials/" folder, if this checkout has one. It holds the
# recordings, the transcripts and the MapIt report on the main branch. It is
# copied at run time and never into the working tree, because identifiable
# material does not enter the public repository.
WK3="${ROOT}/week 3 materials"
if [ -d "${WK3}" ]; then
  copy_tree "${WK3}" "${A_DIR}/week 3 materials"
  # Counted after the copy, not before: copy_tree prunes tool state, so a count
  # taken from the source would report files that are not in the zip.
  found "week 3 materials/ ($(find "${A_DIR}/week 3 materials" -type f | wc -l | tr -d ' ') files) from the checkout"
else
  missing "week 3 materials/" "not in this checkout; it is on the main branch and a decision about it is open, so the raw material is submitted from evidence/raw/week3/ instead"
fi

# 5. PLAN.md W3 once asked for a second summary, deliverables/week4-midpoint/
# summary.md. The group's own V2 summary above is that deliverable now
# (decisions/decision-log.md, 22 September), so nothing is looked for here and
# nothing is reported missing for it.

# 6. The manifest, generated now rather than maintained by hand, because a
# hand-maintained list of what is in a zip goes stale the first time the zip is
# rebuilt and then lies quietly.
{
  printf '# Deliverable A: contents\n\n'
  printf 'Generated by `deliverables/week4-midpoint/package.sh` on %s.\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')"
  printf 'Do not hand-edit this file: run the script again instead.\n\n'
  printf '## Files in this zip\n\n'
  while IFS= read -r file; do
    printf -- '- `%s`\n' "${file}"
  done < <(list_files "${A_DIR}")
  printf '\n## Expected, and not here\n\n'
  if [ "${#MISSING[@]}" -eq 0 ]; then
    printf 'Nothing expected is absent.\n'
  else
    for item in "${MISSING[@]}"; do
      printf -- '- %s\n' "${item}"
    done
  fi
  printf '\nThe full record of what the Week 3 material does not contain, and why,\n'
  printf 'is `annotations/GAPS.md` in this zip. The absences listed above are about\n'
  printf 'this package; the ones in GAPS.md are about the research.\n'
} > "${A_DIR}/CONTENTS.md"
found "CONTENTS.md, generated"

make_zip "${OUT}/deliverable-A.zip" "${A_DIR}"
A_FILE_COUNT="$(list_files "${A_DIR}" | wc -l | tr -d ' ')"
# The staged folder goes once it is zipped: deliverable A is submitted as a zip,
# and leaving an unzipped copy of raw material lying about invites somebody to
# hand in the wrong one.
rm -rf "${A_DIR}"
say ""

# --- deliverable B ----------------------------------------------------------
say "Deliverable B: the design proposal, slides, demo and the documents it cites"

B_DIR="${OUT}/deliverable-B"
mkdir -p "${B_DIR}"

if [ -d "${W4}/slides" ]; then
  copy_tree "${W4}/slides" "${B_DIR}/slides"
  found "slides/ from deliverables/week4-midpoint/slides/"
  # The three named slide files are checked one by one as well as copied
  # wholesale, because the deck is rebuilt right up to the rehearsal and a
  # missing deck.pdf is the one failure that is invisible until the room.
  for wanted in index.html NOTES.md deck.pdf; do
    if [ -f "${B_DIR}/slides/${wanted}" ]; then
      found "slides/${wanted}"
    else
      missing "slides/${wanted}" "not in deliverables/week4-midpoint/slides/"
    fi
  done
else
  missing "slides/" "deliverables/week4-midpoint/slides/ does not exist"
fi

if [ -d "${W4}/demo" ]; then
  copy_tree "${W4}/demo" "${B_DIR}/demo"
  found "demo/ from deliverables/week4-midpoint/demo/"
else
  missing "demo/" "deliverables/week4-midpoint/demo/ does not exist"
fi

# Only the markdown twins of the documentation, not the HTML ones: they carry
# the same content at a fraction of the size, and they are what the deck cites.
mkdir -p "${B_DIR}/documentation"
for document in stack.md flowchart.md pipelines.md; do
  if [ -f "${ROOT}/deliverables/documentation/${document}" ]; then
    cp "${ROOT}/deliverables/documentation/${document}" "${B_DIR}/documentation/${document}"
    found "documentation/${document}"
  else
    missing "documentation/${document}" "not in deliverables/documentation/"
  fi
done

# SUBMISSION.md sits at the top of the output folder and again inside
# deliverable B, so that the folder is readable on its own once it is detached
# from the rest of the submission.
if [ -f "${W4}/SUBMISSION.md" ]; then
  cp "${W4}/SUBMISSION.md" "${B_DIR}/SUBMISSION.md"
  cp "${W4}/SUBMISSION.md" "${OUT}/SUBMISSION.md"
  found "SUBMISSION.md, at the top of the output and inside deliverable B"
else
  missing "SUBMISSION.md" "deliverables/week4-midpoint/SUBMISSION.md does not exist"
fi

make_zip "${OUT}/deliverable-B.zip" "${B_DIR}"
B_FILE_COUNT="$(list_files "${B_DIR}" | wc -l | tr -d ' ')"
say ""

# --- the closing report -----------------------------------------------------
say "========================================================================"
say "Submission built"
say "  ${OUT}"
say ""
say "  deliverable-A.zip   ${A_FILE_COUNT} files, zipped, staging folder removed"
say "  deliverable-B/      ${B_FILE_COUNT} files, kept as a folder"
say "  deliverable-B.zip   the same folder, zipped"
say "  SUBMISSION.md       what is in each deliverable, and what is not"
say ""
say "Deliverable A holds:"
say "  annotations/        the four annotation files, INDEX.md and GAPS.md"
say "  ${SUMMARY_NAME}"
say "  raw/week3/          whatever evidence/raw/week3/ held at run time"
say "  week 3 materials/   only if this checkout had the folder"
say "  CONTENTS.md         generated, lists every file and every absence"
say ""
say "Deliverable B holds:"
say "  slides/             index.html, NOTES.md, deck.pdf and anything beside them"
say "  demo/               start.sh, step.sh, stop.sh, RUNBOOK.md, fallback shots"
say "  documentation/      stack.md, flowchart.md, pipelines.md"
say "  SUBMISSION.md"
say ""
if [ "${#MISSING[@]}" -eq 0 ]; then
  say "Nothing expected is missing."
else
  # Deliverable A's CONTENTS.md is written before its zip is sealed, so it can
  # only carry A's absences. This block is the one place both deliverables'
  # absences are listed together.
  say "Missing, ${#MISSING[@]} items. The deliverable A ones are in its CONTENTS.md too:"
  for item in "${MISSING[@]}"; do
    say "  - ${item}"
  done
fi
say ""
say "The raw Week 3 material is submitted from the group's own machine. None of"
say "it is in the repository and this script never copies any of it into the tree."
say "========================================================================"
