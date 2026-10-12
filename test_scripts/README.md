# Dashboard Tests

Python refresh/cache tests:

```sh
python3 -m unittest test_scripts.test_research_refresh -v
```

Install and run the Playwright dashboard tests from this folder:

```sh
npm install
npx playwright install chromium
npm test
```

The browser tests reserve one free localhost port, start the dashboard there with the initial network scrape skipped, and share that port with all Playwright workers. They exercise `/api/health`, refresh/cache counts, the live status panel, and conditional `Last-Modified` caching for the dashboard and an ingested source. The normal server performs an immediate web scrape at startup and then refreshes every three hours.
