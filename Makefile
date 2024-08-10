install: pyinstall npminstall precommitinstall nltkdownload
update: pyupdate npmupdate precommitupdate

pyinstall:
	poetry install

pyupdate:
	poetry update

npminstall:
	npm ci

npmupdate:
	npm run check-updates && npm install npm-update-all

precommitinstall:
	pre-commit install && pre-commit install --hook-type commit-msg

precommitupdate:
	pre-commit autoupdate

nltkdownload:
	xargs -I{} .venv/bin/python -c "import nltk; nltk.download('{}')" < nltk.txt

clean:
	git clean -Xdf
