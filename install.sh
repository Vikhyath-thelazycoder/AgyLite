#!/usr/bin/env bash
# Agylite one-line installer:
#   curl -fsSL https://raw.githubusercontent.com/Vikhyath-thelazycoder/AgyLite/main/install.sh | bash
# Clones Agylite, runs scripts/install (central install into ~/.agylite and the local capability bundle: the pinned
# upstreams are fetched once, ~2 minutes), and puts `agylite` on your PATH. Re-running it updates an existing install.
set -euo pipefail
REPO="${AGYLITE_REPO:-https://github.com/Vikhyath-thelazycoder/AgyLite.git}"
REF="${AGYLITE_REF:-main}"
HOME_DIR="${AGYLITE_HOME:-$HOME/.agylite}"
command -v git >/dev/null || { echo "Agylite needs git." >&2; exit 1; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
echo "→ Downloading Agylite ($REF)"
git clone --quiet --depth 1 --branch "$REF" "$REPO" "$WORK/agylite"
AGYLITE_HOME="$HOME_DIR" bash "$WORK/agylite/scripts/install"

BIN="$HOME_DIR/core/bin"
LINE="export PATH=\"$BIN:\$PATH\""
case "${SHELL:-}" in
  */zsh) RC="$HOME/.zshrc" ;;
  */bash) RC="$HOME/.bashrc"; [ "$(uname)" = Darwin ] && RC="$HOME/.bash_profile" ;;
  *) RC="" ;;
esac
if [ -n "$RC" ] && ! grep -qsF "$BIN" "$RC"; then
  printf '\n# Agylite\n%s\n' "$LINE" >> "$RC"
  echo "→ Added Agylite to PATH in $RC (open a new terminal)"
fi
echo
echo "Next, in Claude Code (if you have not added the plugin yet):"
echo "  /plugin marketplace add Vikhyath-thelazycoder/AgyLite"
echo "  /plugin install agylite@agylite-marketplace"
echo "Then start a new session. Check anytime with: agylite doctor"
