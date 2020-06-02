
# Feverbase
An open platform to accelerate any and all research related to clinical trials (including but not limited to the efficacy of repurposed drugs) for fighting COVID-19.
## Want to Help?
If you want to build and run Feverbase locally you need to install a few dependencies.
1. Install [Meilisearch](https://github.com/meilisearch/MeiliSearch). We use this to index our search results. You must add a `master-key` to this instance.
2. Either start a local version of [MongoDB](https://github.com/mongodb/mongo) or start a [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) instance.
3. Create a `.env` file at the top-level directory:
   ```
   MONGODB_URI=mongodb+srv://<account>:<password>@<mongo_url>/test?retryWrites=true&w=majority
   MEILI_KEY=xxxxxxxxx
   MEILI_URL=http://xxx.xxx.xxx.xxx:7700
   ```
4. Run the Flask app with `python serve.py`. The `--port` option can be used to specify a port.
5. To begin scraping of clinical trials run `python fetch.py`.
6. Feel free to [tackle an open issue](https://github.com/feverbase/feverbase/issues) or [open your own!](https://github.com/feverbase/feverbase/issues/new/choose). If you issue a Pull Request we will review it and hopefully merge it in.