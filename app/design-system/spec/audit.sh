#!/usr/bin/env bash
# =============================================================================
# Jarvaids design system: the mechanical half of the audit.
#
# Everything in here either passes or fails. The judgement half, the part a
# grep cannot do, is in AUDIT.md section 3 and is still a human reading a
# screen.
#
# Usage:   spec/audit.sh [path ...]
#          spec/audit.sh app/client
#
# With no argument it audits the application source directories. It NEVER
# audits the design system's own files: this file is where the literals are
# supposed to live, so pointing the audit at it returns hundreds of hits and
# an audit whose first run is all noise is an audit nobody runs twice.
#
# Exit 0 = clean. Exit 1 = at least one check found something.
#
# Every regex here is tested against a legal and an illegal fixture before it
# ships. Three earlier versions of these checks used PCRE lookaheads under
# `grep -E`, which does not support them: they printed a warning, matched the
# LEGAL value and missed the illegal one, so a third typeface passed the audit
# clean. Note the possessive `\s*+`. Without it the `\s*` backtracks to zero
# width and the lookahead succeeds against the space, which is the same bug
# wearing a different hat.
# =============================================================================
set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEM_DIR="$(dirname "$SELF_DIR")"
REPO_ROOT="$(cd "$SYSTEM_DIR/../.." && pwd)"

if [ "$#" -gt 0 ]; then
  TARGETS=("$@")
else
  TARGETS=(app/client app/server)
fi

# Drop targets that do not exist yet, so a fresh repo does not fail on paths
# that are simply empty.
EXISTING=()
for t in "${TARGETS[@]}"; do
  [ -e "$t" ] && EXISTING+=("$t")
done

if [ "${#EXISTING[@]}" -eq 0 ]; then
  echo "audit: no application source to check yet (looked in: ${TARGETS[*]})"
  echo "audit: the design system's own files are never audited, see the header"
  exit 0
fi

# .mjs matters: the whole client is ES modules, so without it the audit saw
# none of the code that actually renders the product.
INCLUDE=(--include='*.css' --include='*.html' --include='*.tsx' --include='*.jsx' --include='*.ts' --include='*.js' --include='*.mjs' --include='*.vue' --include='*.svelte')
EXCLUDE=(--exclude-dir=node_modules --exclude-dir=.git --exclude-dir=dist --exclude-dir=build --exclude-dir="$(basename "$SYSTEM_DIR")")

FAILED=0

# The client's token file is where its literals are supposed to live, the
# same reason the design system's own folder is excluded above, and its
# fonts folder holds the faces and their licences. Both are left out of the
# literal checks (section 2) only; every other check still reads them. The
# pattern matches the path however the target was spelled.
LITERAL_HOME='(^|/)app/client/(tokens\.css|fonts/)'

check() {
  local name="$1" engine="$2" pattern="$3" scope="${4:-all}"
  local out
  out="$(grep -rn"$engine" "$pattern" "${INCLUDE[@]}" "${EXCLUDE[@]}" "${EXISTING[@]}" 2>/dev/null)"
  if [ "$scope" = "literal" ] && [ -n "$out" ]; then
    out="$(printf '%s\n' "$out" | grep -Ev "$LITERAL_HOME" || true)"
  fi
  if [ -n "$out" ]; then
    printf '\n  FAIL  %s\n' "$name"
    printf '%s\n' "$out" | sed 's/^/        /'
    FAILED=1
  else
    printf '  ok    %s\n' "$name"
  fi
}

echo "Auditing: ${EXISTING[*]}"
echo "Excluding the design system itself: $(basename "$SYSTEM_DIR")/"
echo

# --- 1. contrast -------------------------------------------------------------
# The client's tokens are app/client/tokens.css, and its contrast test parses
# that file and measures every text-on-colour pair the client ships. The
# design system's Python tool (contrast-check.py) reads the previous token
# file, which the UI overhaul deleted. It is not edited, because the overhaul
# changes no .py file, so this step runs the client's test instead. Resolved
# from this script's own location, so it runs from any directory.
CONTRAST_TEST="$REPO_ROOT/app/client/tests/contrast-unit.mjs"
if node --test "$CONTRAST_TEST" >/dev/null 2>&1; then
  echo "  ok    contrast: every text-on-colour pair in app/client/tokens.css meets AA"
else
  echo "  FAIL  contrast: run node --test $CONTRAST_TEST for the pairs"
  FAILED=1
fi

# --- 2. literals that should be tokens ---------------------------------------
# The negative lookahead keeps DOM id selectors out: `#add-note` is three
# hex characters followed by a hyphen, and it is an element, not a colour.
# Without it, widening this audit to .mjs reports every such selector.
# The token file holds the @font-face rules, so it is the one place a
# font-family names a face; everywhere else it is var( or inherit.
check "no raw hex colours"        P '#[0-9a-fA-F]{3,8}(?![-_0-9a-zA-Z])' literal
check "no arbitrary radii"        P 'border-radius:\s*+(?!(?:2px|4px|999px|var\())' literal
check "no non-system typefaces"   P 'font-family:\s*+(?!(?:var\(|inherit))' literal
check "one breakpoint only"       P '@media[^{]*\b(?:min|max)-width:\s*+(?!(?:1023px|1024px))'
check "no arbitrary line widths"  P '(?:border|outline)(?:-[a-z]+)?-width:\s*+(?!(?:var\()|(?:0)|(?:1px)|(?:2px))' literal
check "no Tailwind palette"       P '\b(?:bg|text|border|ring|fill|stroke)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-[0-9]{2,3}\b'

# --- 3. things this system forbids outright ----------------------------------
# Shadows only on floating surfaces, and only as the shadow token: a literal
# shadow, or one on page content, is the decoration this system refuses. The
# client has one shadow, --shadow (app/client/tokens.css); the previous
# system's three elevation tokens stay allowed for the pages that still link
# its stylesheet.
check "no shadows on content"     P 'box-shadow:\s*+(?!(?:none|var\(--shadow\)|var\(--elevation-(?:sm|md|lg)\)))'
check "no toasts or spinners"     P '\b(?:toast|Toast|spinner|Spinner)\b'
check "no CDN or network font"    P '(?:https?:)?//(?:fonts\.googleapis|fonts\.gstatic|cdn\.|unpkg|jsdelivr)'
check "no text glyphs as icons"   P '>[[:space:]]*[✓✔✕✖×▾▴▸◂→←][[:space:]]*<'

# --- 4. the rules that carry the product -------------------------------------
# forbidden.md #16, #17, #18. The A/B audit found these three were the only
# rules left to human judgement, which is the wrong half to leave unenforced:
# they are the ones that, broken once, make the product dishonest. Two of the
# three are mechanically checkable, so they are checked here.
check "provisional is never dimmed"        P 'provisional[^\n]{0,80}(?:opacity|ink-muted)'
check "provisional is never a plain fill"  P 'provisional[^\n]{0,80}background:\s*+(?!(?:none|transparent))'

echo
if [ "$FAILED" -eq 0 ]; then
  echo "Clean. The judgement half of the audit is AUDIT.md section 3."
else
  echo "Violations above. Each one is either a fix or an exception explained in"
  echo "the pull request. There is no third option."
fi
exit "$FAILED"
