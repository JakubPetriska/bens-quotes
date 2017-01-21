import re
from enum import Enum

from bs4 import NavigableString
from bs4 import Tag

NEWLINE_TAGS = ['br', 'p', 'div']
QUOTES = '\'"“”’'
ARTIST_PREFIXES = ['—', '--', '-']


def filter_out_whitespace_strings(l):
    return list(filter(lambda i: False if type(i) == NavigableString and not i.strip() else True, l))


def strip_quotes(string):
    while re.match('^[%s]{1}.*' % QUOTES, string):
        string = string[1:]
    while re.match('.*[%s]{1}$' % QUOTES, string):
        string = string[:-1]
    return string


class HipHopQuoteParser:
    class Result:
        SUCCESS = 0
        NO_QUOTE = 1
        UNKNOWN_FORMAT = 2

    class State(Enum):
        INITIAL = 1

        REMOVE_NON_QUOTE_CONTENT = 10

        UNPACK_QUOTE_LINES = 21

        UNPACK_QUOTE_LINES_REMOVE_WRAPPING_TAG = 22

        UNPACK_QUOTE_LINES_SPLIT_BY_NEWLINE = 23

        PARSE_QUOTE_BODY = 24

        PARSE_LAST_LINE = 25

        SPLIT_LAST_LINE = 26

        PARSE_SONG_TITLE_AND_AUTHOR = 28

        FINAL = 100

    def __init__(self):
        self.state = HipHopQuoteParser.State.INITIAL
        self.song_artist, self.song_title, self.song_quote = None, None, None
        self.result = HipHopQuoteParser.Result.UNKNOWN_FORMAT
        self.data = None

    def _set_state(self, state):
        self.state = state

    def _in_state(self, state):
        return self.state == state

    def _print_error(self, reason):
        print('Error - %s' % reason)
        print('\tState: %s, data: %s' % (self.state, self.data))

    def parse(self, post_excerpt_div):
        self.state = HipHopQuoteParser.State.INITIAL
        self.song_artist, self.song_title, self.song_quote = None, None, None
        self.result = HipHopQuoteParser.Result.UNKNOWN_FORMAT
        self.data = post_excerpt_div

        while True:
            if self._in_state(HipHopQuoteParser.State.INITIAL):
                block_quote = post_excerpt_div.blockquote
                if block_quote:
                    # Often the quote is wrapped in <blockquote> tag, this is the case. Jackpot!
                    self.data = filter_out_whitespace_strings(block_quote.contents)
                    self._set_state(HipHopQuoteParser.State.UNPACK_QUOTE_LINES)
                else:
                    self._set_state(HipHopQuoteParser.State.REMOVE_NON_QUOTE_CONTENT)

            elif self._in_state(HipHopQuoteParser.State.REMOVE_NON_QUOTE_CONTENT):
                # self.data = filter_out_whitespace_strings(self.data.contents)
                # for i in range(len(self.data) - 1, -1, -1):
                self.song_artist, self.song_title, self.song_quote = 'Cake', 'is', 'lie'
                self._set_state(HipHopQuoteParser.State.FINAL)

            elif self._in_state(HipHopQuoteParser.State.UNPACK_QUOTE_LINES):
                for i in range(len(self.data)):
                    if type(self.data[i]) == Tag:
                        self.data[i] = filter_out_whitespace_strings(self.data[i].contents)
                self.state = HipHopQuoteParser.State.UNPACK_QUOTE_LINES_SPLIT_BY_NEWLINE

            elif self._in_state(HipHopQuoteParser.State.UNPACK_QUOTE_LINES_SPLIT_BY_NEWLINE):
                any_line_split = False
                for i in reversed(range(len(self.data))):
                    line = self.data[i]
                    new_line_positions = []
                    for j in range(len(line)):
                        if type(line[j]) == Tag and line[j].name in NEWLINE_TAGS:
                            new_line_positions.append(j)
                    if len(new_line_positions) > 0:
                        any_line_split = True
                        new_line_positions.append(len(line))
                        new_lines = []
                        line_start = 0
                        for new_line_position in new_line_positions:
                            if new_line_position - line_start > 0:
                                new_line = line[line_start:new_line_position]
                                if len(new_line) == 1:
                                    new_line = new_line[0]
                                new_lines.append(new_line)
                                line_start = new_line_position
                        self.data = self.data[:i] + new_lines + self.data[i + 1:]
                if any_line_split:
                    self._set_state(HipHopQuoteParser.State.UNPACK_QUOTE_LINES)
                else:
                    self._set_state(HipHopQuoteParser.State.PARSE_QUOTE_BODY)

            elif self._in_state(HipHopQuoteParser.State.PARSE_QUOTE_BODY):
                # Quote lines may possibly be lists of various things including tags so join them
                for i in range(len(self.data) - 1):
                    quote_line = self.data[i]
                    if type(quote_line) == Tag:
                        quote_line = quote_line.get_text()
                    else:
                        # This means it's collection of items
                        # So make all of them strings
                        for j in range(len(quote_line)):
                            if type(quote_line[j]) == Tag:
                                quote_line[j] = quote_line[j].get_text()
                        # And now join them
                        quote_line = ''.join(quote_line)
                    self.data[i] = quote_line

                quote_lines = self.data[:-1]
                self.song_quote = '\n'.join(quote_lines)
                self._set_state(HipHopQuoteParser.State.PARSE_LAST_LINE)

            elif self._in_state(HipHopQuoteParser.State.PARSE_LAST_LINE):
                last_line = self.data[-1]
                # Convert all tags to text
                last_line = [e.get_text() if type(e) == Tag else e for e in last_line]

                # Remove quotes from all elements in the line and remove all empty strings
                for i in reversed(range(len(last_line))):
                    if re.match('^[^0-9a-zA-Z]*$', last_line[i]):
                        # Remove if element contains no letters or digits
                        del last_line[i]
                    else:
                        # Or at least strip all quotes
                        previous_element_length = -1
                        element_length = len(last_line[i])
                        while not element_length == previous_element_length:
                            previous_element_length = element_length
                            last_line[i] = strip_quotes(last_line[i])
                            element_length = len(last_line[i])

                self.data[-1] = last_line

                if len(last_line) == 1:
                    self._set_state(HipHopQuoteParser.State.SPLIT_LAST_LINE)
                elif len(last_line) > 1:
                    self._set_state(HipHopQuoteParser.State.PARSE_SONG_TITLE_AND_AUTHOR)
                else:
                    self._print_error('No artist and song to parse')
                    self._set_state(HipHopQuoteParser.State.FINAL)

            elif self._in_state(HipHopQuoteParser.State.SPLIT_LAST_LINE):
                last_line = self.data[-1]
                last_line_splits = last_line[0].split(', ')
                if len(last_line_splits) >= 2:
                    self.data[-1] = last_line_splits
                    self._set_state(HipHopQuoteParser.State.PARSE_SONG_TITLE_AND_AUTHOR)
                else:
                    self._print_error('Last line: "%s" - not song lyrics quote' % last_line)
                    self.result = HipHopQuoteParser.Result.NO_QUOTE
                    self._set_state(HipHopQuoteParser.State.FINAL)

            elif self._in_state(HipHopQuoteParser.State.PARSE_SONG_TITLE_AND_AUTHOR):
                last_line = self.data[-1]
                if len(last_line) == 2:
                    self.song_artist = last_line[0].strip()
                    if self.song_artist.endswith(','):
                        self.song_artist = self.song_artist[:-1]
                    for artist_prefix in ARTIST_PREFIXES:
                        if self.song_artist.startswith(artist_prefix):
                            self.song_artist = self.song_artist[len(artist_prefix):]
                            break
                    self.song_artist = self.song_artist.strip()
                    self.song_artist = strip_quotes(self.song_artist)
                    self.song_artist = self.song_artist.strip()

                    self.song_title = last_line[1].strip()
                    self.song_title = strip_quotes(self.song_title)
                    self.song_title = self.song_title.strip()
                self._set_state(HipHopQuoteParser.State.FINAL)

            elif self._in_state(HipHopQuoteParser.State.FINAL):
                if not self.song_artist or not self.song_title or not self.song_quote:
                    return [self.result]
                else:
                    return HipHopQuoteParser.Result.SUCCESS, self.song_artist, self.song_title, self.song_quote
