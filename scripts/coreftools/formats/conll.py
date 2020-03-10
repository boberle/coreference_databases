"""
This module contains various functions to manipulate mention and coreference
informations from a conll files (last column).

TODO: a summary of each function
"""


import re
import json

import numpy as np
import scipy.optimize

from .. import chains
from . import conll_transform




class Token:

    sep = None

    def __init__(self, data):
        if isinstance(data, str):
            if self.__class__.sep is not None:
                self.columns = data.split(self.__class__.sep)
            else:
                self.columns = data.split()
        else:
            self.columns = data

    def __getitem__(self, key):
        return self.columns[key]

    def __len__(self):
        return len(self.columns)

    def __iter__(self):
        return iter(self.columns)



class Sentence:

    def __init__(self, tokens=None, first_token_index=0):
        self.tokens = tokens if tokens is not None else []
        self.mentions = None
        self.first_token_index = first_token_index

    def add_line(self, line):
        self.tokens.append(Token(line))

    def iter_tokens(self, columns=None):
        for token in self.tokens:
            if columns is None:
                yield token
            elif isinstance(columns, int):
                yield token[columns]
            else:
                yield [token[i] for i in columns]
                

    def __str__(self):
        res = []
        lengths = None
        for token in self.tokens:
            if lengths is None:
                lengths = [0]*len(token)
            for c, col in enumerate(token):
                lengths[c] = max(lengths[c], len(col))
        res = [""] * len(self.tokens)
        for i, token in enumerate(self.tokens):
            for c, col in enumerate(token):
                extra = 0 if c == 0 else 3
                fmt = "%% %ds" % (lengths[c] + extra)
                res[i] += fmt % col
        return "\n".join(res)


    def __len__(self):
        return len(self.tokens)




class Document:



    def __init__(self, key, sentences=None):
        self.key = key
        self.sentences = sentences if sentences is not None else []
        self._add_sentence = False
        self.chains = None
        self.mentions = None



    def add_line(self, line):
        cumul = sum(len(s) for s in self.sentences)
        if not line.strip():
            self._add_sentence = True
            return
        if self._add_sentence:
            self._add_sentence = False
            self.sentences.append(Sentence(first_token_index=cumul))
        if not self.sentences:
            self.sentences.append(Sentence(first_token_index=cumul))
        self.sentences[-1].add_line(line)


    def add_raw_sentence(self, sentence):
        cumul = sum(len(s) for s in self.sentences)
        sentence = Sentence(
            tokens = [ Token(token) for token in sentence ],
            first_token_index=cumul,
        )
        self.sentences.append(sentence)
        


    def compute_mentions_n_chains(self):
        assert not self.chains
        for i, sent in enumerate(self.sentences):
            sent.mentions = col2mentions(list(sent.iter_tokens(-1)))
            for mention in sent.mentions:
                mention.text_start = mention.start + sent.first_token_index
                mention.text_stop = mention.stop + sent.first_token_index
        mentions = [ m for sent in self.sentences for m in sent.mentions ]
        self.mentions = mentions
        self.chains = chains.index2chains(
            mentions,
            [ m.chain for m in mentions ]
        )



class Mention:

    def __init__(self, start, stop, chain, sentence=None, text_start=None,
            text_stop=None):
        self.start = start
        self.stop = stop
        self.chain = int(chain)
        self.sentence = sentence
        self.text_start = text_start
        self.text_stop = text_stop



START_DOC_PATTERN = re.compile(
    r'#begin document (.+?)' + '\n')

DOUBLE_INDEX_PATTERN = re.compile(
    r'\d+-\d+\s')

END_DOC_STRING = '#end document\n'

def read_files(*fpaths, sep=None, ignore_double_indices=False,
        ignore_comments=True, key_callback=None):
    """Iter over documents in conll files."""

    if sep is not None:
        Token.sep = sep

    cur_doc = None
    for fpath in fpaths:
        for line in open(fpath):
            if not line.strip() and not cur_doc: # white lines btw docs
                continue
            m = START_DOC_PATTERN.fullmatch(line)
            # new document
            if m:
                if cur_doc: # missing "#end document"
                    yield cur_doc
                key = m.group(1)
                if key_callback:
                    key = key_callback(key)
                cur_doc = Document(key)
            elif line == END_DOC_STRING:
                yield cur_doc
                cur_doc = None
            elif line.startswith("#") and ignore_comments:
                pass
            else:
                if DOUBLE_INDEX_PATTERN.match(line) and ignore_double_indices:
                    pass
                else:
                    if not cur_doc:
                        raise RuntimeError("line '%s' before '#begin document'"
                            % (line.strip()))
                    cur_doc.add_line(line)

    if cur_doc: # missing "#end document"
        yield cur_doc



def write_file(fpath, docs):
    """Write a conll file."""

    with open(fpath, 'w') as fh:
        for doc in docs:
            fh.write('#begin document %s\n' % doc.key)
            fh.write("\n\n".join(str(s) for s in doc.sentences))
            fh.write('#end document\n\n')


CONLL_MENTION_PATTERN = re.compile(
    r'(?:\((?P<mono>\d+)\)|\((?P<start>\d+)|(?P<end>\d+)\))')

def col2mentions(column):
    """Compute mentions from the raw last column of the conll file.

    Return a list of Mention.

    Parameters:
    -----------
    column: list of strings
        List of tokens: eg `['*', '(1', '*', '1)', ...]`
    """

    return [
        Mention(*pos, chain)
        for pos, chain in conll_transform.compute_mentions(column)
    ]


def col2simple_spans(column, offset=0):
    """Same as `col2spans()` but without support for nested spans."""

    filo = []
    for i, cell in enumerate(column):
        if cell.startswith('(') and cell.endswith(')'):
            yield i+offset, i+1+offset, cell[1:-2 if cell[-2] in '-_*' else -1]
        elif cell.startswith('('):
            filo.append((i, cell[1:-1 if cell[-1] in '_*' else None]))
        elif cell.endswith(')'):
            last = filo.pop()
            yield last[0]+offset, i+1+offset, last[1]



NESTED_COLUMN_PARSER_PATERN = re.compile(
    r'(?:\((?P<mono>%s)[-_*]\)|\((?P<start>%s)|(?P<end>)\))'
    % tuple(['[-_A-Za-z0-9]+']*2))

def col2spans(column, offset=0):
    """Iter over spans from a raw column of the conll file.

    Yield tuples of the form `(start, stop, text)`, where `text` is the text of
    the span.  For example: 
        *
        (foo*
        (bar*
        *
        *))
    will yield:
        (1, 4, "foo")
        (2, 4, "bar")

    Parameters:
    -----------
    column: list of strings
        List of tokens: eg `['*', '(foo*', '*', '*)', ...]`
    """
    filo = []
    for i, cell in enumerate(column):
        for m in NESTED_COLUMN_PARSER_PATERN.finditer(cell):
            if m.lastgroup == 'mono':
                yield i+offset, i+1+offset, m.group(m.lastgroup)
            elif m.lastgroup == 'start':
                filo.append((i, m.group(m.lastgroup)))
            elif m.lastgroup == 'end':
                last_start_index, last_text = filo.pop()
                yield last_start_index+offset, i+1+offset, last_text
            else:
                assert False


