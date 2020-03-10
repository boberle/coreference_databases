import json
import os
import itertools

import pandas as pd

from coreftools.formats import conll
from . import load_cache, save_cache, get_value, get_list_value

from ._conll_tree_parser import TreeParser

import nltk
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer




def extract_named_entities(outfpath, *infpaths, key_callback=None):
    print("- extracting named entities")
    data = {
        #doc.key: {
        #    (start, stop): kind
        #    for start, stop, kind in [
        #        ne
        #        for sent in doc.sentences
        #        for ne in conll.col2spans(sent.iter_tokens(10),
        #            offset=sent.first_token_index)
        #    ]
        #}
        doc.key: {
            (start, stop): kind
            for sent in doc.sentences
            for start, stop, kind in conll.col2spans(sent.iter_tokens(10),
                offset=sent.first_token_index)
        }
        for doc in conll.read_files(*infpaths, key_callback=key_callback)
    }
    save_cache(outfpath, data)


"""
# very slow because of `mentions.loc[i]`

#def annotate_name_entities(mentions, fpath):
    dic = load_cache(fpath)
    mentions['named_entity_type'] = [
        get_value(
            dic,
            *mentions.loc[i][['text_id', 'text_start', 'text_stop']],
            extend=1)
        for i in mentions.index
    ]
    mentions['is_named_entity'] = mentions['named_entity_type'].notna()
    mentions['is_name'] = mentions['named_entity_type'].apply(
        lambda x: x in {'PERSON', 'FAC', 'ORG', 'GPE', 'WORK_OF_ART'})
"""



"""
# better but uses a bit more memory and is a bit slower because create a second
# DF and then concat

#def annotate_name_entities(mentions, fpath):
    dic = load_cache(fpath)
    def gen(text, start, stop):
        res = get_value(dic, text, start, stop, extend=1)
        if res is None:
            return [None]*3
        return (res, res is not None,
            res in {'PERSON', 'FAC', 'ORG', 'GPE', 'WORK_OF_ART'})
    df = pd.DataFrame(
        data=(
            gen(text, start, stop)
            for text, start, stop in zip(
                mentions['text_id'],
                mentions['text_start'],
                mentions['text_stop'],
            )
        ),
        columns=[
            'named_entity_type',
            'is_named_entity',
            'is_name',
        ],
        index=mentions.index,
    )
    return pd.concat([mentions, df], axis=1)
"""



# the best option, not using `mentions.loc[i]` and not creating a second DF

def annotate_name_entities(mentions, fpath):
    print("- named entities")
    dic = load_cache(fpath)
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
    mentions['is_name'] = mentions['named_entity_type'].apply(
        lambda x: x in {
            'PERSON',
            'FAC', 'FACILITY',
            'ORG',
            'GPE',
            'WORK_OF_ART',
            'NORP',
            'LOCATION',
            'PRODUCT',
            'EVENT',
            'LAW',
            'LANGUAGE',
            })
    mentions['is_name'] = mentions['named_entity_type'] == 'PERSON'



def extract_speakers(outfpath, *infpaths, key_callback=None):
    print("- extracting speaker")
    data = {
        doc.key:[
            sent.tokens[0][9] if sent.tokens[0][9] not in "-_" else None
            for sent in doc.sentences
        ]
        for doc in conll.read_files(*infpaths, key_callback=key_callback)
    }
    save_cache(outfpath, data, as_is=True)



def annotate_speakers(mentions, fpath):
    print("- spearkers")
    dic = load_cache(fpath, as_is=True)

    #for id_, ser in mentions[['text_id', 'text_sent_index']].iterrows():
    #    print(f"mention {id_}, text {ser['text_id']}, sent {ser['text_sent_index']}")
    #    print(dic[ser['text_id']][ser['text_sent_index']])

    mentions['speaker'] = [
        dic[text_id][text_sent_index]
        for text_id, text_sent_index in zip(
            mentions['text_id'],
            mentions['text_sent_index'],
        )
    ]




def extract_argument_structures(outfpath, *infpaths, key_callback=None):
    print("- extracting argument structures")
    data = dict()
    counter = 0
    for doc in conll.read_files(*infpaths, key_callback=key_callback):
        print("... from '%s'" % doc.key)
        data[doc.key] = dict()
        for sent in doc.sentences:
            cols = list(range(11, len(sent.tokens[0])-1))
            for col in cols:
                args = list(conll.col2spans(
                    sent.iter_tokens(col),
                    offset=sent.first_token_index))
                is_neg = bool(
                    (next((x for x in args if x[2] == "ARGM-NEG"), None)))
                dic = {
                    (start, stop): [counter+i, i, kind, is_neg]
                    for i, (start, stop, kind) in enumerate(args)
                    if kind != 'V'
                }
                counter += len(dic)
                data[doc.key].update(dic)
    save_cache(outfpath, data)



