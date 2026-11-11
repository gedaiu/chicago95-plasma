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
XML_FILES := $(shell git ls-files '*.xml')
DESKTOP_FILES := $(wildcard config/applications/*.desktop)
PRETTIER_GLOB := "**/*.{js,json,jsonc,yml,yaml,css,md}"

# usable PROBE COMMAND: run COMMAND unless PROBE fails (tool missing); then skip, or fail under STRICT=1
define usable
@if $(1) >/dev/null 2>&1; then $(2); \
elif [ "$(STRICT)" = 1 ]; then echo "missing tool: $(1)"; exit 1; \
else echo "skipped (not installed): $(1)"; fi
endef

.PHONY: check format lint lint-python lint-shell lint-qml lint-xml lint-desktop format-check format-python format-shell format-qml format-prettier

check: format-check lint

format: format-python format-shell format-qml format-prettier

lint: lint-python lint-shell lint-qml lint-xml lint-desktop

format-python:
	ruff check --select I --fix --quiet .
	ruff format .

format-shell:
	$(call usable,shfmt --version,shfmt -w $(SHELL_FILES))

format-qml:
	$(call usable,$(QMLFORMAT) --version,$(QMLFORMAT) -i $(QML_FILES))

format-prettier:
	$(PRETTIER) --write $(PRETTIER_GLOB)

format-check:
	ruff format --check .
	$(call usable,shfmt --version,shfmt -d $(SHELL_FILES))
	$(call usable,$(QMLFORMAT) --version,for f in $(QML_FILES); do $(QMLFORMAT) "$$f" | diff -q - "$$f" >/dev/null || { echo "needs qmlformat: $$f"; exit 1; }; done)
	$(PRETTIER) --check $(PRETTIER_GLOB)

lint-python:
	ruff check .

lint-shell:
	$(call usable,shellcheck --version,shellcheck -S warning $(SHELL_FILES))

# qmllint warns about every Plasma import it cannot resolve; only its exit code (syntax errors) gates.
lint-qml:
	$(call usable,$(QMLLINT) --version,out=$$($(QMLLINT) $(QML_FILES) 2>&1) || { echo "$$out"; exit 1; })

lint-xml:
	xmllint --noout $(XML_FILES)

lint-desktop:
	desktop-file-validate $(DESKTOP_FILES)
