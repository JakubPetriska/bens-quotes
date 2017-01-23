# Ben's Quotes

Web scraper that obtains all quotes cited on the [blog of Ben Horowitz](http://www.bhorowitz.com/).

The output is saved into two csv files that can be found in the same directory as the project directory is located. The files are _bens_quotes-posts.csv_ and _bens_quotes-quotes.csv_ containing all posts on the blog and all quotes respectively.

To scrape the quotes launch the _scrape_posts.py_ script. To read the scraped data use the `read_bens_quotes_file` function from file _utils.py_. The function returns list, each element of which is also list containing quote or post depending on which file is being read. The format of posts and quotes is specified below. 

## Posts format
The posts file lines and the data that are read from it have following format:`post_id, post_date, post_url, post_name`.

## Quotes format
The quotes file lines and the data that are read from it have following format:`quote_post_id, quote, author, song_title`. The `quote_post_id` is a reference into the `post_id` in posts file.
