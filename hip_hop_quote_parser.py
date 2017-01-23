import re
from enum import Enum

import html2text
from bs4 import Comment
from bs4 import Tag

NEWLINE_TAGS = ['br', 'p', 'div']
QUOTATION_MARKS = '\'"’“”'
AUTHOR_PREFIXES = ['—', '–', '-', '-- ']

MARKDOWN_ITALICS_REGEX = '^_.*_$'


def _convert_html2text(html_tag):
    h = html2text.HTML2Text()
    h.ignore_links = True
    return h.handle(str(html_tag))


# Matches the start of author line
# Works for text directly obtained from Tags and for text from html2text.
AUTHOR_LINE_START_REGEX = '^\s*>?\s*(%s)' % '|' \
    .join(AUTHOR_PREFIXES + [_convert_html2text(prefix).strip() for prefix in AUTHOR_PREFIXES])


def _is_unwanted_content(e):
    if isinstance(e, Comment):
        return False
    elif isinstance(e, Tag) and not e.get_text().strip():
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


class QuoteParser:
    class State(Enum):
        INITIAL = 1

        CLEANUP_DATA = 10

        # Following states gather blocks from the input data that contain the quotes, e.g. their last line
        # starts with the dash or similar character which indicates quote end.
        # The obtained blocks are stored in the quote_blocks variable.
        # Quote block means list of tags that contain the quote.
        GATHER_QUOTE_BLOCKS = 20

        CUT_NON_QUOTE_RELATED_DATA_FROM_QUOTE_BLOCKS = 30

        # This state turns quote block into parsed quote. Tuple in format (quote, author, song_title).
        PARSE_QUOTE = 50

        FINAL = 100

    def __init__(self):
        self.state = QuoteParser.State.INITIAL
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

    def parse(self, post_name, post_excerpt_div):
        self.state = QuoteParser.State.INITIAL

        self.post_name = post_name
        self.data = [post_excerpt_div]
        self.quote_blocks = []
        self.parsed_quotes = []

        while True:
            if self._in_state(QuoteParser.State.INITIAL):
                self._set_state(QuoteParser.State.GATHER_QUOTE_BLOCKS)

            if self._in_state(QuoteParser.State.CLEANUP_DATA):
                new_data = []
                for item in self.data:
                    if not (isinstance(item, Comment)
                            or (isinstance(item, Tag)
                                and (re.match('^h[1-9]', item.name)
                                     or ('class' in item.attrs and 'byline' in item['class'])
                                     or ('class' in item.attrs and 'sharetable' in item['class'])))):
                        new_data.append(item)
                self.data = new_data
                self._set_state(QuoteParser.State.GATHER_QUOTE_BLOCKS)

            if self._in_state(QuoteParser.State.GATHER_QUOTE_BLOCKS):
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
                self.data = new_data
                if self.data:
                    self._set_state(QuoteParser.State.CLEANUP_DATA)
                else:
                    self._set_state(QuoteParser.State.CUT_NON_QUOTE_RELATED_DATA_FROM_QUOTE_BLOCKS)

            elif self._in_state(QuoteParser.State.CUT_NON_QUOTE_RELATED_DATA_FROM_QUOTE_BLOCKS):
                # TODO
                self._set_state(QuoteParser.State.PARSE_QUOTE)

            elif self._in_state(QuoteParser.State.PARSE_QUOTE):
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
                    # Strip quotes at the beginning and end of the quote
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
                    self._set_state(QuoteParser.State.PARSE_QUOTE)
                else:
                    self._set_state(QuoteParser.State.FINAL)

            elif self._in_state(QuoteParser.State.FINAL):
                return self.parsed_quotes


                # if self._in_state(HipHopQuoteParser.State.INITIAL):
                #     # First we try to find if the post begins with blockquote at the beginning
                #     # If yeas the quote is in it
                #     block_quote = None
                #     contents = filter_out_empty_elements(self.data.contents)
                #     for i in reversed(range(len(contents))):
                #         if type(contents[i]) == Comment:
                #             del contents[i]
                #     for i in range(len(contents)):
                #         if type(contents[i]) == Tag and contents[i].name == 'blockquote' \
                #                 and ((i > 0 and type(contents[i - 1]) == Tag
                #                       and 'class' in contents[i - 1].attrs and 'sharetable' in contents[i - 1]['class'])
                #                      or (i > 1 and type(contents[i - 1]) == Tag
                #                       and 'class' in contents[i - 2].attrs and 'sharetable' in contents[i - 2]['class'])):
                #             # Either blockquote needs to be directly below share table or there is one tag
                #             # between it and share table
                #             block_quote = contents[i]
                #
                #     if post_name == 'Can Do vs. Can’t Do Cultures':
                #         s = ''
                #
                #     if block_quote:
                #         # Often the quote is wrapped in <blockquote> tag
                #         # If yes we'll just work with content of the blockquote
                #         self.data = filter_out_empty_elements(block_quote.contents)
                #         self._set_state(HipHopQuoteParser.State.UNPACK_QUOTE_LINES)
                #     else:
                #         self.data = filter_out_empty_elements(self.data.contents)
                #         self._set_state(HipHopQuoteParser.State.CUT_OUT_QUOTE_CONTENT)
                #
                # elif self._in_state(HipHopQuoteParser.State.CUT_OUT_QUOTE_CONTENT):
                #     # Remove all tags that obviously do not contain the quote (headers, etc..) and comments
                #     for i in reversed(range(len(self.data))):
                #         element = self.data[i]
                #         if not element \
                #                 or (type(element) == Tag
                #                     and (not element.get_text().strip()
                #                          or not (element.name == 'div' or element.name == 'p')
                #                          or ('class' in element.attrs
                #                              and ('byline' in element['class']
                #                                   or 'sharetable' in element['class']
                #                                   or 'button' in element['class'])))) \
                #                 or type(element) == Comment:
                #             del self.data[i]
                #     self._set_state(HipHopQuoteParser.State.UNPACK_QUOTE_LINES)
                #
                # elif self._in_state(HipHopQuoteParser.State.UNPACK_QUOTE_LINES):
                #     # If whole lines are wrapped in tags then unwrap them
                #     # Lines are unwrapped only if line is a tag or list containing one tag
                #     # Repeat this until anything gets unwrapped
                #     any_line_unpacked = False
                #     for i in reversed(range(len(self.data))):
                #         if type(self.data[i]) == Tag:
                #             self.data[i] = filter_out_empty_elements(self.data[i].contents)
                #             any_line_unpacked = True
                #         elif type(self.data[i]) == list and len(self.data[i]) == 1 and type(self.data[i][0]) == Tag:
                #             self.data[i] = filter_out_empty_elements(self.data[i][0].contents)
                #             any_line_unpacked = True
                #     self.data = filter_out_empty_elements(self.data)
                #     if any_line_unpacked:
                #         self.state = HipHopQuoteParser.State.UNPACK_QUOTE_LINES
                #     else:
                #         self.state = HipHopQuoteParser.State.UNPACK_QUOTE_LINES_SPLIT_BY_NEWLINE
                #
                # elif self._in_state(HipHopQuoteParser.State.UNPACK_QUOTE_LINES_SPLIT_BY_NEWLINE):
                #     # The data contain lines of the input
                #     # In case some of the lines contains tag that visually splits it into two lines, split the lines in data
                #     any_line_split = False
                #     for i in reversed(range(len(self.data))):
                #         line = self.data[i]
                #         new_line_positions = []
                #         for j in range(len(line)):
                #             if type(line[j]) == Tag and line[j].name in NEWLINE_TAGS:
                #                 new_line_positions.append(j)
                #         if len(new_line_positions) > 0:
                #             any_line_split = True
                #             new_line_positions.append(len(line))
                #             new_lines = []
                #             line_start = 0
                #             for new_line_position in new_line_positions:
                #                 if new_line_position - line_start > 0:
                #                     new_line = line[line_start:new_line_position]
                #                     if type(new_line) == list and type(new_line[0]) == Tag:
                #                         new_line = filter_out_empty_elements(new_line[0].contents) + new_line[1:]
                #                     if len(new_line) == 1:
                #                         new_line = new_line[0]
                #                     new_lines.append(new_line)
                #                     line_start = new_line_position
                #             self.data = self.data[:i] + new_lines + self.data[i + 1:]
                #     if any_line_split:
                #         self._set_state(HipHopQuoteParser.State.UNPACK_QUOTE_LINES)
                #     else:
                #         self._set_state(HipHopQuoteParser.State.TRIM_NON_QUOTE_CONTENT)
                #
                # elif self._in_state(HipHopQuoteParser.State.TRIM_NON_QUOTE_CONTENT):
                #     # Sometimes stuff before and after the quote is still left in data, remove it now
                #     # Find the line with quote author and delete everything below it
                #     author_line_index = -1
                #     for i in range(len(self.data)):
                #         element = self.data[i][0] if type(self.data[i]) == list else self.data[i]
                #         element_string = element.get_text() if type(element) == Tag else str(element)
                #         for author_prefix in AUTHOR_PREFIXES:
                #             if element_string.strip().startswith(author_prefix):
                #                 self.data = self.data[:i + 1]
                #                 author_line_index = i
                #                 break
                #         if author_line_index != -1:
                #             break
                #     if author_line_index == -1:
                #         # There is no author, so there's no quote
                #         self._print_error('No author found - no quote in this post')
                #         self.result = HipHopQuoteParser.Result.NO_QUOTE
                #         self._set_state(HipHopQuoteParser.State.FINAL)
                #     else:
                #         # Quote often starts with quotation mark
                #         # If we find a line starting with quotation mark it's the start of the quote
                #         for i in range(len(self.data)):
                #             element = self.data[i][0]
                #             element_string = element.get_text() if type(element) == Tag else str(element)
                #             for quotation_mark in QUOTATION_MARKS:
                #                 if element_string.strip().startswith(quotation_mark):
                #                     self.data = self.data[i:]
                #                     element = None
                #                     break
                #             if not element:
                #                 break
                #
                #         if len(self.data) > 0:
                #             self._set_state(HipHopQuoteParser.State.PARSE_QUOTE_BODY)
                #         else:
                #             self._print_error('No quote in this post')
                #             self.result = HipHopQuoteParser.Result.NO_QUOTE
                #             self._set_state(HipHopQuoteParser.State.FINAL)
                #
                # elif self._in_state(HipHopQuoteParser.State.PARSE_QUOTE_BODY):
                #     # Quote lines may possibly be lists of various things including tags so join them
                #     for i in range(len(self.data) - 1):
                #         quote_line = self.data[i]
                #         if type(quote_line) == Tag:
                #             quote_line = quote_line.get_text()
                #         else:
                #             # This means it's collection of items
                #             # So make all of them strings
                #             for j in range(len(quote_line)):
                #                 if type(quote_line[j]) == Tag:
                #                     quote_line[j] = quote_line[j].get_text()
                #             # And now join them
                #             quote_line = ''.join(quote_line)
                #         self.data[i] = quote_line
                #
                #     quote_lines = self.data[:-1]
                #     self.song_quote = '\n'.join(quote_lines)
                #     self._set_state(HipHopQuoteParser.State.PARSE_LAST_LINE)
                #
                # elif self._in_state(HipHopQuoteParser.State.PARSE_LAST_LINE):
                #     last_line = self.data[-1]
                #     if type(last_line) == NavigableString:
                #         last_line = [last_line]
                #     else:
                #         # Convert all tags to text
                #         last_line = [e.get_text() if type(e) == Tag else e for e in last_line]
                #
                #     # Remove quotes from all elements in the line and remove all empty strings
                #     for i in reversed(range(len(last_line))):
                #         if re.match('^[^0-9a-zA-Z]*$', last_line[i]):
                #             # Remove if element contains no letters or digits
                #             del last_line[i]
                #         else:
                #             # Or at least strip all quotes
                #             previous_element_length = -1
                #             element_length = len(last_line[i])
                #             while not element_length == previous_element_length:
                #                 previous_element_length = element_length
                #                 last_line[i] = strip_quotes(last_line[i])
                #                 element_length = len(last_line[i])
                #
                #     self.data[-1] = last_line
                #
                #     if len(last_line) == 1:
                #         self._set_state(HipHopQuoteParser.State.SPLIT_LAST_LINE)
                #     elif len(last_line) > 1:
                #         self._set_state(HipHopQuoteParser.State.PARSE_SONG_TITLE_AND_AUTHOR)
                #     else:
                #         self._print_error('No artist and song to parse')
                #         self._set_state(HipHopQuoteParser.State.FINAL)
                #
                # elif self._in_state(HipHopQuoteParser.State.SPLIT_LAST_LINE):
                #     last_line = self.data[-1]
                #     last_line_splits = last_line[0].split(', ')
                #     if len(last_line_splits) >= 2:
                #         self.data[-1] = last_line_splits
                #         self._set_state(HipHopQuoteParser.State.PARSE_SONG_TITLE_AND_AUTHOR)
                #     else:
                #         self._print_error('Last line: "%s" - not song lyrics quote' % last_line)
                #         self.result = HipHopQuoteParser.Result.NO_QUOTE
                #         self._set_state(HipHopQuoteParser.State.FINAL)
                #
                # elif self._in_state(HipHopQuoteParser.State.PARSE_SONG_TITLE_AND_AUTHOR):
                #     last_line = self.data[-1]
                #     if len(last_line) == 2:
                #         self.song_artist = last_line[0].strip()
                #         if self.song_artist.endswith(','):
                #             self.song_artist = self.song_artist[:-1]
                #         for artist_prefix in AUTHOR_PREFIXES:
                #             if self.song_artist.startswith(artist_prefix):
                #                 self.song_artist = self.song_artist[len(artist_prefix):]
                #                 break
                #         self.song_artist = self.song_artist.strip()
                #         self.song_artist = strip_quotes(self.song_artist)
                #         self.song_artist = self.song_artist.strip()
                #
                #         self.song_title = last_line[1].strip()
                #         self.song_title = strip_quotes(self.song_title)
                #         self.song_title = self.song_title.strip()
                #     self._set_state(HipHopQuoteParser.State.FINAL)
                #
                # elif self._in_state(HipHopQuoteParser.State.FINAL):
                #     if not self.song_artist or not self.song_title or not self.song_quote:
                #         return [self.result]
                #     else:
                #         return HipHopQuoteParser.Result.SUCCESS, self.song_artist.strip(), \
                #                self.song_title.strip(), self.song_quote.strip()
