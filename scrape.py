import datetime
import locale
import sys
import urllib.request

from bs4 import BeautifulSoup

from hip_hop_quote_parser import HipHopQuoteParser

BLOG_BASE_URL = 'http://www.bhorowitz.com/'
# BLOG_BASE_URL = 'http://www.bhorowitz.com/?page=2'


def parse_blog_page(page_html):
    # Set locale to US for date parsing, the en_IN locale must be available in the system
    locale.setlocale(locale.LC_TIME, "en_IN")

    soup = BeautifulSoup(page_html, 'html.parser')
    post_excerpt_divs = soup.find_all('div', class_='page-excerpt')
    post_id = 0
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

        quote_parser = HipHopQuoteParser()
        parsed_quotes = quote_parser.parse(post_name, post_excerpt_div)
        quotes.extend([(post_id, quote, author, song_title) for quote, author, song_title in parsed_quotes])
    return posts, quotes


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
    new_posts, new_quotes = parse_blog_page(main_page_html)
    posts.extend(new_posts)
    quotes.extend(new_quotes)

    # Download and parse the rest of the pages
    for page_link in page_links:
        response = urllib.request.urlopen(page_link)
        page_html = response.read()
        new_posts, new_quotes = parse_blog_page(page_html)
        posts.extend(new_posts)
        quotes.extend(new_quotes)
    return posts, quotes


if __name__ == "__main__":
    posts, quotes = scrape_posts()
    last_post_name = None
    last_post_quote_count = 0
    for quote in quotes:
        post_id, quote, author, song_title = quote
        post_id, post_date, post_url, post_name = posts[post_id - 1]

        if post_name != last_post_name and last_post_name:
            print('%s:\t%s' % (last_post_quote_count, last_post_name))
            last_post_quote_count = 0
            last_post_name = post_name
        last_post_quote_count += 1

    for quote in quotes:
        post_id, quote, author, song_title = quote
        post_id, post_date, post_url, post_name = posts[post_id - 1]
        print('%s (%s):\n\t/%s/%s/%s/' % (post_name, post_url, author, song_title, quote.replace('\n', ' ')))

    print('\nTotal posts: %s, total quotes:%s' % (len(posts), len(quotes)))
