# Build the RSS 2027 paper.
# Needs latexmk, pdflatex, bibtex, and poppler-utils (pdfinfo/pdffonts) for
# `make check`. Ubuntu: sudo apt install latexmk texlive-latex-extra \
#   texlive-science texlive-fonts-recommended poppler-utils
# IEEEtran.cls (v1.7a, from the official RSS template) ships in this folder.

MAIN    := main
LATEXMK := latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error

.PHONY: all pdf submission check clean distclean

all: pdf

# Draft build: author names and TODO notes visible -> main.pdf
pdf:
	$(LATEXMK) $(MAIN).tex

# Anonymous build for RSS review: notes hidden, anonymous author block and
# PDF metadata -> main_submission.pdf
submission:
	$(LATEXMK) -jobname=$(MAIN)_submission \
	  -usepretex='\def\papermode{submission}' $(MAIN).tex

# Quick compliance checks on the anonymous build
check: submission
	@pdf=$(MAIN)_submission.pdf; \
	echo "Pages: $$(pdfinfo $$pdf | awk '/^Pages:/{print $$2}')  (Stage 1: max 5 pages of content + 1 page of references)"; \
	echo "PDF metadata (no author names allowed in review):"; \
	pdfinfo $$pdf | grep -E '^(Title|Author|Subject|Keywords):' || true; \
	if pdffonts $$pdf | awk 'NR>2' | grep -q 'Type 3'; then echo "WARNING: Type 3 fonts found"; else echo "Fonts: no Type 3 fonts"; fi; \
	if pdffonts $$pdf | awk 'NR>2 && $$(NF-4)!="yes"' | grep -q .; then echo "WARNING: some fonts are not embedded"; else echo "Fonts: all embedded"; fi; \
	grep -h 'skeleton outline block' $(MAIN)_submission.log || true

clean:
	latexmk -c $(MAIN).tex
	latexmk -c -jobname=$(MAIN)_submission $(MAIN).tex
	rm -f *.bbl

distclean: clean
	rm -f $(MAIN).pdf $(MAIN)_submission.pdf
