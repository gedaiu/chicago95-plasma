# Lint and format every kind of source file in the repo.
#   make check    verify formatting and lint, change nothing (what CI runs)
#   make format   rewrite files into the house style
#   make lint     lint only
# A tool that is not installed is skipped with a notice; with STRICT=1 (CI) it is an error.

PRETTIER ?= npx --yes prettier@3.3.3
QMLFORMAT ?= pyside6-qmlformat
QMLLINT ?= pyside6-qmllint
STRICT ?= 0

SHELL_FILES := install.sh uninstall.sh $(wildcard setup/*.sh)
QML_FILES := $(shell git ls-files '*.qml')
# lockscreen/ and data/qml/ are KDE's own Breeze and Milou code with local patches: formatted, not linted.
QML_LINT_FILES := $(filter-out lockscreen/% data/qml/%,$(QML_FILES))
PLASMA_QML_DIR := $(firstword $(wildcard /usr/lib64/qt6/qml /usr/lib/qt6/qml /usr/lib/x86_64-linux-gnu/qt6/qml))
# With the Plasma modules installed qmllint resolves every import, so any message at all fails the check.
# Without them (CI) it can only vouch for syntax: unresolved Plasma types would flood it with false warnings.
QMLLINT_FLAGS := $(if $(wildcard $(PLASMA_QML_DIR)/org/kde/plasma/core),-I $(PLASMA_QML_DIR) -I data/qml)
# QML JavaScript libraries start with ".pragma library", which prettier cannot parse on its own.
PRAGMA_JS_FILES := $(shell git ls-files '*.js' | xargs grep -l '^\.pragma' 2>/dev/null)
XML_FILES := $(shell git ls-files '*.xml')
DESKTOP_FILES := $(wildcard config/applications/*.desktop config/autostart/*.desktop splash/*/metadata.desktop)
PRETTIER_GLOB := "**/*.{js,json,jsonc,yml,yaml,css,md}"

# usable PROBE COMMAND: run COMMAND unless PROBE fails (tool missing); then skip, or fail under STRICT=1
define usable
@if $(1) >/dev/null 2>&1; then $(2); \
elif [ "$(STRICT)" = 1 ]; then echo "missing tool: $(1)"; exit 1; \
else echo "skipped (not installed): $(1)"; fi
endef

.PHONY: check coverage format lint lint-python lint-shell lint-qml lint-xml lint-desktop format-check format-python format-shell format-qml format-js format-prettier lint-js

check: format-check lint

# Branch coverage of the programs, including the ones the tests start as subprocesses.
coverage:
	QT_QPA_PLATFORM=offscreen python3 -m pytest tests -q --cov --cov-report=term-missing:skip-covered

format: format-python format-shell format-qml format-js format-prettier

lint: lint-python lint-shell lint-qml lint-js lint-xml lint-desktop

format-python:
	ruff check --select I --fix --quiet .
	ruff format .

format-shell:
	$(call usable,shfmt --version,shfmt -w $(SHELL_FILES))

format-qml:
	$(call usable,$(QMLFORMAT) --version,$(QMLFORMAT) -i $(QML_FILES))

# eslint adds the blank lines prettier never inserts, then prettier lays out the rest
format-js: node_modules
	npx eslint --fix .

format-prettier: format-js
	$(PRETTIER) --write $(PRETTIER_GLOB)
	python3 tests/tools_prettier_pragma.py write "$(PRETTIER)" $(PRAGMA_JS_FILES)

format-check: node_modules
	ruff format --check .
	$(call usable,shfmt --version,shfmt -d $(SHELL_FILES))
	$(call usable,$(QMLFORMAT) --version,for f in $(QML_FILES); do $(QMLFORMAT) "$$f" | diff -q - "$$f" >/dev/null || { echo "needs qmlformat: $$f"; exit 1; }; done)
	$(PRETTIER) --check $(PRETTIER_GLOB)
	python3 tests/tools_prettier_pragma.py check "$(PRETTIER)" $(PRAGMA_JS_FILES)

lint-python:
	ruff check .

lint-shell:
	$(call usable,shellcheck --version,shellcheck -x $(SHELL_FILES))

lint-qml:
	$(call usable,$(QMLLINT) --version,out=$$($(QMLLINT) $(QMLLINT_FLAGS) $(QML_LINT_FILES) 2>&1) || { echo "$$out"; exit 1; }; [ -z "$(QMLLINT_FLAGS)" ] || [ -z "$$out" ] || { echo "$$out"; exit 1; })

lint-js: node_modules
	npx eslint .

node_modules: package-lock.json
	npm ci
	touch node_modules

lint-xml:
	xmllint --noout $(XML_FILES)

lint-desktop:
	desktop-file-validate $(DESKTOP_FILES)
