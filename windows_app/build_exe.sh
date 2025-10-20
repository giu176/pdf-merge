#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export WINEARCH="win64"
export WINEPREFIX="${WINEPREFIX:-$HOME/.wine}"

PY_VERSION="${PY_VERSION:-3.11.5}"
PY_INSTALLER_URL="https://www.python.org/ftp/python/${PY_VERSION}/python-${PY_VERSION}-amd64.exe"
TMP_DIR="$(mktemp -d)"
cleanup() {
    rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

APT_UPDATED=0
apt_update_once() {
    if [ "${APT_UPDATED}" -eq 0 ]; then
        sudo apt-get update
        APT_UPDATED=1
    fi
}

ensure_packages() {
    apt_update_once
    sudo apt-get install -y --no-install-recommends "$@"
}

for cli_dep in curl rsync; do
    if ! command -v "${cli_dep}" >/dev/null 2>&1; then
        echo "Installing ${cli_dep}..."
        ensure_packages "${cli_dep}"
    fi
done

if ! command -v wine >/dev/null 2>&1; then
    echo "Installing Wine and helper packages..."
    apt_update_once
    wine_package="wine32"
    if ! apt-cache show "${wine_package}" >/dev/null 2>&1; then
        echo "${wine_package} not available; falling back to the generic wine package."
        wine_package="wine"
    fi
    ensure_packages "${wine_package}" winbind cabextract unzip
fi

mkdir -p "${WINEPREFIX}"
wineboot -i >/dev/null 2>&1 || true

PY_INSTALLER_PATH="${TMP_DIR}/python-installer.exe"
if [ ! -f "${PY_INSTALLER_PATH}" ]; then
    echo "Downloading Windows Python ${PY_VERSION}..."
    curl -L "${PY_INSTALLER_URL}" -o "${PY_INSTALLER_PATH}"
fi

echo "Installing Windows Python inside the Wine prefix..."
wine "${PY_INSTALLER_PATH}" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1

PYTHON_EXE="$(find "${WINEPREFIX}/drive_c" -type f -name python.exe | grep -i "Python3" | head -n 1)"
if [ -z "${PYTHON_EXE}" ]; then
    echo "Unable to locate python.exe inside ${WINEPREFIX}" >&2
    exit 1
fi

echo "Bootstrapping pip and build dependencies..."
wine "${PYTHON_EXE}" -m pip install --upgrade pip
wine "${PYTHON_EXE}" -m pip install --upgrade pyinstaller PyMuPDF

TARGET_DIR="${WINEPREFIX}/drive_c/pdf-merge"
rm -rf "${TARGET_DIR}"
mkdir -p "${TARGET_DIR}"

rsync -a --delete \
    --exclude '.git' \
    --exclude 'dist' \
    --exclude 'build' \
    --exclude '__pycache__' \
    "${REPO_ROOT}/" "${TARGET_DIR}/"

pushd "${TARGET_DIR}" >/dev/null

echo "Building the Windows executable with PyInstaller..."
wine "${PYTHON_EXE}" -m PyInstaller \
    --clean \
    --distpath dist \
    --workpath build \
    windows_app\\pyinstaller.spec

popd >/dev/null

echo "Build complete. The executable is located at:"
echo "${TARGET_DIR}/dist/windows_app.exe"

mkdir -p "${REPO_ROOT}/dist"
cp "${TARGET_DIR}/dist/windows_app.exe" "${REPO_ROOT}/dist/windows_app.exe"

echo "A copy has been placed in:"
echo "${REPO_ROOT}/dist/windows_app.exe"
