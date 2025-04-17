import djclick as click

from radiofeed import tokenizer
from radiofeed.podcasts import recommender


@click.command()
def command():
    """Generate recommendations based on podcast similarity."""
    for language in tokenizer.NLTK_LANGUAGES:
        click.echo(f"Generating recommendations for {language}")
        recommender.recommend(language)
