import json

import pandas as pd

from coreftools.formats import conll, conll_transform
import depparser_tree

#from . import load_cache, save_cache, get_value, get_list_value
from . import get_value, get_list_value


def add_named_entities(mentions, *conll_fpaths, col_index=12):

    print("- named entities")

    dic = {
        doc.key: {
            (start, stop): kind
            for sent in doc.sentences
            for start, stop, kind in conll.col2spans(
                sent.iter_tokens(col_index),
                offset=sent.first_token_index)
        }
        for doc in conll.read_files(*conll_fpaths,
            sep="\t", ignore_comments=True, ignore_double_indices=True)
    }

    mentions['named_entity_type'] = [
        get_value(dic, text, start, stop, extend=1)
        for text, start, stop in zip(
            mentions['text_id'],
            mentions['text_start'],
            mentions['text_stop'],
        )
    ]
    mentions['is_named_entity'] = [
        not pd.isnull(val)
        for val in mentions['named_entity_type']
    ]
    mentions['is_pers'] = mentions['named_entity_type']=='PERS'



def add_speakers(mentions, *conll_fpaths, col_index=10):

    print("- speaker")

    dic = {
        doc.key: {
            i: sent.tokens[0][col_index]
                if sent.tokens[0][col_index] not in "-_" else None
            for i, sent in enumerate(doc.sentences) }
        for doc in conll.read_files(*conll_fpaths,
            sep="\t", ignore_comments=True, ignore_double_indices=True)
    }

    mentions['speaker'] = [
        dic[text_id][int(text_sent_index)]
        for text_id, text_sent_index in zip(
            mentions['text_id'],
            mentions['text_sent_index'],
        )
    ]




def _gattr(obj, attr, add=None):
    if obj is None:
        return None
    attr = getattr(obj, attr)
    if add is not None:
        attr += add
    return attr


_NODE_ATTRIBUTES = (

    ('h_lemma', lambda n: n.lemma),
    'pos',
    'deplabel',
    'subdeplabel',
    ('head', lambda n: n.form),
    ('h_level', lambda n: n.level),

    ('node_id', lambda n: n.id_),
    ('parent_node_id', lambda n: _gattr(n.parent, 'id_')),
    ('grandparent_node_id',
        lambda n: _gattr(_gattr(n.parent, 'parent'), 'id_')),

    'parent_pos',
    'parent_deplabel',
    'parent_subdeplabel',

    'parent_clause_pos',
    'parent_clause_deplabel',
    'parent_clause_subdeplabel',
    'parent_clause_id',

    ('preposition', lambda n:
        " ".join(_gattr(_gattr(n, 'preposition'), 'text'))
        if _gattr(n, 'preposition') else None),
    'in_pp',

    'node_depth',
    'clause_depth',

    'is_in_main_clause',
    'is_in_embedded',
    'is_in_matrix',

    'dependent_count',
    'predependent_count',
    'postdependent_count',
    'noun_dependent_counter',
    'appos_dependent_counter',
    'num_dependent_counter',
    'clause_dependent_counter',
    'adjective_dependent_counter',

    'determiner_string',
    'determiner_head_string',
    'determiner_head_lemma',
    'has_genitive_determiner',
    'has_complex_determiner',
    'h_broad_pspeech',
    'h_noun_type',
    'h_person',
    'h_pronoun_type',
    'h_number',
    'h_gender',
    'h_reflex',
    'h_poss',
    'h_definite',
    'h_start',
    'h_stop',

    'is_arg',
    'struct_id',
    'arg_index',
    'arg_type',
    'struct_is_negative',
    'struct_is_passive',
    'struct_tense',
    'struct_mood',
    'struct_person',

    'is_relative_pronoun',
    'is_reciprocal',
    'is_reflexive',
    'is_expletive',
    'is_complement',
    'is_apposition',

    'is_verb',
    'is_verb_without_subject',

    'is_subject',
    'is_object',
    'is_non_core',
    'is_clause',
    'is_dependent',
    'dependent_type',

    'is_determiner',
    'is_possessive_determiner',
    'is_genitive_determiner',

    ('h_text_start', lambda n: n.text_start),
    ('h_text_stop', lambda n: n.text_stop),

)

#_NODE_ATTRIBUTE_LIST = [
#    x if isinstance(x, str) else x[0] for x in _NODE_ATTRIBUTES
#]

_NODE_ATTRIBUTES_FOR_RELATIONS = (
    'descendant_list',
    'phrase_descendant_list',
    'clause_descendant_list',
)


def add_syntax(mentions, *conll_fpaths, head_pos_cache=None):

    print("- syntax")

    mention_gby = mentions.groupby('text_id')

    dic = dict()
    for doc_key, doc in conll_transform.read_files(
            *conll_fpaths, sep="\t", ignore_comments=True,
            ignore_double_indices=True).items():
        if doc_key not in mention_gby.groups:
            continue
        dic[doc_key] = []
        cumul = 0
        for root, tokens in depparser_tree.iter_sentences(
                doc,
                indices=None, # = default
                tagset='ud'):
            for token in tokens:
                token.text_start = token.index + cumul
                token.text_stop = token.index+1 + cumul
            dic[doc_key].append((root, tokens))
            cumul += len(tokens)

    def get_syntax(text, sent, start, stop):
        root, tokens = dic[text][sent]
        head = depparser_tree.UDToken.get_head(tokens[start:stop])
        return [
            getattr(head, attr) if isinstance(attr, str) else attr[1](head)
            for attr in _NODE_ATTRIBUTES
        ]

    df = pd.DataFrame(
        data=(
            get_syntax(text, sent, start, stop)
            for text, sent, start, stop in zip(
                mentions['text_id'],
                mentions['text_sent_index'],
                mentions['start'], # sentence relative
                mentions['stop'],
            )
        ),
        columns=[
            attr if isinstance(attr, str) else attr[0]
            for attr in _NODE_ATTRIBUTES
        ],
        index=mentions.index,
    )
    return pd.concat([mentions, df], axis=1)


def add_genre(db):

    print("- replace genre")

    db['texts']['genre'] = [
        "wk" if "wiki" in x
        else "pr" if "republicain" in x
        else "ot"
        for x in db['texts'].index
    ]


def add_other_annotations(db):

    print("- other annotations")

    # nothing


def add_token_pos(db, *infpaths):

    print("- token part of speech")

    tokens = db['tokens']
    groupped = tokens.groupby('text_id')

    dic = dict()
    for doc in conll.read_files(*infpaths, sep="\t",
            ignore_double_indices=True):
        df = groupped.get_group(doc.key)
        df = df.sort_index()
        tks = [ t for sent in doc.sentences for t in sent.iter_tokens(3) ]
        assert len(df.index) == len(tks), (len(df.index), len(tks))
        d = dict(zip(df.index, tks))
        dic.update(d)

        #for sent in doc.sentences:
        #    pspeech_col = list(sent.iter_tokens(4))

    tokens['pos'] = [ dic[index] for index in tokens.index ]



def add_dem1921_specific_annotations(db, *input_files, replace_genre=False):

    add_named_entities(db['mentions'], *input_files)
    add_speakers(db['mentions'], *input_files)
    db['mentions'] = add_syntax(db['mentions'], *input_files)

    if replace_genre:
        add_genre(db)
    add_other_annotations(db)
    add_token_pos(db, *input_files)

    return db

