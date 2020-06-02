
# Feverbase
An open platform to accelerate any and all research related to clinical trials (including but not limited to the efficacy of repurposed drugs) for fighting COVID-19.
## Dependencies
Feverbase requires an instance of [Meilisearch](https://github.com/meilisearch/MeiliSearch) to index search results and an instance of [MongoDB](https://github.com/mongodb/mongo) to persist data. We recommend using [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) for easy setup.

A `.env` file must be created at the top-level directory:
   ```
   MONGODB_URI=mongodb+srv://<account>:<password>@<mongo_url>/test?retryWrites=true&w=majority
   MEILI_KEY=xxxxxxxxx
   MEILI_URL=http://xxx.xxx.xxx.xxx:7700
   ```
## Running the App
Feverbase has two main components: `serve.py` which serves the Flask app which contains the actual interface to search and filter clinical trials. This can be run with `python serve.py` with the optional argument of `--port <port>` to manually specify a port.

The second component is the web scraper. By default this will scrape trials from every clinicial trial registry we have added support for. This behavior can be changed in `fetch/__init__.py`, specifically with the `DRIPPING_FAUCETS` array. The scraper can be run with `python fetch.py`. This may take a while to run if you're scraping every search query from every registry. We run this as a cron job every hour.
## Contributing
Feverbase is open-sourced! Feel free to tackle open issues or create your own.
## License
Feverbase is MIT-licensed. Use it however you see fit.