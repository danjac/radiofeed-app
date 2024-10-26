install:
    @just envfile
    @just pyinstall
    @just precommmitinstall
    @just nltkdownload

update:
    @just pyupdate
    @just pyinstall
    @just precommitupdate

check:
    @just test
    @just typecheck
    @just precommitall

serve:
    ./manage.py tailwind runserver_plus

clean:
    git clean -Xdf

test *args:
    pytest {{ args }}

precommitall:
    pre-commit run -a

typecheck:
    pyright

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
