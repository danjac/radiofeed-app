.PHONY: install
install:
	@$(MAKE) pyinstall
	@$(MAKE) npminstall
	@$(MAKE) precommitinstall
	@$(MAKE) nltkdownload

.PHONY: update
update:
	@$(MAKE) pyupdate
	@$(MAKE) npmupdate
	@$(MAKE) precommitupdate

.PHONY: pyinstall
pyinstall:
	uv venv && source .venv/bin/activate
	uv pip install -r requirements-ci.txt

.PHONY: pyupdate
pyupdate:
	uv pip compile pyproject.toml --no-annotate --no-header --upgrade -o requirements.txt
	uv pip compile pyproject.toml --no-annotate --no-header --upgrade --extra dev -o requirements-ci.txt
	uv pip sync requirements-ci.txt

.PHONY: npminstall
npminstall:
	npm ci

.PHONY: npmupdate
npmupdate:
	npm run check-updates && npm install npm-update-all

.PHONY: precommitinstall
precommitinstall:
	pre-commit install && pre-commit install --hook-type commit-msg

.PHONY: precommitupdate
precommitupdate:
	pre-commit autoupdate

.PHONY: nltkdownload
nltkdownload:
	xargs -I{} .venv/bin/python -c "import nltk; nltk.download('{}')" < nltk.txt

.PHONY: clean
clean:
	git clean -Xdf
	poetry env remove --all
