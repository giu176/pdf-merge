#!/usr/bin/env bash

set -euo pipefail

if [[ $(id -u) -ne 0 ]]; then
    SUDO="sudo"
else
    SUDO=""
fi

APT_PACKAGES=(
    python3
    python3-pip
    python3-venv
    poppler-utils
    pdftk-java
)

printf 'Updating package lists...\n'
$SUDO apt-get update -y

printf 'Installing system dependencies...\n'
$SUDO apt-get install -y "${APT_PACKAGES[@]}"

if [[ ! -d .venv ]]; then
    printf 'Creating Python virtual environment...\n'
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

printf 'Upgrading pip and installing Python dependencies...\n'
pip install --upgrade pip

if [[ -f requirements.txt ]]; then
    pip install -r requirements.txt
else
    printf 'No requirements.txt found; skipping Python package installation.\n'
fi

printf '\nAll dependencies installed successfully. Activate the virtual environment with:\n'
printf '    source .venv/bin/activate\n'
printf 'and run the application using:\n'
printf '    python3 pdf.py\n'
