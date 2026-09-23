#!/bin/sh
# Build the NAACL/ACL-format PDF (naacl.tex); the Makefile builds the ICLR one.
set -e
cd "$(dirname "$0")"
PDFLATEX=${PDFLATEX:-/Library/TeX/texbin/pdflatex}
BIBTEX=${BIBTEX:-/Library/TeX/texbin/bibtex}
$PDFLATEX -interaction=nonstopmode -halt-on-error naacl.tex >/dev/null
$BIBTEX naacl >/dev/null
$PDFLATEX -interaction=nonstopmode -halt-on-error naacl.tex >/dev/null
$PDFLATEX -interaction=nonstopmode -halt-on-error naacl.tex >/dev/null
