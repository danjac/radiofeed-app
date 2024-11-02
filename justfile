@_default:
    @just --list

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
    @just dcup
    @just migrate
    @just serve

@stop:
    @just dcdn

@restart:
    @just dcrestart

@dj *ARGS:
    uv run python ./manage.py {{ ARGS }}

@serve:
    @just dj tailwind runserver_plus

@migrate:
    @just dj migrate

@shell:
    @just dj shell_plus

@templatecheck:
    @just dj validate_templates

@clean:
    git clean -Xdf

@test *ARGS:
    uv run pytest {{ ARGS }}

@typecheck *ARGS:
    uv run pyright {{ ARGS }}

@dcup *ARGS:
    docker compose up -d {{ ARGS }}

@dcdn *ARGS:
    docker compose down {{ ARGS }}

@dcrestart *ARGS:
    docker compose restart {{ ARGS }}

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

@dbclean:
    #!/usr/bin/env bash
    while true; do
        read -p "Do you wish to remove the database? [y/n] " yn
        case $yn in
            [Yy]* ) docker volume rm radiofeed-app_pg_data; break;;
            [Nn]* ) exit;;
            * ) echo "Please answer yes or no.";;
        esac
    done
