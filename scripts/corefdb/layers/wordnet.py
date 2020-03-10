import pandas as pd

import nltk
from nltk.corpus import wordnet as wn

from coreftools.cache import PairDictCache


class SynsetCache:

    def __init__(self, lang='eng', max_senses=None):
        self.data = dict()
        self.lang = lang
        self.max_senses = max_senses

    def __getitem__(self, key):
        # key = (lemma|synset_name, pos)
        if key is None:
            return []
        if not key[1] or pd.isnull(key[1]):
            return []
        if key[1] and key[1] not in "arvn":
            return []
        if key not in self.data:
            if key[0].count('.') == 2:
                # ValueError or KeyError
                try:
                    self.data[key] = [wn.synset(key[0])]
                except (ValueError, KeyError):
                    # errors like "www.foo.com"
                    #print(f"can't find {key[0]} in synset")
                    self.data[key] = []
            else:
                self.data[key] = wn.synsets(key[0], pos=key[1], lang=self.lang)
                if self.max_senses:
                    self.data[key] = self.data[key][:self.max_senses]
        return self.data[key]



def add_mention_annotations(db, cache_dir=None):

    raise NotImplementedError("not enough noun have a synset for that")

    # TODO: if 'wn_lexname' in annotations or not annotations:
    # TODO:     print("Mention annotation: wn lexname...")
    # TODO:     fill_out(db, 'synset')
    # TODO:     db['mentions']['wn_lexname'] = db['mentions']['wn'].apply(
    # TODO:         lambda x: wn.synset(x).lexname()
    # TODO:             if not pd.isnull(x) else None
    # TODO:     )
    # TODO: return db





def add_relation_annotations(db, lemma_col, pos_col, wn_col=None,
        cache_dir=None, lang='eng', max_senses=5, annotations=None):
    """Add WordNet related annotations to the `db['relations']` df.

    TODO

    Parameters:
    -----------
    max_senses: int (def 5)
        Use only the first `max_senses` sense for each word.

    Note:
    -----

    Use `max_sense` to limit the number of synsets for highly polysemic words.

    For example, French words "homme" and "chat" are related hyperonyms in some
    derived senses.  Run this:

        import nltk
        from nltk.corpus import wordnet as wn
        hommes = wn.synsets('homme', lang='fra')
        hommes
        chats = wn.synsets('chat', lang='fra')
        chats
        for i, homme in enumerate(hommes):
            for hypernym in list(homme.closure(rel=lambda x: x.hyponyms())):
                #print(hypernym)
                for j, chat in enumerate(chats):
                    if chat == hypernym:
                        print(hypernym)
                        for lemma in chat.lemma_names('fra'):
                            print(lemma)
                        #print(homme.shortest_path_distance(chat))
                        print(i, j)

    This assumes that the synsets are ordered by order of "importance".

    """

    mentions = db['mentions']
    relations = db['relations']

    synsets = SynsetCache(lang=lang, max_senses=max_senses)
    assert lemma_col
    if wn_col:
        mention2wn = {
            id_: (wn, pos) if not pd.isnull(wn)
                else (word, pos) if not pd.isnull(word) else None
            for id_, (wn, word, pos)
                in mentions[[wn_col, lemma_col, pos_col]].iterrows()
        }
    else:
        mention2wn = {
            id_: (word, pos) if not pd.isnull(word) else None
            for id_, (word, pos) in mentions[[lemma_col, pos_col]].iterrows()
        }
    #input(mention2wn)


    ## distance ##

    print("Relation annotation: wordnet distances and similarities...")

    def compute_min_max(attr, synsets1, synsets2):
        values = list(filter(lambda x: x is not None, [
            getattr(s1, attr)(s2)
            for s1 in synsets1
                for s2 in synsets2
                    if s1.pos() == s2.pos()
        ]))
        return (
            min(values) if values else None,
            max(values) if values else None,
        )

    for attr in ('wup_similarity', 'path_similarity', 'shortest_path_distance',
            #'lch_similarity',
            ):

        if annotations and not attr in annotations:
            continue

        print("... %s" % attr)

        cache = PairDictCache(name=attr, dpath=cache_dir)

        def func(m1_id, m2_id):
            f = lambda m1, m2: \
                    compute_min_max(
                        attr, synsets[mention2wn[m1]], synsets[mention2wn[m2]])
            return cache[m1_id, m2_id, f]

        cols = [
            func(m1, m2)
            for _, (m1, m2) in relations[['m1_id','m2_id']].iterrows()
        ]
        relations[f"min_{attr}"] = [x[0] for x in cols]
        relations[f"max_{attr}"] = [x[1] for x in cols]

        cache.save()


    ## hypernyms ##

    if not annotations or 'hypernymy' in annotations:

        print("Relation annotation: wordnet hypernyms...")

        cache = PairDictCache(name="hypernyms", dpath=cache_dir)

        hyper_cache = dict()

        def compute_hypernymy(synsets1, synsets2):
            if not (synsets1 and synsets2):
                return False
            for s1 in synsets1:
                if s1.name() not in hyper_cache:
                    hyper_cache[s1.name()] = \
                        list(s1.closure(rel=lambda x: x.hypernyms())) \
                        + list(s1.closure(rel=lambda x: x.hyponyms()))
                related = hyper_cache[s1.name()]
                for s2 in synsets2:
                    if s1.pos() == s2.pos() and s2 in related:
                        return True
            return False

        def func(m1_id, m2_id):
            # NOTE: is it necessary to compute both ways?
            f = lambda m1, m2: \
                    (compute_hypernymy(
                        synsets[mention2wn[m1]], synsets[mention2wn[m2]])
                    or compute_hypernymy(
                        synsets[mention2wn[m2]], synsets[mention2wn[m1]])
                    )
            return cache[m1_id, m2_id, f]

        relations['hypernymy'] = [
            func(m1, m2)
            for _, (m1, m2) in db['relations'][['m1_id','m2_id']].iterrows()
        ]

        del hyper_cache

        cache.save()


    ## meronyms ##

    if not annotations or 'meronymy' in annotations:

        print("Relation annotation: meronymy...")

        cache = PairDictCache(name="meronyms", dpath=cache_dir)

        mero_cache = dict()

        def compute_meronymy(synsets1, synsets2):
            if not (synsets1 and synsets2):
                return False
            for s1 in synsets1:
                if s1.name() not in mero_cache:
                    mero_cache[s1.name()] = \
                        s1.part_meronyms() + s1.substance_meronyms()
                related = mero_cache[s1.name()]
                for s2 in synsets2:
                    if s1.pos() == s2.pos() and s2 in related:
                        return True
            return False

        def func(m1_id, m2_id):
            f = lambda m1, m2: \
                    (compute_meronymy(
                        synsets[mention2wn[m1]], synsets[mention2wn[m2]])
                    or compute_meronymy(
                        synsets[mention2wn[m2]], synsets[mention2wn[m1]])
                    )
            return cache[m1_id, m2_id, f]

        relations['meronymy'] = [
            func(m1, m2)
            for _, (m1, m2) in db['relations'][['m1_id','m2_id']].iterrows()
        ]

        del mero_cache

        cache.save()

        return db




