import re
from enum import Enum

from bs4 import NavigableString
from bs4 import Tag

QUOTES = '\'"“”’'
ARTIST_PREFIXES = ['—', '--']


def filter_out_whitespace_strings(l):
    return list(filter(lambda i: False if type(i) == NavigableString and not i.strip() else True, l))


def strip_quotes(string):
    while re.match('^[%s]{1}.*' % QUOTES, string):
        string = string[1:]
    while re.match('.*[%s]{1}$' % QUOTES, string):
        string = string[:-1]
    return string


class HipHopQuoteParser:
    class State(Enum):
        INITIAL = 1

        FINAL = 2

        # We have a tag, extract it's content
        STRIP_WRAPPING_TAG = 4

        # We have multiple tags that together contain the string
        PARSE_QUOTE_LINES = 6

        # Expects a list of strings corresponding to quote lines
        # with last element being the last line of quote containing author and title
        # The last element can be a list of strings (last line containing author and song title)
        PROCESS_QUOTE = 7

        SPLIT_LAST_LINE = 8

        PROCESS_LAST_LINE = 9

    def __init__(self):
        self.state = HipHopQuoteParser.State.INITIAL
        self.song_artist, self.song_title, self.song_quote = None, None, None
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
        self.data = post_excerpt_div

        while True:
            if self._in_state(HipHopQuoteParser.State.INITIAL):
                block_quote = post_excerpt_div.blockquote
                if block_quote:
                    self.data = block_quote
                    self._set_state(HipHopQuoteParser.State.STRIP_WRAPPING_TAG)
                else:
                    self.song_artist, self.song_title, self.song_quote = 'Cake', 'is', 'lie'
                    self._set_state(HipHopQuoteParser.State.FINAL)

            elif self._in_state(HipHopQuoteParser.State.STRIP_WRAPPING_TAG):
                contents = self.data.contents
                contents = filter_out_whitespace_strings(contents)
                contents_count = len(contents)

                if contents_count > 1:
                    self.data = contents
                    self._set_state(HipHopQuoteParser.State.PARSE_QUOTE_LINES)
                elif contents_count == 1:
                    self.data = contents[0]
                    self._set_state(HipHopQuoteParser.State.STRIP_WRAPPING_TAG)
                else:
                    self._set_state(HipHopQuoteParser.State.FINAL)

            elif self._in_state(HipHopQuoteParser.State.PARSE_QUOTE_LINES):
                self.data = filter_out_whitespace_strings(self.data)

                # In case quote is separated by <br> take those out and split into lines
                while type(self.data[-1]) == Tag and self.data[-1].name == 'br':
                    last_element_split = self.data[-1].contents
                    contains_more_lines = False
                    for element in last_element_split:
                        if type(element) == Tag and element.name == 'br':
                            contains_more_lines = True
                            break
                    if contains_more_lines:
                        self.data = self.data[:-1] + self.data[-1].contents
                    else:
                        self.data = self.data[:-1]
                        self.data.append(last_element_split
                                                     if len(last_element_split) > 1 else last_element_split[0])

                # Make all quote lines text
                for i in range(len(self.data) - 1):
                    if type(self.data[i]) == Tag:
                        self.data[i] = self.data[i].get_text()

                # Process the last line
                last_line = self.data[-1]
                # Strip all single tags wrapping the last line
                while type(last_line) == Tag:
                    last_line = last_line.contents
                    last_line = filter_out_whitespace_strings(last_line)
                    if len(last_line) == 1:
                        last_line = last_line[0]

                if not type(last_line) == NavigableString:
                    # This means that last line is a collection
                    last_line = [last_line_element if type(last_line_element) == NavigableString
                                 else last_line_element.get_text()
                                 for last_line_element in last_line]
                self.data[-1] = last_line
                self._set_state(HipHopQuoteParser.State.PROCESS_QUOTE)

            elif self._in_state(HipHopQuoteParser.State.PROCESS_QUOTE):
                quote_lines = self.data[:-1]
                self.song_quote = '\n'.join(quote_lines)

                last_line = self.data[-1]
                if type(last_line) == NavigableString:
                    self._set_state(HipHopQuoteParser.State.SPLIT_LAST_LINE)
                else:
                    self._set_state(HipHopQuoteParser.State.PROCESS_LAST_LINE)

            elif self._in_state(HipHopQuoteParser.State.SPLIT_LAST_LINE):
                last_line = self.data[-1]
                last_line_splits = last_line.split(', ')
                if len(last_line_splits) == 2:
                    self.data[-1] = last_line_splits
                    self._set_state(HipHopQuoteParser.State.PROCESS_LAST_LINE)
                else:
                    # TODO error message
                    print('%s not Hip Hop quote' % last_line)
                    self._set_state(HipHopQuoteParser.State.FINAL)

            elif self._in_state(HipHopQuoteParser.State.PROCESS_LAST_LINE):
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
                    print('Cannot parse quote (%s, %s, %s)' % (self.song_artist, self.song_title, self.song_quote))
                    return None
                else:
                    return self.song_artist, self.song_title, self.song_quote
