PDFLATEX ?= /Library/TeX/texbin/pdflatex
BIBTEX ?= /Library/TeX/texbin/bibtex
UV ?= uv
MAIN := main
FIGURES_SCRIPT := ../scripts/paper_figures.py
FIGURES := figures/fig_identity_ablation.pdf figures/fig_policy_generalisation.pdf \
	figures/fig_stacking.pdf figures/fig_approval_curve.pdf figures/fig_self_judgment.pdf \
	figures/fig_judge_agreement.pdf

.PHONY: all clean figures

all: figures $(MAIN).pdf

figures: $(FIGURES)

$(FIGURES): $(FIGURES_SCRIPT)
	cd .. && $(UV) run python scripts/paper_figures.py

$(MAIN).pdf: $(MAIN).tex sections/*.tex appendix.tex refs.bib $(FIGURES)
	$(PDFLATEX) -interaction=nonstopmode -halt-on-error $(MAIN).tex
	$(BIBTEX) $(MAIN)
	$(PDFLATEX) -interaction=nonstopmode -halt-on-error $(MAIN).tex
	$(PDFLATEX) -interaction=nonstopmode -halt-on-error $(MAIN).tex

clean:
	rm -f $(MAIN).pdf $(MAIN).aux $(MAIN).bbl $(MAIN).blg $(MAIN).log \
		$(MAIN).out $(MAIN).toc $(MAIN).synctex.gz $(MAIN).fls \
		$(MAIN).fdb_latexmk texput.log
