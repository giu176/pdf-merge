# pdf-merge

Utility for combining PDF templates with generated documents.

## Prerequisites (Windows + WSL)

If you are running the project from Windows via the Windows Subsystem for
Linux (WSL), complete the following steps before running the installer:

1. Enable the "Windows Subsystem for Linux" and "Virtual Machine Platform"
   features from **Control Panel → Programs → Turn Windows features on or
   off**, or run `wsl --install` from an elevated PowerShell session on Windows
   11 to enable them automatically.
2. Install the [Debian distribution from the Microsoft
   Store](https://apps.microsoft.com/detail/9MSVKQC78PK6).
3. Launch Debian from the Start Menu to finish the initial user setup.
4. Inside the Debian shell, update the package index, install Git, clone the
   repository, and launch the installer with the following one-liner:

   ```bash
   sudo apt update && sudo apt upgrade -y && sudo apt install -y git && \
   git clone https://github.com/giu176/pdf-merge.git && cd pdf-merge && sudo ./install.sh
   ```

## One-click setup

The project includes an installation script that fetches all required system and
Python dependencies. Run it from the repository root:

```bash
./install.sh
```

The script will:

- Install the system packages used to manipulate PDF files (`poppler-utils`
  and `pdftk-java`) alongside Python tooling.
- Create a virtual environment in `.venv` if one does not already exist.
- Install the Python dependency [`PyMuPDF`](https://pymupdf.readthedocs.io/),
  which powers the PDF processing utilities.

Activate the virtual environment before running the application:

```bash
source .venv/bin/activate
```

## Usage

### Graphical interface

Launch the GUI with:

```bash
python3 pdf.py
```

### Command line interface

To use the command line interface supply the template, input and output
paths (additional options are available via `--help`):

```bash
python3 pdf.py template.pdf input.pdf output.pdf
```

### Windows shortcut

If you are running the project inside the Debian WSL distribution, you can start
it from Windows with the provided `run_pdf_merge.bat` script. The batch file
launches Debian, switches to `/home/pdf-merge`, activates the virtual
environment when available, and invokes `python3 pdf.py`.

Double-clicking the script (after `install.sh` has created the `.venv`
directory) opens the application using the existing environment.

#### WSL file dialogs

When the GUI detects that it is running inside WSL it opens file dialogs in the
Windows user directory (for example `/mnt/c/Users`). Selected Windows-style
paths are transparently converted to their `/mnt/...` equivalents via
[`wslpath`](https://learn.microsoft.com/windows/wsl/filesystems#use-the-wslpath-command),
so subsequent processing continues to work with POSIX-style paths. If the
Windows user directory is not mounted (for example, on a non-standard setup),
the dialogs fall back to the Linux home directory.

