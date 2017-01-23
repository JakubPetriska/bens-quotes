import csv
import datetime
import locale
import os
import urllib.request

from bs4 import BeautifulSoup

from quote_parser import QuoteParser

POSTS_OUTPUT_FILE = os.path.join(os.pardir, 'bensqutoes-posts.csv')
QUOTES_OUTPUT_FILE = os.path.join(os.pardir, 'bensqutoes-quotes.csv')

BLOG_BASE_URL = 'http://www.bhorowitz.com/'


def parse_blog_page(page_html, post_id_offset=0):
    # Set locale to US for date parsing, the en_IN locale must be available in the system
    locale.setlocale(locale.LC_TIME, "en_IN")

    soup = BeautifulSoup(page_html, 'html.parser')
    post_excerpt_divs = soup.find_all('div', class_='page-excerpt')
    post_id = post_id_offset
    posts = []
    quotes = []
    for post_excerpt_div in post_excerpt_divs:
        post_date_string = post_excerpt_div.div.string.strip()
        post_date = datetime.datetime.strptime(post_date_string, '%B %d, %Y')

        post_url_relative = post_excerpt_div.h3.a['href']
        post_url = BLOG_BASE_URL + post_url_relative[1:] if post_url_relative.startswith('/') else post_url_relative

        post_name = post_excerpt_div.h3.a.string

        post_id += 1
        posts.append((post_id, post_date, post_url, post_name))

        quote_parser = QuoteParser()
        parsed_quotes = quote_parser.parse(post_name, post_excerpt_div)
        quotes.extend([(post_id, quote, author, song_title) for quote, author, song_title in parsed_quotes])
    return posts, quotes, post_id


def scrape_posts():
    # Download the main page
    response = urllib.request.urlopen(BLOG_BASE_URL)
    main_page_html = response.read()

    # Figure out how many pages are there and gather their links
    soup = BeautifulSoup(main_page_html, 'html.parser')
    page_link_tags = soup.find('div', class_='pagination').find_all('li')
    # Remove all tags until the active page and the active page as well
    # We started at home (1st page) so all following are all that's needed
    # Also in case we want to start from some other page than 1st this allows us to only to that and all following pages
    for i in range(len(page_link_tags)):
        if 'class' in page_link_tags[i].attrs and page_link_tags[i]['class'][0] == 'active':
            page_link_tags = page_link_tags[i + 1:]
            break
    page_link_tags = list(filter(lambda tag: tag.a.string.isdigit(), page_link_tags))
    page_links = [page_link_tag.a['href'] for page_link_tag in page_link_tags]

    posts = []
    quotes = []

    # Parse the first page
    new_posts, new_quotes, next_post_id_offset = parse_blog_page(main_page_html)
    posts.extend(new_posts)
    quotes.extend(new_quotes)

    progress_message = 'Parsed page %s/%s'
    page_count = len(page_links) + 1
    print(progress_message % (1, page_count))

    # Download and parse the rest of the pages
    for i in range(len(page_links)):
        page_link = page_links[i]
        response = urllib.request.urlopen(page_link)
        page_html = response.read()
        new_posts, new_quotes, next_post_id_offset = parse_blog_page(page_html, next_post_id_offset)
        posts.extend(new_posts)
        quotes.extend(new_quotes)
        print(progress_message % (i + 2, page_count))
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
        quotes_writer = csv.writer(quotes_file, delimiter=';', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for post in posts:
            quotes_writer.writerow(post)

    with open(QUOTES_OUTPUT_FILE, 'w', newline='') as quotes_file:
        quotes_writer = csv.writer(quotes_file, delimiter=';', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for quote in quotes:
            quotes_writer.writerow(quote)
