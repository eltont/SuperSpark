#!/usr/bin/env bash
# Source this to use the user-local toolchain.
if [[ -x "${HOME}/.homebrew/bin/brew" ]]; then
  eval "$("${HOME}/.homebrew/bin/brew" shellenv)"
fi
if [[ -d "${HOME}/.homebrew/opt/openjdk@17" ]]; then
  export JAVA_HOME="${HOME}/.homebrew/opt/openjdk@17"
  export PATH="${JAVA_HOME}/bin:${PATH}"
fi
export SUPERSPARK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="${SUPERSPARK_ROOT}/scripts:${SUPERSPARK_ROOT}/runner/bin:${PATH}"
