#!/bin/bash
virtualenv scripts -p python3
. scripts/bin/activate
pip3 install pdf2image
pip3 install docx
pip3 install python-docx
pip3 install pypdf2
pip3 install pymupdf
deactivate