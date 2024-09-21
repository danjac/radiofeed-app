.PHONY: install
install:
	@$(MAKE) envfile
	@$(MAKE) pyinstall
	@$(MAKE) precommitinstall
	@$(MAKE) nltkdownload

.PHONY: update
update:
	@$(MAKE) pyupdate
	@$(MAKE) precommitupdate

.PHONY: envfile
envfile:
	cp -R -u -p .env.example .env

.PHONY: pyinstall
pyinstall:
	uv sync --frozen --all-extras

.PHONY: pyupdate
pyupdate:
	uv sync --all-extras

.PHONY: precommitinstall
precommitinstall:
	pre-commit install && pre-commit install --hook-type commit-msg

.PHONY: precommitupdate
precommitupdate:
	pre-commit autoupdate

.PHONY: nltkdownload
nltkdownload:
	uv run xargs -I{} python -c "import nltk; nltk.download('{}')" < ./nltk.txt

.PHONY: clean
clean:
	git clean -Xdf
