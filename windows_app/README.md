# Windows Application Bundle

This directory contains a Windows-native launcher for the PDF merge utility.
It provides both a command line interface and a graphical interface that mirror
the behaviour of the cross-platform scripts in the repository.  The application
can be packaged into a single self-contained `.exe` so that it runs on a vanilla
Windows installation without requiring Python or any other external runtime.

## Features

* Launch the same Tk-based graphical interface that ships with the project.
* Run the full command line workflow when template, input and output paths are
  supplied.
* Support for scaling pages, removing the first input page, optionally deleting
  the template once the merge is complete and performing append-only merges.
* Automatic detection of invalid configurations with descriptive error
  messages.

## Building the executable

1. Ensure you have Python 3.11 (or newer) installed on Windows together with
   the project dependencies:

   ```powershell
   py -3.11 -m pip install -r requirements.txt
   ```

2. Install PyInstaller, which is used to create the standalone executable:

   ```powershell
   py -3.11 -m pip install pyinstaller
   ```

3. Run the build helper script from the repository root.  It wraps PyInstaller
   with the correct options to bundle PyMuPDF and the project modules:

   ```powershell
   py -3.11 windows_app\build_exe.py
   ```

   The resulting executable is placed in `windows_app\dist\pdf-merge.exe`.

The generated binary bundles the Python interpreter, the Tk GUI toolkit and the
PyMuPDF native libraries so that the program can be executed directly.  Simply
copy the produced `pdf-merge.exe` to the target machine and run it.

## Manual PyInstaller invocation

If you prefer to run PyInstaller yourself, execute the following from the
repository root:

```powershell
py -3.11 -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name pdf-merge ^
    --collect-all fitz ^
    windows_app\windows_main.py
```

The `--collect-all fitz` option instructs PyInstaller to include the binary
resources shipped with PyMuPDF so that no extra installation steps are needed.

## Running the executable

Double-clicking `pdf-merge.exe` launches the graphical interface.  To use the
command line interface, open `cmd.exe` or PowerShell and run:

```powershell
pdf-merge.exe --help
```

Arguments are identical to those supported by `pdf.py` at the project root.
