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
    @just typecheck
    @just templatecheck
    @just test
    @just precommitall

serve:
    ./manage.py tailwind runserver_plus

clean:
    git clean -Xdf

test *args:
    pytest {{ args }}

typecheck:
    pyright

templatecheck:
    ./manage.py validate_templates

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

precommitall:
    pre-commit run -a

nltkdownload:
    uv run xargs -I{} python -c "import nltk; nltk.download('{}')" < ./nltk.txt
