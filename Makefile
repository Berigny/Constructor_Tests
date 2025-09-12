# Quick helpers for installing and running the evaluator

SHELL := /bin/bash
PY ?= python3
PIP ?= $(PY) -m pip
SCRIPT := constructor_eval.py

# Defaults (can be overridden: make run INPUT=path/to.csv OUT_DIR=out2 ...)
INPUT ?= constructor_tests_sheet1_1.csv
URL_COL ?= URL Query
BUDGET_COL ?= Budget
PROFILE_COL ?= Profile_Description
FILTERS_COL ?= Filters
OUT_DIR ?= out
TOPK ?= 3
HUMAN_SCORES ?=
URL_BASE ?= https://www.kmart.com.au

FLAGS = \
  --input "$(INPUT)" \
  --url-col "$(URL_COL)" \
  --budget-col "$(BUDGET_COL)" \
  --profile-col "$(PROFILE_COL)" \
  --filters-col "$(FILTERS_COL)" \
  --out-dir "$(OUT_DIR)" \
  --topk $(TOPK)

URL_FLAGS = --url-base "$(URL_BASE)"

.PHONY: help install venv install-venv run run-autocheck run-merge print-urls prompts requery-fixes clean

help:
	@echo "Constructor Evaluator Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  install         Install requirements into current Python env"
	@echo "  venv            Create .venv (no install)"
	@echo "  install-venv    Create .venv and install requirements"
	@echo "  run             Run and print $(PWD)/$(OUT_DIR)/eval_autocheck.csv"
	@echo "  run-autocheck   Generate out/results_flat.csv and eval_autocheck.csv"
	@echo "  run-merge       Merge with human scoring (set HUMAN_SCORES=...)"
	@echo "  print-urls      Print only product URLs (uses URL_BASE)"
	@echo "  prompts         Emit per-test LLM prompts to $(OUT_DIR)/prompts/"
	@echo "  requery-fixes   Apply LLM fixes from $(OUT_DIR)/llm_fixes and re-evaluate"
	@echo "  clean           Remove output directory (OUT_DIR=$(OUT_DIR))"
	@echo ""
	@echo "Variables (override via make VAR=value):"
	@echo "  INPUT=$(INPUT) URL_COL=$(URL_COL) BUDGET_COL=$(BUDGET_COL) PROFILE_COL=$(PROFILE_COL) FILTERS_COL=$(FILTERS_COL) OUT_DIR=$(OUT_DIR) TOPK=$(TOPK)"
	@echo "  HUMAN_SCORES=$(HUMAN_SCORES)"
	@echo ""
	@echo "Examples:"
	@echo "  make install"
	@echo "  make run OUT_DIR=out" 
	@echo "  make run-merge HUMAN_SCORES=Constructor_Gift_Scoring_Sheet.csv"

install:
	$(PIP) install -r requirements.txt

venv:
	$(PY) -m venv .venv
	@echo "Created .venv. Activate with: source .venv/bin/activate"

install-venv: venv
	. .venv/bin/activate && pip install -U pip && pip install -r requirements.txt
	@echo "Installed into .venv. Activate with: source .venv/bin/activate"

run: run-autocheck
	@echo "---- $(PWD)/$(OUT_DIR)/eval_autocheck.csv ----"
	@cat "$(OUT_DIR)/eval_autocheck.csv" || true
	@echo "\n---- Product URLs -> $(PWD)/$(OUT_DIR)/product_urls.txt ----"
	@$(PY) $(SCRIPT) $(FLAGS) $(URL_FLAGS) --print-urls-grouped > "$(OUT_DIR)/product_urls.txt" || true
	@wc -l "$(OUT_DIR)/product_urls.txt" 2>/dev/null | awk '{print $1, "URLs"}' || true

run-autocheck:
	$(PY) $(SCRIPT) $(FLAGS) $(URL_FLAGS)

run-merge:
	@if [ -z "$(HUMAN_SCORES)" ]; then \
	  echo "HUMAN_SCORES not set. Example: make run-merge HUMAN_SCORES=Constructor_Gift_Scoring_Sheet.csv"; \
	  exit 1; \
	fi
	$(PY) $(SCRIPT) $(FLAGS) $(URL_FLAGS) --human-scores "$(HUMAN_SCORES)"

print-urls:
	$(PY) $(SCRIPT) $(FLAGS) $(URL_FLAGS) --print-urls-only

prompts:
	$(PY) $(SCRIPT) $(FLAGS) $(URL_FLAGS) --emit-llm-prompts

requery-fixes:
	@mkdir -p "$(OUT_DIR)/llm_fixes"
	$(PY) $(SCRIPT) $(FLAGS) $(URL_FLAGS) --llm-fixes-dir "$(OUT_DIR)/llm_fixes"
	@echo "---- Revised URLs (if any) in results_flat.csv column Revised_URL ----"

clean:
	rm -rf "$(OUT_DIR)"
	@echo "Removed $(OUT_DIR)"