def annotate_argument_structures(mentions, fpath):
    print("- argument structures")
    dic = load_cache(fpath)

    def gen(text, start, stop):
        res = get_value(dic, text, start, stop, extend=1)
        if res is None:
            return (False, None, None, None, None, None)
        return (True,
            res[0],
            res[1],
            res[2],
            res[3],
            res[2] == "ARG0",
        )

    df = pd.DataFrame(
        data=(
            gen(text, start, stop)
            for text, start, stop in zip(
                mentions['text_id'],
                mentions['text_start'],
                mentions['text_stop'],
            )
        ),
        columns=[
            'is_arg',
            'struct_id',
            'arg_index',
            'arg_type',
            'struct_is_negative',
            'arg_is_agent',
        ],
        index=mentions.index,
    )
    return pd.concat([mentions, df], axis=1)



def extract_wordnet_synsets(*infpaths, outfpath, inventories2wordnet_fpath,
        syntax_cache_fpath, key_callback=None):
    """NOTE: WN in nltk is 3.0, so we are look for v3.0"""

    print("- extracting WordNet synsets")

    data = dict()

    # extract heads: datas = { doc_key: {(start, stop): [None, None]} }
    # (official synset, guessed synset)
    syntax_cache = load_cache(syntax_cache_fpath)
    h_text_start_index = _NODE_ATTRIBUTE_LIST.index('h_text_start')
    h_text_stop_index = _NODE_ATTRIBUTE_LIST.index('h_text_stop')
    for doc_key, syntax in syntax_cache.items():
        data[doc_key] = dict()
        for pos, syntax in syntax.items():
            h_pos = (syntax[h_text_start_index], syntax[h_text_stop_index])
            data[doc_key][h_pos] = [None, None]
    del syntax_cache

    # load cached data
    inventories2wordnet = json.load(open(inventories2wordnet_fpath))

    def synset_exists(synset):
        try:
            synset = wordnet.synset(synset)
            if synset.lemmas()[0].name()[0].isupper():
                return False
            return True
        except nltk.corpus.reader.wordnet.WordNetError:
            return False

    # for each head, extract (lemma, pos, word sense) and look into
    # inventories2wordnet to find the word net synset.  If not, set a guessed
    # one.  Check that the synset really exists.
    lemmatizer = WordNetLemmatizer()
    for doc in conll.read_files(*infpaths, key_callback=key_callback):
        print("... from '%s'" % doc.key)
        for sent in doc.sentences:
            for i, (form, pos, lemma, sense) in enumerate(zip(
                    sent.iter_tokens(3),
                    sent.iter_tokens(4),
                    sent.iter_tokens(6),
                    sent.iter_tokens(8))):
                i += sent.first_token_index
                #print(i, form, lemma, pos, sense)
                if (i,i+1) in data[doc.key]:
                    pos = pos[0].lower()
                    if not pos in 'nv':
                        continue
                    synset = None
                    # some sense recorded
                    if lemma != '-' and sense != '-':
                        inventory = "%s-%s-%s" % (lemma, pos, sense)
                        # for predicted pos, there may be some errors:
                        if inventory in inventories2wordnet:
                            for version, sense in inventories2wordnet[inventory]:
                                # WN in nltk is 3.0, so we are look for v3.0
                                if version == "3.0" and sense is not None:
                                    synset = "%s.%s.%02d" % \
                                        (lemma, pos, int(sense))
                                    #input(synset)
                                    if synset_exists(synset):
                                        data[doc.key][(i,i+1)][0] = synset
                                        #print('found (official)')
                                        break
                    if not data[doc.key][(i,i+1)][0]: # not found
                        if lemma == '-':
                            lemma = lemmatizer.lemmatize(form.lower(), pos)
                        synset = "%s.%s.01" % (lemma, pos)
                        #input(synset)
                        if synset_exists(synset):
                            #print('found (guessed)')
                            data[doc.key][(i,i+1)][1] = synset

    save_cache(outfpath, data)



def annotate_wordnet_synsets(mentions, fpath, keep_guessed=False,
        merge_official_and_guessed=False):
    print("- wordnet synsets")
    dic = load_cache(fpath)

    def gen(text, start, stop):
        official, guessed = get_list_value(dic, text, start, stop, length=2)
        if merge_official_and_guessed:
            return official if official else guessed
        return official, guessed

    df = pd.DataFrame(
        data=(
            gen(text, start, stop)
            for text, start, stop in zip(
                mentions['text_id'],
                mentions['h_text_start'],
                mentions['h_text_stop'],
            )
        ),
        columns=['wn'] if merge_official_and_guessed else ['wn', 'guessed_wn'],
        index=mentions.index,
    )
    if not keep_guessed:
        df = df.drop('guessed_wn', axis=1)
    return pd.concat([mentions, df], axis=1)




