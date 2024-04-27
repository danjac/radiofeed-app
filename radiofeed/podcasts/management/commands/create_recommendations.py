import djclick as click

from radiofeed import tokenizer
from radiofeed.podcasts import recommender
from radiofeed.thread_pool import DatabaseSafeThreadPoolExecutor


@click.command(help="Runs recommendation algorithms")
def command() -> None:
    """Implementation of command."""
    with DatabaseSafeThreadPoolExecutor() as executor:
        executor.db_safe_map(_recommend, tokenizer.NLTK_LANGUAGES)


def _recommend(language: str) -> None:
    click.echo(f"Creating recommendations for language: {language}...")
    recommender.recommend(language)
    click.echo(
        click.style(
            f"Recommendations created for language: {language}",
            bold=True,
            fg="green",
        )
    )
