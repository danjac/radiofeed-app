import djclick as click

from radiofeed import tokenizer
from radiofeed.podcasts import recommender
from radiofeed.thread_pool import DatabaseSafeThreadPoolExecutor


@click.command(help="Runs recommendation algorithms")
def command() -> None:
    """Implementation of command."""
    with DatabaseSafeThreadPoolExecutor() as executor:
        executor.db_safe_map(
            lambda language: recommender.recommend(language),
            tokenizer.NLTK_LANGUAGES,
        )