def _gattr(obj, attr, add=None):
    if obj is None:
        return None
    attr = getattr(obj, attr)
    if add is not None:
        attr += add
    return attr


_NODE_ATTRIBUTES = (

    # tag
    'tag',
    ('parent_phrase_tag', lambda n: _gattr(n.parent_phrase, 'tag')),
    ('parent_clause_tag', lambda n: _gattr(n.parent_clause, 'tag')),
    #'function_tag', # not annotated in conll2012

    # nature
    'is_clause',
    'is_phrase',
    ('is_word', lambda n: n.is_leaf),
    ('pspeech', lambda n: n.pspeech if n.is_leaf else None),

    # for relations
    ('parent_phrase_id', lambda n: _gattr(n.parent_phrase, 'id_')),
    ('parent_clause_id', lambda n: _gattr(n.parent_clause, 'id_')),

    # preposition
    ('in_pp', lambda n: bool(n.pp)),
    ('preposition', lambda n: _gattr(_gattr(n.pp, 'preposition'), 'lemma')),

    # position
    'node_depth',
    'clause_depth',
    'phrase_depth',
    'is_in_main_clause',
    'is_in_matrix',
    'is_embedded',
    'is_in_embedded',

    # dependent
    'dependent_count',
    'predependent_count',
    'postdependent_count',
    'adjective_dependent_counter',
    'noun_dependent_counter',
    'clause_dependent_counter',
    'phrase_dependent_counter',
    'other_dependent_counter',

    # determiner
    ('determiner_string', lambda n: n.determiner_string.lower()),
    ('determiner_head_string', lambda n: n.determiner_head_string.lower()),
    'determiner_type',
    'has_bare_determiner',
    'has_genetive_determiner',
    'has_complex_determiner',
    'is_possessive',
    'is_genitive',

    # head
    ('head', lambda n: _gattr(n.head, 'string')),
    ('h_pspeech', lambda n: _gattr(n.head, 'tag')),
    ('h_ud_pspeech', lambda n: _gattr(n.head, 'ud_pspeech')),
    ('h_broad_pspeech', lambda n: _gattr(n.head, 'broad_pspeech')),
    ('h_noun_type', lambda n: _gattr(n.head, 'noun_type')),
    ('h_number', lambda n: {"True":"p", "False":"s", "None":None} \
        [str(_gattr(n.head, 'is_plural_noun'))]),
    ('h_lemma', lambda n: _gattr(n.head, 'lemma')),
    ('h_node_depth', lambda n: _gattr(n.head, 'node_depth')),
    ('h_start', lambda n: _gattr(n.head, 'start')),
    ('h_stop', lambda n: _gattr(n.head, 'stop')),
    ('h_text_start', lambda n: _gattr(n.head, 'text_start')),
    ('h_text_stop', lambda n: _gattr(n.head, 'text_stop')),

)

_NODE_ATTRIBUTE_LIST = [
    x if isinstance(x, str) else x[0] for x in _NODE_ATTRIBUTES
]

_NODE_ATTRIBUTES_FOR_RELATIONS = (
    'descendant_list',
    'phrase_descendant_list',
    'clause_descendant_list',
)


def extract_syntax_tree(outfpath, outfpath_for_relations, *infpaths,
        key_callback=None, head_pos_cache=None):

    print("- extracting syntax tree")

    heads = load_cache(head_pos_cache) if head_pos_cache else None

    data = dict()
    data_for_relations = dict()
    for doc in conll.read_files(*infpaths, key_callback=key_callback):

        print("... from %s" % doc.key)
        data[doc.key] = dict()
        data_for_relations[doc.key] = dict()

        for sent in doc.sentences:

            # cols
            word_col = list(sent.iter_tokens(3))
            pspeech_col = list(sent.iter_tokens(4))
            tree_col = list(sent.iter_tokens(5))
            lemma_col = list(sent.iter_tokens(6))

            # prepare
            tree_string = "\n".join(tree_col).replace('*', ' *') 
            lemma_col = [
                l
                if (l and l != '-') else w
                for w, l in zip(word_col, lemma_col)
            ]

            # parse
            parser = TreeParser(
                tree_string,
                list(zip(pspeech_col, word_col, lemma_col)),
            )
            parser.parse()

            # put text_start|stop in ALL node before processing
            for node in parser.node_list:
                node.text_start = node.start + sent.first_token_index
                node.text_stop = node.stop + sent.first_token_index

            if heads:
                pos2nodes = {
                    (node.text_start, node.text_stop): node
                    for node in parser.node_list
                }
                doc_heads = heads[doc.key]
                for node in parser.node_list:
                    pos = (node.text_start, node.text_stop)
                    if pos in doc_heads:
                        pos = (doc_heads[pos], doc_heads[pos]+1)
                        node.set_head(pos2nodes[pos])
                        print("Found!")
                    else:
                        print("WARNING: head not found")

            for node in parser.node_list:
                start = node.start + sent.first_token_index
                stop = node.stop + sent.first_token_index
                # take the most nested element (so overwrite), except if it is
                # a leaf:
                if node.is_leaf and (start, stop) in data[doc.key]:
                    continue
                data[doc.key][(start, stop)] = []
                for attr in _NODE_ATTRIBUTES:
                    if not isinstance(attr, str):
                        attr = attr[1](node)
                    else:
                        attr = getattr(node, attr)
                    data[doc.key][(start, stop)].append(attr)
                data_for_relations[doc.key][(start, stop)] = []
                for attr in _NODE_ATTRIBUTES_FOR_RELATIONS:
                    attr = getattr(node, attr)
                    data_for_relations[doc.key][(start, stop)].append(attr)

    save_cache(outfpath, data)
    save_cache(outfpath_for_relations, data_for_relations)




