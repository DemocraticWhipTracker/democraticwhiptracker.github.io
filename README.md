# Democratic Leadership Whip Tracker

Unofficial tracker of where every Democrat in the 120th Congress publicly stands in the Senate Democratic leader race (Schumer vs Van Hollen) and Hakeem Jeffries' bid for Speaker.

- `data/` holds the tracker data (members, activity feed, run status). An hourly scheduled task updates it.
- `build.py` turns the data into the static site: tracker, race pages, a page per member, FAQ, sitemap and structured data.
- `.github/workflows/pages.yml` rebuilds and deploys to GitHub Pages on every push to `main`.

Local build: `pip install pillow && python build.py --site-url http://localhost:8000` then serve `_site/`.

To use your own domain, set a repository variable `CNAME_DOMAIN` (Settings > Secrets and variables > Actions > Variables) and point the domain's DNS at GitHub Pages.
