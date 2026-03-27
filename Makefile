MDFILES = $(wildcard docs/*.md)
TESTFILES = $(patsubst docs/%.md, tests/test_%.py, $(MDFILES))

.PHONY: all test clean

all: test testfiles

testfiles: $(TESTFILES)

tests/test_%.py: docs/%.md
	echo "Generating test file for $<"
	phmdoctest $< --outfile $@

tests/test_readme.py: README.md
	echo "Generating test file for README.md"
	phmdoctest README.md --outfile tests/test_readme.py

test: $(TESTFILES) tests/test_readme.py
	pytest -q

clean:
	echo "Cleaning up generated test files" $(TESTFILES)