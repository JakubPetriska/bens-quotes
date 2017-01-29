import csv
import os
import urllib.request
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from post_parser import PostParser

POSTS_OUTPUT_FILE = os.path.join(os.pardir, 'bensquotes-posts.csv')
QUOTES_OUTPUT_FILE = os.path.join(os.pardir, 'bensquotes-quotes.csv')

BLOG_BASE_URL = 'https://a16z.com'
BLOG_POSTS_PAGE = BLOG_BASE_URL + '/author/ben-horowitz/'

OUTPUT_FILE_DELIMITER = ';'

# Used to limit the number of pages the scraper downloads
# Set to -1 to remove the limit
MAX_DOWNLOADED_PAGES = -1


def scrape_posts():
    # We'll progress from the Ben Horowitz's page which contains his latest posts and Load more button.
    # The Load more button calls ajax request which gives <div> containing more posts and also new Load more button.
    # We'll call Load more button's URL in loop starting with Ben Horowitz's page URL while
    # the Load more button will be present in server's answer.
    posts = []
    post_id = 0
    url = BLOG_POSTS_PAGE
    downloaded_pages_count = 0
    while MAX_DOWNLOADED_PAGES == -1 or downloaded_pages_count < MAX_DOWNLOADED_PAGES:
        print('Loading URL: %s' % url)
        response = urllib.request.urlopen(url)
        downloaded_pages_count += 1
        html = response.read()
        soup = BeautifulSoup(html, 'html.parser')
        articles = soup.find_all('article')
        for article in articles:
            article_header = article.h3
            post_name = article_header.get_text()
            if not post_name.startswith('a16z Podcast:'):
                # We don't care about podcasts
                post_url = article_header.parent['href']

                post_domain = urlparse(post_url).netloc
                if post_domain.startswith('www.'):
                    post_domain = post_domain[4:]

                # TODO allow parsing of posts on Medium.com
                if post_domain == 'a16z.com':
                    post_date = article.time['datetime']
                    post_id += 1
                    posts.append([post_id, post_date, post_url, post_name])
                else:
                    print('Post from unsupported domain %s skipped' % post_domain)
        load_more_button = soup.find(id='trigger-load-more')
        if load_more_button:
            url = BLOG_BASE_URL + load_more_button['data-ajax-path']
        else:
            break

    quotes = []
    for post in posts:
        post_id, post_date, post_url, post_name = post
        response = urllib.request.urlopen(post_url)
        html = response.read()
        soup = BeautifulSoup(html, 'html.parser')
        article_div = soup.article.find('div', class_='entry-content')

        quote_parser = PostParser()
        parsed_quotes = quote_parser.parse(post_name, article_div)
        quotes.extend([(post_id, quote, author, song_title) for quote, author, song_title in parsed_quotes])
    return posts, quotes


if __name__ == "__main__":
    posts, quotes = scrape_posts()

    quotes_index = 0
    for post in posts:
        post_id, post_date, post_url, post_name = post

        post_quotes_count = 0
        while quotes_index < len(quotes):
            quote_post_id, quote, author, song_title = quotes[quotes_index]
            if quote_post_id == post_id:
                post_quotes_count += 1
                quotes_index += 1
            else:
                break
        print('%s:\t%s' % (post_quotes_count, post_name))

    for quote in quotes:
        post_id, quote, author, song_title = quote
        post_id, post_date, post_url, post_name = posts[post_id - 1]
        print()
        print('%s (%s):\n\t/%s/%s/' % (post_name, post_url, author, song_title))
        print(quote)

    print('\nTotal posts: %s, total quotes: %s' % (len(posts), len(quotes)))

    with open(POSTS_OUTPUT_FILE, 'w', newline='') as quotes_file:
        quotes_writer = csv.writer(quotes_file, delimiter=OUTPUT_FILE_DELIMITER, quoting=csv.QUOTE_MINIMAL)
        for post in posts:
            quotes_writer.writerow(post)

    with open(QUOTES_OUTPUT_FILE, 'w', newline='') as quotes_file:
        quotes_writer = csv.writer(quotes_file, delimiter=OUTPUT_FILE_DELIMITER, quoting=csv.QUOTE_MINIMAL)
        for quote in quotes:
            quotes_writer.writerow(quote)
