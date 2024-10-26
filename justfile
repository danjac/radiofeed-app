install: envfile pyinstall precommmitinstall nltkdownload

update: pyupdate pyinstall precommitupdate

serve:
    ./manage.py tailwind runserver_plus

test *args:
    pyright
    pytest {{ args }}

clean:
    git clean -Xdf

envfile:
	cp -R -u -p .env.example .env

pyinstall:
    uv sync --frozen --all-extras --no-install-project

pyupdate:
    uv lock --upgrade

precommmitinstall:
    pre-commit install && pre-commit install --hook-type commit-msg

precommitupdate:
	pre-commit autoupdate

nltkdownload:
    uv run xargs -I{} python -c "import nltk; nltk.download('{}')" < ./nltk.txt
