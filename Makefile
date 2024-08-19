install: pyinstall npminstall precommitinstall nltkdownload
update: pyupdate npmupdate precommitupdate

pyinstall:
	uv venv && source .venv/bin/activate
	uv pip install -r requirements-ci.txt

pyupdate:
	uv pip compile pyproject.toml --upgrade -o requirements.txt
	uv pip compile pyproject.toml --upgrade --extra dev -o requirements-ci.txt
	uv pip sync requirements-ci.txt

npminstall:
	npm ci

npmupdate:
	npm run check-updates && npm install npm-update-all

precommitinstall:
	pre-commit install && pre-commit install --hook-type commit-msg

precommitupdate:
	pre-commit autoupdate

nltkdownload:
	xargs -I{} poetry run python -c "import nltk; nltk.download('{}')" < nltk.txt

clean:
	git clean -Xdf
	poetry env remove --all
