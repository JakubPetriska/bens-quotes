import re
from enum import Enum

from bs4 import Comment
from bs4 import NavigableString
from bs4 import Tag

NEWLINE_TAGS = ['br', 'p', 'div']
QUOTATION_MARKS = '\'"“”’'
AUTHOR_PREFIXES = ['—', '–', '--', '-']


def filter_out_empty_elements(l):
    """Filters out strings containing only whitespace, empty strings and empty arrays."""
    return list(filter(lambda i: i.strip() if type(i) == NavigableString else i, l))


def strip_quotes(string):
    while re.match('^[%s]{1}.*' % QUOTATION_MARKS, string):
        string = string[1:]
    while re.match('.*[%s]{1}$' % QUOTATION_MARKS, string):
        string = string[:-1]
    return string


class HipHopQuoteParser:
    class State(Enum):
        INITIAL = 1

        # Following states gather blocks from the input data that contain the quotes, e.g. their last line
        # starts with the dash or similar character which indicates quote end.
        # The obtained blocks are stored in the quote_blocks variable.
        GATHER_QUOTE_BLOCKS = 20

        REMOVE_BLOCKS_WITHOUT_QUOTE = 22

        UNWRAP_BLOCKS_WITH_QUOTE = 24

        # This state turns quote block into parsed quote. Tuple in format (quote, author, song_title).
        PARSE_QUOTE = 50

        FINAL = 100

    def __init__(self):
        self.state = HipHopQuoteParser.State.INITIAL
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
        self.state = HipHopQuoteParser.State.INITIAL

        self.post_name = post_name
        self.data = post_excerpt_div
        self.quote_blocks = []
        self.parsed_quotes = []

        while True:
            if self._in_state(HipHopQuoteParser.State.INITIAL):
                self._set_state(HipHopQuoteParser.State.FINAL)

            elif self._in_state(HipHopQuoteParser.State.FINAL):
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
