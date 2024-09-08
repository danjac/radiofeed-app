.PHONY: install
install:
	@$(MAKE) envfile
	@$(MAKE) pyinstall
	@$(MAKE) npminstall
	@$(MAKE) precommitinstall
	@$(MAKE) nltkdownload

.PHONY: update
update:
	@$(MAKE) pyupdate
	@$(MAKE) npmupdate
	@$(MAKE) precommitupdate

.PHONY: envfile
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
	npm update

.PHONY: tailwind
tailwind:
	npx tailwindcss -i ./assets/app.css -o ./assets/dist/app.css --verbose --watch

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
