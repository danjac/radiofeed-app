@_default:
    just --list

@install:
    @just envfile
    @just pyinstall
    @just precommmitinstall
    @just nltkdownload

@update:
    @just pyupdate
    @just pyinstall
    @just precommitupdate

@check:
    @just typecheck
    @just templatecheck
    @just test
    @just precommitall

@start:
    @just dockerup
    @just serve

@stop:
    @just dockerdown

@serve:
    @just dj tailwind runserver_plus

@shell:
    @just dj shell_plus

@clean:
    git clean -Xdf

@test *ARGS:
    uv run pytest {{ ARGS }}

@dockerup *ARGS:
    docker compose up -d {{ ARGS }}

@dockerdown *ARGS:
    docker compose down {{ ARGS }}

@dj *ARGS:
    uv run python ./manage.py {{ ARGS }}

@typecheck *ARGS:
    uv run pyright {{ ARGS }}

@templatecheck:
    ./manage.py validate_templates

@envfile:
	cp -R -u -p .env.example .env

@pyinstall:
    uv sync --frozen --all-extras --no-install-project

@pyupdate:
    uv lock --upgrade

@precommit *ARGS:
    uv run --with pre-commit-uv pre-commit {{ ARGS }}

@precommmitinstall:
    @just precommit install
    @just precommit install --hook-type commit-msg

@precommitupdate:
	@just precommit autoupdate

@precommitall:
    @just precommit run --all-files

@nltkdownload:
    uv run xargs -I{} python -c "import nltk; nltk.download('{}')" < ./nltk.txt