def annotate_syntax_tree(mentions, fpath):
    print("- syntax tree")
    dic = load_cache(fpath)
    length = len(_NODE_ATTRIBUTES)
    df = pd.DataFrame(
        data=(
            get_list_value(dic, text, start, stop, length)
            for text, start, stop in zip(
                mentions['text_id'],
                mentions['text_start'],
                mentions['text_stop'],
            )
        ),
        columns=[
            attr if isinstance(attr, str) else attr[0]
            for attr in _NODE_ATTRIBUTES
        ],
        index=mentions.index,
    )
    return pd.concat([mentions, df], axis=1)



def add_other_annotations(db):

    print("- other annotations")
    #db['texts']['genre'] = [x[0:2] for x in db['texts'].index]
    db['texts']['source'] = [x[2:x.index('_')] for x in db['texts'].index]


def add_token_pos(db, *infpaths):

    print("- token part of speech")

    tokens = db['tokens']
    groupped = tokens.groupby('text_id')

    dic = dict()
    for doc in conll.read_files(*infpaths):
        df = groupped.get_group(doc.key)
        df = df.sort_index()
        tks = [ t for sent in doc.sentences for t in sent.iter_tokens(4) ]
        assert len(df.index) == len(tks)
        d = dict(zip(df.index, tks))
        dic.update(d)

        #for sent in doc.sentences:
        #    pspeech_col = list(sent.iter_tokens(4))

    tokens['pos'] = [ dic[index] for index in tokens.index ]


def build_cache_conll2012(*infpaths, cache_dir, inventories2wordnet_fpath):

    if not os.path.exists(cache_dir):
        os.mkdir(cache_dir)

    extract_named_entities(
        os.path.join(cache_dir, 'ne'),
        *infpaths,
    )

    extract_speakers(
        os.path.join(cache_dir, 'spk'),
        *infpaths,
    )

    extract_syntax_tree(
        os.path.join(cache_dir, 'tree'),
        os.path.join(cache_dir, 'tree_rel'),
        *infpaths,
        #head_pos_cache=None,
    )

    extract_argument_structures(
        os.path.join(cache_dir, 'struct'),
        *infpaths,
    )

    extract_wordnet_synsets(
        *infpaths,
        outfpath=os.path.join(cache_dir, 'wordnet'),
        inventories2wordnet_fpath=inventories2wordnet_fpath,
        syntax_cache_fpath=os.path.join(cache_dir, "tree"),
    )



def add_conll2012_specific_annotations(db, cache_dir, *infpaths):

    #print("... named entities")
    # in place
    annotate_name_entities(
        db['mentions'],
        fpath=os.path.join(cache_dir, 'ne'))

    #print("... speaker")
    # in place
    annotate_speakers(
        db['mentions'],
        fpath=os.path.join(cache_dir, 'spk'))

    #print("... syntax")
    db['mentions'] = annotate_syntax_tree(
        db['mentions'],
        fpath=os.path.join(cache_dir, 'tree'),
    )

    #print("... argument structure")
    db['mentions'] = annotate_argument_structures(
        db['mentions'],
        fpath=os.path.join(cache_dir, 'struct'),
    )

    #print("... wordnet")
    db['mentions'] = annotate_wordnet_synsets(
        db['mentions'],
        fpath=os.path.join(cache_dir, 'wordnet'),
        merge_official_and_guessed=False,
    )

    #print("Adding other informations...")
    add_other_annotations(db)

    add_token_pos(db, *infpaths)

    return db


