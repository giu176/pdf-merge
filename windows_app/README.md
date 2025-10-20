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

The Windows automation expects this package so that PyInstaller can discover a
stable entry point. To produce a Windows binary manually, activate the project
virtual environment and run the following command from the repository root:

```bash
pyinstaller --noconsole --onefile windows_app/main.py --name pdf-merge
```

This generates a standalone executable in the `dist/` folder that uses the same
logic and configuration as the cross-platform scripts.
