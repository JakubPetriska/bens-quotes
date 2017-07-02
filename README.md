# Ben's Quotes

Scraper that gathers all quotes from articles on [a16z.com](http://a16z.com/) written by Ben Horowitz. Web frontend presenting the data can be found [here](https://jakubpetriska.github.io/bens-quotes/).

The output is saved into two csv files that can be found in the same directory as the project directory is located. The files are _bensquotes-posts.csv_ and _bensquotes-quotes.csv_ containing all posts and all quotes respectively.

To scrape the quotes launch the _scrape_quotes.py_ script. To read the scraped data use the `read_bens_quotes_file` function from file _utils.py_. The function returns list, each element of which is also list containing quote or post depending on which file is being read. The format of posts and quotes is specified below.

## Posts format
The posts file lines and the data that are read from it have following format:`post_id, post_date, post_url, post_name`.

## Quotes format
The quotes file lines and the data that are read from it have following format:`quote_post_id, quote, author, song_title`. The `quote_post_id` is a reference into the `post_id` in posts file.
