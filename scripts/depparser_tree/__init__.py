import sys

import coreftools.formats.conll_transform
from . import token as token_module
from .ud_token import UDToken


def iter_sentences(doc, indices=None, tagset=None):

    if tagset == "ud":
        cls = UDToken
    elif tagset is None:
        cls = None
    else:
        assert False, tagset

    yield from token_module.iter_sentences(doc, indices, cls=cls)



def iter_documents(*fpaths, indices=None, tagset=None, by_doc=False):

    docs = coreftools.formats.conll_transform.read_files(
        *fpaths,
        sep="\t",
        ignore_double_indices=True,
        ignore_comments=True
    )

    for doc_key, doc in docs.items():
        if by_doc:
            yield doc_key, list(iter_sentences(doc, indices, tagset))
        else:
            for i, (root, tokens) \
                    in enumerate(iter_sentences(doc, indices, tagset)):
                yield doc_key, i, root, tokens


def get_head(tokens):
    min_token = None
    min_level = sys.maxsize
    for token in tokens:
        if token.level < min_level:
            min_token = token
            min_level = token.level
    assert min_token
    return min_token

