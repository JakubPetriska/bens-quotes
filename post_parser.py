import re
from enum import Enum

import html2text
from bs4 import Comment
from bs4 import Tag

NEWLINE_TAGS = ['br', 'p', 'div']
QUOTATION_MARKS = '\'"’“”'
AUTHOR_PREFIXES = ['—', '–', '-', '-- ', '\\\\-- ']

MARKDOWN_ITALICS_REGEX = '^_.*_$'


def _convert_html2text(html_tag):
    h = html2text.HTML2Text()
    h.ignore_links = True
    return h.handle(str(html_tag))


# Matches the start of author line
# Works for text directly obtained from Tags and for text from html2text.
AUTHOR_LINE_START_REGEX = '^\s*>?\s*(%s)' % '|'.join(AUTHOR_PREFIXES)


def _is_unwanted_content(e):
    """Decides whether given element is part of the quote or not."""
    if isinstance(e, Comment):
        return False
    elif isinstance(e, Tag) \
            and (re.match('^h[1-9]', e.name)
                 or ('class' in e.attrs and 'byline' in e['class'])
                 or ('class' in e.attrs and 'sharetable' in e['class'])):
        # Unwanted tag known to not be a part of the quote
        return False
    elif isinstance(e, Tag) and not e.get_text().strip():
        # Tag with empty content
        return False
    else:
        return e.strip() if isinstance(e, str) else e


def _filter_content(l):
    """Filters content of a tag.
        Removes strings containing only whitespace, tags containing only whitespace, comments and all false items.
    """
    return list(filter(lambda e: _is_unwanted_content(e), l))


def _starts_with_quote(string):
    return re.match('^[%s]{1}.*' % QUOTATION_MARKS, string)


def _strip_quotes_beginning(string):
    while _starts_with_quote(string):
        string = string[1:]
    return string


def _ends_with_quote(string):
    return re.match('.*[%s]{1}$' % QUOTATION_MARKS, string)


def _strip_quotes_end(string):
    while _ends_with_quote(string):
        string = string[:-1]
    return string


def _strip_quotes(string):
    return _strip_quotes_beginning(_strip_quotes_end(string))


def _strip_markdown_italics(string):
    if re.match(MARKDOWN_ITALICS_REGEX, string):
        return string[1:-1]
    else:
        return string