########################################################################

#class LexCache:
#
#    def __init__(self, fpath=None):
#        self.fpath = fpath
#        self.synsets = dict()
#        self.lexnames = dict()
#        self.dist = dict()
#        self.wndist = dict()
#        self.saved = False
#        if self.fpath:
#            self.load()
#
#    def __getitem__(self, key):
#        if pd.isnull(key):
#            return None
#        if key not in self.synsets:
#            self.synsets[key] = wn.synset(key)
#        return self.synsets[key]
#
#    def load(self):
#        if os.path.exists(self.fpath):
#            data = json.load(open(self.fpath))
#            self.lexnames = data['lexnames']
#            self.dist = { (a, b): val for a, b, val in data['dist'] }
#            self.wndist = { (a, b): val for a, b, val in data['wndist'] }
#            #self.docs = {
#            #    doc_key: { (start, stop): val for start, stop, val in values }
#            #    for doc_key, values in data['docs'].items()
#            #}
#
#    def save(self):
#        if self.fpath:
#            json.dump(dict(
#                lexnames=self.lexnames,
#                dist=[ [a, b, val] for (a, b), val in self.dist.items() ],
#                wndist=[ [a, b, val] for (a, b), val in self.wndist.items() ],
#                #docs={
#                #    doc_key: [
#                #        [start, stop, val] for (start, stop), val in data.items()
#                #    ]
#                #    for doc, data in self.docs.items()
#                #},
#            ), open(self.fpath, 'w'))
#        self.saved = True
#
#    def get_lexname(self, key):
#        if key not in self.lexnames:
#            synset = self[key]
#            if pd.isnull(key):
#                key = None
#            self.lexnames[key] = synset.lexname() if synset else None
#        return self.lexnames[key]
#
#    def get_dist(self, a, b, kind):
#        if not (a, b) in self.dist and not (b, a) in self.dist:
#            self.dist[(a, b)] = [
#                td.levenshtein.normalized_distance(a, b),
#                td.sorensen_dice.normalized_distance(a.split(), b.split()),
#            ]
#        res = self.dist[(a, b)] if (a, b) in self.dist else self.dist[(b, a)]
#        return res[{
#            'levenshtein':0,
#            'sorensen_dice':1
#        }[kind]]
#
#    def _get_meronymy(self, a, b):
#        for attr in ('part_meronyms', 'substance_meronyms'):
#            if bool(sum([int(s==a) for s in getattr(b, attr)()])) \
#                    or \
#                    bool(sum([int(s==b) for s in getattr(a, attr)()])):
#                return true
#        return False
#
#    def get_wndist(self, a, b, kind):
#        if not (a, b) in self.wndist and not (b, a) in self.wndist:
#            a_syn = self[a]
#            b_syn = self[b]
#            if not a_syn or not b_syn:
#                if pd.isnull(a):
#                    a = None
#                if pd.isnull(b):
#                    b = None
#                self.wndist[(a, b)] = None
#            else:
#                self.wndist[(a, b)] = [
#                    a_syn.shortest_path_distance(b_syn),
#                    a_syn.lch_similarity(b_syn)
#                        if a_syn.pos() == b_syn.pos() else None,
#                    a_syn.wup_similarity(b_syn),
#                    a_syn.path_similarity(b_syn),
#                    self._get_meronymy(a_syn, b_syn)
#                ]
#        res = self.wndist[(a, b)] \
#            if (a, b) in self.wndist else self.wndist[(b, a)]
#        if res is not None:
#            return res[{
#                'shortest_path_distance':0,
#                'lch_similarity':1,
#                'wup_similarity':2,
#                'path_similarity':3,
#                'meronymy':4,
#            }[kind]]





