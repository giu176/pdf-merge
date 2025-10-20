# Windows application wrapper

This package contains the Windows specific launch code for the PDF merge tool.
It reuses the shared PDF manipulation logic from `pdf_processing.py` and exposes
it through a lightweight Tkinter interface that can be packaged for Windows
users.

## Shared logic

The UI constructs a `pdf_processing.MergeConfig` instance and invokes
`pdf_processing.merge_pdfs()` to perform the merge. By relying on the common
module, new behaviour that is added to the core logic automatically becomes
available in the Windows desktop build without having to duplicate it.

## Running locally

You can exercise the Windows GUI entry point directly from the repository root:

```bash
python -m windows_app
```

## Building the Windows executable

The repository provides an automated build that runs PyInstaller inside a Wine
prefix. The helper script downloads a Windows edition of Python, installs the
required dependencies (`PyMuPDF` and `pyinstaller`), and then executes the
packaging step with the bundled `pyinstaller.spec` file.

### Prerequisites

- Debian/Ubuntu environment with `curl`, `rsync`, and `sudo` available.
- Internet access to download the Windows Python installer and Python packages.

### Step-by-step

Run the build script from the repository root:

```bash
./windows_app/build_exe.sh
```

The script will:

1. Install Wine (if missing) so that Windows binaries can be executed.
2. Download and install a Windows Python distribution inside `~/.wine`.
3. Install `pyinstaller` and `PyMuPDF` inside the Wine-managed Python
   environment.
4. Copy the current project into the Wine prefix.
5. Invoke PyInstaller with `windows_app/pyinstaller.spec`, which collects the
   `PyMuPDF` runtime libraries and any packaged GUI assets.

When the build finishes, the Windows executable is available at:

```
~/.wine/drive_c/pdf-merge/dist/windows_app.exe
```

The script also copies the binary back to the repository as `dist/windows_app.exe`
for convenience.

### Manual invocation

If you already have a Windows Python environment set up, you can trigger the
build manually by running PyInstaller against the provided spec file:

```bash
pyinstaller --distpath dist --workpath build windows_app/pyinstaller.spec
```

The spec embeds the GUI resources and ensures that all `PyMuPDF` binaries are
bundled with the final executable.
