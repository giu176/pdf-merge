# pdf-merge

Utility for combining PDF templates with generated documents.

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
