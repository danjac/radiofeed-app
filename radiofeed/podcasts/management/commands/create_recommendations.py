import djclick as click

from radiofeed import tokenizer
from radiofeed.podcasts import recommender
from radiofeed.thread_pool import execute_thread_pool


@click.command()
def command():
    """Generate recommendations based on podcast similarity."""
    execute_thread_pool(recommender.recommend, tokenizer.NLTK_LANGUAGES)
