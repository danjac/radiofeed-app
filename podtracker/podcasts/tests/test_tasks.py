from podtracker.podcasts.tasks import crawl_itunes, recommend


def test_recommend(mocker):
    patched = mocker.patch("podtracker.podcasts.tasks.recommender.recommend")
    recommend()
    patched.assert_called()


def test_crawl_itunes(mocker):
    patched = mocker.patch("podtracker.podcasts.tasks.itunes.crawl")
    crawl_itunes()
    patched.assert_called()
