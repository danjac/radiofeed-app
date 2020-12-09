
![](/screenshots/screenshot-1.png)

This is a very simple MVP podcast app. It has the following features:

1. Sync podcasts with their RSS feeds
2. Discover podcasts through iTunes categories
3. Search individual podcasts and episodes
4. Play episodes using an embedded HTML5 audio player
5. Bookmark episodes (logged in users)
6. Subscribe to individual podcast feeds (logged in users)

Some ideas for additional features you might want to add in a fork:

1. An episode queue that automatically plays the next episode in the queue when one is finished
2. Store the play history in the database for logged in users
3. Recommend new podcasts using machine learning based on subscriptions and play history
4. Allow users to compile and share their own lists or collections of podcasts
5. Automatically add new podcasts using the GPodder or iTunes API

For local development, first copy the .env.example file:

> cp .env.example .env

To get started, first import the categories:

> ./scripts/manage loaddata radiofeed/podcasts/fixtures/categories.json

You can then import a sample list of podcasts:

> ./scripts/manage loaddata radiofeed/podcasts/fixtures/podcasts.json

Alternatively, use the Django admin to add podcasts.

To sync podcasts and download episodes to the database:

> ./scripts/manage sync_podcast_feeds

In production this command could be run a few times a day in a cron, or adapted as a celery task to use with celerybeat.