class PostParser:
    """Parser that accepts beautifulsoup Tag object and collects all quotes from it."""
    class State(Enum):
        INITIAL = 1

        FILTER_DATA = 10

        # Following states gather blocks from the input data that contain the quotes, e.g. their last line
        # starts with the dash or similar character which indicates quote end.
        # The obtained blocks are stored in the quote_blocks variable.
        # Quote block means list of tags that contain the quote.
        GATHER_QUOTE_BLOCKS = 20

        PROCESS_AND_STRIP_QUOTE_BLOCKS = 30

        # This state turns quote block into parsed quote. Tuple in format (quote, author, song_title).
        PARSE_QUOTE = 50

        FINAL = 100

    def __init__(self):
        self.state = PostParser.State.INITIAL
        self.post_name = None
        self.data = None
        self.quote_blocks = []
        self.parsed_quotes = []

    def _set_state(self, state):
        self.state = state

    def _in_state(self, state):
        return self.state == state

    def _print_error(self, reason, print_data=False):
        print('Error - "%s" while parsing post "%s"' % (reason, self.post_name))
        if print_data:
            print('\tState: %s, data: %s' % (self.state, self.data))
        else:
            print('\tState: %s' % self.state)

    def parse(self, post_name, post_tag):
        """Parse beautifulsoup Tag and collect all it's quotes.

        :param post_name: Name of the post for identification in logs.
        :param post_tag: beautifulsoup Tag containg the excerpt of the post.
        :return: The parsed quotes.
        """
        self.state = PostParser.State.INITIAL

        self.post_name = post_name
        self.data = [post_tag]
        self.quote_blocks = []
        self.parsed_quotes = []

        while True:
            if self._in_state(PostParser.State.INITIAL):
                self._set_state(PostParser.State.GATHER_QUOTE_BLOCKS)

            if self._in_state(PostParser.State.FILTER_DATA):
                self.data = _filter_content(self.data)
                self._set_state(PostParser.State.GATHER_QUOTE_BLOCKS)

            if self._in_state(PostParser.State.GATHER_QUOTE_BLOCKS):
                new_data = []
                last_author_item_index = 0
                for i in range(len(self.data)):
                    item = self.data[i]
                    text = item if isinstance(item, str) else _convert_html2text(item)
                    # Split the block text by new lines
                    text_lines = text.split('\n')
                    # Remove empty lines and lines containing only whitespace
                    text_lines = list(filter(lambda text_line: text_line.strip(), text_lines))
                    for line_index in range(len(text_lines)):
                        text_line = text_lines[line_index]
                        if re.match(AUTHOR_LINE_START_REGEX, text_line):
                            # Line contains quote author
                            if line_index == (len(text_lines) - 1):
                                # The line is last in this item, so the block is complete quote
                                if len(text_lines) == 1:
                                    # However this block is only author
                                    self.quote_blocks.append(self.data[last_author_item_index:i + 1])
                                else:
                                    # This block contains the author as well as the quote
                                    self.quote_blocks.append([self.data[i]])
                                last_author_item_index = i
                            else:
                                # The line is in the middle of the block so let's unpack it and try again
                                new_data.extend(_filter_content(item.contents))
                                break
                self.data = new_data
                if self.data:
                    self._set_state(PostParser.State.FILTER_DATA)
                else:
                    self._set_state(PostParser.State.PROCESS_AND_STRIP_QUOTE_BLOCKS)

            elif self._in_state(PostParser.State.PROCESS_AND_STRIP_QUOTE_BLOCKS):
                for i in range(len(self.quote_blocks)):
                    quote_block = _filter_content(self.quote_blocks[i])
                    while len(quote_block) == 1:
                        quote_block = _filter_content(quote_block[0])
                    self.quote_blocks[i] = quote_block
                self._set_state(PostParser.State.PARSE_QUOTE)

            elif self._in_state(PostParser.State.PARSE_QUOTE):
                if len(self.quote_blocks) > 0:
                    quote_block = self.quote_blocks[0]
                    self.quote_blocks = self.quote_blocks[1:]
                    # Items are either strings or tags
                    # Split the whole block so that it's items represent individual lines of the quote
                    for i in reversed(range(len(quote_block))):
                        quote_block_item = quote_block[i]
                        if not isinstance(quote_block_item, str):
                            quote_block_item = _convert_html2text(str(quote_block_item))
                        quote_block_item_splits = quote_block_item.split('\n')
                        quote_block_item_splits = list(filter(lambda split: split.strip(), quote_block_item_splits))
                        quote_block = quote_block[:i] + quote_block_item_splits + quote_block[i + 1:]

                    # In case the quote is wrapped in <blockquote> we need to strip the quote signs from line beginnings
                    for i in reversed(range(len(quote_block))):
                        line = quote_block[i]
                        m = re.match('^\s*>\s*', line)
                        if m:
                            quote_block[i] = line[m.span()[1]:]

                    # Strip all lines of whitespace and remove the empty ones
                    quote_block = list(map(lambda string: string.strip(), quote_block))
                    quote_block = list(filter(lambda split: split, quote_block))

                    quote_lines = quote_block[:len(quote_block) + - 1]
                    # If the last line ends with quotation mark and there is a line that begins with quotation mark
                    # and this line is not the first then we have more than our quote.
                    # So strip everything that is not the quote.
                    if _ends_with_quote(quote_lines[-1]):
                        for i in range(len(quote_lines) - 1):
                            if _starts_with_quote(quote_lines[i]):
                                quote_lines = quote_lines[i:]
                                break
                    quote_lines[0] = _strip_quotes_beginning(quote_lines[0])
                    quote_lines[-1] = _strip_quotes_end(quote_lines[-1])

                    # Strip whitespace again from all lines
                    quote_block = list(map(lambda line: line.strip(), quote_block))

                    quote = '\n'.join(quote_lines)
                    last_line = quote_block[-1]
                    # Cut the dash or any author preceding characters from the last line
                    author_start_match = re.match(AUTHOR_LINE_START_REGEX, last_line)
                    if not author_start_match:
                        self._print_error('Last line does not start with usual author prefix.')
                    else:
                        author_start_index = author_start_match.span()[1]
                        last_line = last_line[author_start_index:]
                        author_title_split = re.search(', ', last_line)
                        if not author_title_split:
                            # Quote has only author, no song title
                            author = last_line
                            song_title = None
                        else:
                            author_title_split_span = author_title_split.span()
                            author = last_line[:author_title_split_span[0]]
                            song_title = _strip_markdown_italics(_strip_quotes(last_line[author_title_split_span[1]:]))
                        self.parsed_quotes.append((quote, author, song_title))
                    self._set_state(PostParser.State.PARSE_QUOTE)
                else:
                    self._set_state(PostParser.State.FINAL)

            elif self._in_state(PostParser.State.FINAL):
                return self.parsed_quotes
