#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export WINEARCH="win64"
export WINEPREFIX="${WINEPREFIX:-$HOME/.wine}"

wineprefix_architecture_matches() {
    local reg_file="${WINEPREFIX}/system.reg"
    local expected_tag="#arch=${WINEARCH}"

    if [ ! -f "${reg_file}" ]; then
        return 1
    fi

    if grep -qxF "${expected_tag}" "${reg_file}"; then
        return 0
    fi

    return 1
}

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

ensure_i386_architecture() {
    if ! dpkg --print-foreign-architectures | grep -qx "i386"; then
        echo "Enabling i386 architecture support..."
        sudo dpkg --add-architecture i386
        # Ensure package lists are refreshed for the new architecture on next update.
        APT_UPDATED=0
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
    ensure_i386_architecture
    apt_update_once
    ensure_packages wine64 wine32:i386 winbind cabextract unzip
fi

ensure_vulkan_runtime() {
    local required_packages=(
        libvulkan1
        libvulkan1:i386
        mesa-vulkan-drivers
        mesa-vulkan-drivers:i386
    )

    local missing_packages=()

    for pkg in "${required_packages[@]}"; do
        if ! dpkg -s "${pkg}" >/dev/null 2>&1; then
            missing_packages+=("${pkg}")
        fi
    done

    if [ ${#missing_packages[@]} -gt 0 ]; then
        echo "Installing Vulkan runtime dependencies for Wine (${missing_packages[*]})..."
        ensure_i386_architecture
        apt_update_once
        ensure_packages "${missing_packages[@]}"
    fi
}

ensure_vulkan_runtime

vulkan_runtime_available() {
    if command -v ldconfig >/dev/null 2>&1; then
        if ldconfig -p | grep -q "libvulkan.so.1"; then
            return 0
        fi
    fi

    local lib_paths=(
        /usr/lib/x86_64-linux-gnu/libvulkan.so.1
        /usr/lib/i386-linux-gnu/libvulkan.so.1
        /usr/lib64/libvulkan.so.1
        /usr/lib/libvulkan.so.1
    )

    for lib_path in "${lib_paths[@]}"; do
        if [ -e "${lib_path}" ]; then
            return 0
        fi
    done

    return 1
}

append_wine_override() {
    local override="$1"

    if [ -z "${WINEDLLOVERRIDES:-}" ]; then
        export WINEDLLOVERRIDES="${override}"
    else
        export WINEDLLOVERRIDES="${WINEDLLOVERRIDES};${override}"
    fi
}

if ! vulkan_runtime_available; then
    echo "Warning: libvulkan.so.1 could not be found on this system. Disabling Vulkan for Wine." >&2
    echo "Install libvulkan1 and mesa-vulkan-drivers packages for best performance." >&2
    append_wine_override "vulkan-1=d"
    append_wine_override "vulkan=d"
fi

if [ -d "${WINEPREFIX}" ] && ! wineprefix_architecture_matches; then
    current_arch="$(grep -m1 '^#arch=' "${WINEPREFIX}/system.reg" | cut -d= -f2 | tr -d '\r' || true)"
    if [ -z "${current_arch}" ]; then
        current_arch="unknown"
    fi
    echo "Existing Wine prefix at ${WINEPREFIX} uses architecture '${current_arch}', but '${WINEARCH}' is required. Recreating prefix..." >&2
    rm -rf "${WINEPREFIX}"
fi

mkdir -p "${WINEPREFIX}"
echo "Initializing Wine prefix (this may take a moment)..."
wineboot -i

if ! wineprefix_architecture_matches; then
    echo "Wine prefix at ${WINEPREFIX} did not initialize with required architecture '${WINEARCH}'." >&2
    exit 1
fi

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
