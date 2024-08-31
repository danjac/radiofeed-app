.PHONY: install
install:
	@$(MAKE) copyenv
	@$(MAKE) pyinstall
	@$(MAKE) npminstall
	@$(MAKE) precommitinstall
	@$(MAKE) nltkdownload

.PHONY: update
update:
	@$(MAKE) pyupdate
	@$(MAKE) npmupdate
	@$(MAKE) precommitupdate

.PHONY: copyenv
copyenv:
	cp -R -u -p .env.example .env

.PHONY: pyinstall
pyinstall:
	pdm install --no-self

.PHONY: pyupdate
pyupdate:
	pdm update

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
	pdm run xargs -I{} python -c "import nltk; nltk.download('{}')" < nltk.txt

.PHONY: clean
clean:
	git clean -Xdf
