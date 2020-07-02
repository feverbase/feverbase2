
# Feverbase
An open platform to accelerate any and all research related to clinical trials (including but not limited to the efficacy of repurposed drugs) for fighting COVID-19.
## Dependencies
Feverbase depends on:

- [MeiliSearch](https://github.com/meilisearch/MeiliSearch) to index search results 
- [MongoDB](https://github.com/mongodb/mongo) to persist data

However, Docker takes care of setting up all required services and connecting them together!

You may also optionally create a `.env` file with the following keys:
```
  SLACK_WEBHOOK_URL=  # for feedback form
  GOOGLE_MAPS_KEY=    # for fetching locations
  MEILI_KEY=          # for a protected MeiliSearch instance
```

## Running the App
Feverbase has two main components: `serve.py` which serves the Flask app which contains the actual interface to search and filter clinical trials. This can be run with `python serve.py` with the optional argument of `--port <port>` to manually specify a port.

The second component is the web scraper. By default this will scrape trials from every clinicial trial registry we have added support for. This behavior can be changed in `fetch/__init__.py`, specifically with the `DRIPPING_FAUCETS` array. The scraper can be run with `python fetch.py`. This may take a while to run if you're scraping every search query from every registry. We run this as a cron job every hour.

With Docker installed, you can run everything in one line:
```
docker-compose up
```

If you want to fetch results, run the above command in one terminal session.
From another terminal session in the same folder, run the following:
```
docker-compose exec app python fetch.py
```

## Running tests
With docker running in one terminal session:
```
docker-compose up
```

Execute the following from another terminal session in the same folder:
```
docker-compose exec app pytest
```

This will execute the tests in the container which is already running!

## Contributing
Feverbase is open-sourced! Feel free to tackle open issues or create your own.
## License
Feverbase is MIT-licensed. Use it however you see fit.