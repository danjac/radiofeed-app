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
	pdm install --no-self

.PHONY: pyupdate
pyupdate:
	pdm update

.PHONY: precommitinstall
precommitinstall:
	pre-commit install && pre-commit install --hook-type commit-msg

.PHONY: precommitupdate
precommitupdate:
	pre-commit autoupdate

.PHONY: nltkdownload
nltkdownload:
	pdm run ./scripts/download-nltk.sh

.PHONY: clean
clean:
	git clean -Xdf
