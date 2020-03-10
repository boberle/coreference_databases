from collections import Counter

import pandas as pd
import numpy as np

import corefdb
from corefdb.op import batch, operation
import myt



def correct_broad_pspeech(db):

    db['mentions']['h_broad_pspeech'] = db['mentions']['h_broad_pspeech'].apply(
        lambda x: x if x and (x in 'npdv') else 'o'
    )



def _add_stability_coeff_10(db, col):
    def func(ser, every=5):
        points = [
            1 - (ser[i:i+every].nunique()-1) / (every-1)
            for i in range(0, len(ser), every)
            if i + every < len(ser)
        ]
        if points:
            return statistics.mean(points)
        return None
    corefdb.op.compute_annotations(
        src=db['mentions'][db['mentions']['h_broad_pspeech']=='n'],
        src_col=col,
        dest=db['chains'],
        dest_col=f'stability_coeff_10_{col}',
        groupby='chain_id',
        func=lambda ser: func(ser, every=5),
        min_len=2,
    )



def _add_stability_coeff(db, col):
    def func(ser):
        l = len(ser)
        if l:
            return 1 - (ser.nunique()-1) / (l-1)
        return None
    corefdb.op.compute_annotations(
        src=db['mentions'][db['mentions']['h_broad_pspeech']=='n'],
        src_col=col,
        dest=db['chains'],
        dest_col=f'stability_coeff_{col}',
        groupby='chain_id',
        func=lambda ser: func(ser),
        min_len=2,
    )

def _add_pattern_diversity(db):

    def func(ser, every=10):
        if len(ser) < every:
            return None
        return myt.da.get_ngrams(
            ser, n=3, every=every, count=True) / len(ser)
    corefdb.op.compute_annotations(
        src=db['mentions'],
        src_col='h_broad_pspeech',
        dest=db['chains'],
        dest_col='pattern_diversity',
        groupby='chain_id',
        func=lambda ser: func(ser, every=10),
    )



def _add_chain_type(chains, mentions):

    chain2ner = dict()

    for chain_id, ner in zip(mentions['chain_id'], mentions['named_entity_type']):
        if pd.isnull(ner):
            continue
        if not chain_id in chain2ner:
            chain2ner[chain_id] = list()
        chain2ner[chain_id].append(ner)

    counter = 0
    for lst in chain2ner.values():
        if len(set(lst)) != 1:
            counter += 1

    for key in chain2ner.keys():
        ner = Counter(chain2ner[key]).most_common(1)[0][0]
        chain2ner[key] = ner

    chains['type'] = [
        chain2ner[index] if index in chain2ner else np.nan
        for index in chains.index
    ]



def _chain_has_multiple_speakers(chains, mentions):

    chain2spk = dict()

    for chain_id, spk in zip(mentions['chain_id'], mentions['speaker']):
        if not chain_id in chain2spk:
            chain2spk[chain_id] = set()
        chain2spk[chain_id].add(spk)

    chains['has_multiple_speakers'] = [
        len(chain2spk[index]) > 1 for index in chains.index
    ]



def _chain_is_plural(chains, mentions):
    chain2plural = dict()
    for chain_id, plural in zip(mentions['chain_id'], mentions['h_number']):
        if not chain_id in chain2plural:
            chain2plural[chain_id] = False
        chain2plural[chain_id] = \
            chain2plural[chain_id] or plural in ("p", "Plur")

    chains['is_plural'] = [ chain2plural[index] for index in chains.index ]




def add_annotations(db):

    # === chains ===

    #print("Chain annotation: stability")
    _add_stability_coeff(db, col='string')
    _add_stability_coeff(db, col='h_lemma')
    _add_pattern_diversity(db)
    _add_chain_type(chains=db['chains'], mentions=db['mentions'])
    _chain_has_multiple_speakers(chains=db['chains'], mentions=db['mentions'])
    _chain_is_plural(chains=db['chains'], mentions=db['mentions'])

    if 'is_subject' in db['mentions'].columns:
        db = batch(db,
            "psplit mentions.is_subject to chains.proportion_of_subjects keep True",
        )

    db = batch(db,
        "psplit mentions.is_named_entity        to chains.proportion_of_named_entities keep True",
        "psplit mentions.in_pp                  to chains.proportion_of_mentions_in_pp keep True",
        "psplit mentions.is_in_main_clause      to chains.proportion_of_mentions_in_main_clause keep True",
        "psplit mentions.h_broad_pspeech        to chains.proportion_of_",
        "mean mentions.node_depth               to chains.mean_node_depth",
    )

    db['chains'].rename(
        lambda x: x[:-5] if x.endswith('_True') else x,
        inplace=True,
        axis=1)

    mentions = db['mentions']
    chains = db['chains']

    # proportion of proper nouns

    dic = dict()
    for chain_id, noun_type in \
            zip(mentions['chain_id'], mentions['h_noun_type']):
        if chain_id not in dic:
            dic[chain_id] = dict(p=0, c=0)
        dic[chain_id]['p' if noun_type == "pnoun" else 'c'] += 1
    for chain_id in dic.keys():
        total = sum(dic[chain_id].values())
        if total:
            dic[chain_id] = dic[chain_id]['p'] / total
        else:
            dic[chain_id] = 0
    chains['proportion_of_proper_nouns'] = [
        dic[chain_id] for chain_id in chains.index
    ]

    # proportions of first arguments:

    dic = dict()
    for chain_id, arg in \
            zip(mentions['chain_id'], mentions['arg_index']):
        if chain_id not in dic:
            dic[chain_id] = dict(first=0, other=0)
        dic[chain_id]['first' if arg == 0 else 'other'] += 1
    for chain_id in dic.keys():
        total = sum(dic[chain_id].values())
        if total:
            dic[chain_id] = dic[chain_id]['first'] / total
        else:
            dic[chain_id] = 0
    chains['proportion_of_first_arguments'] = [
        dic[chain_id] for chain_id in chains.index
    ]

    # proportions of nouns with dependents:

    dic = dict()
    for chain_id, dep_count, pos in \
            zip(mentions['chain_id'], mentions['dependent_count'],
            mentions['h_broad_pspeech']):
        if chain_id not in dic:
            dic[chain_id] = dict(has_dep=0, has_no_dep=0)
        if pos != "n":
            continue
        dic[chain_id]['has_dep' if dep_count else 'has_no_dep'] += 1
    for chain_id in dic.keys():
        total = sum(dic[chain_id].values())
        if total:
            dic[chain_id] = dic[chain_id]['has_dep'] / total
        else:
            dic[chain_id] = 0
    chains['proportion_of_nouns_with_dependents'] = [
        dic[chain_id] for chain_id in chains.index
    ]

    return db



def add_copies(db):

    #print("Adding copy annotations...")

    db = batch(db,
        "copy texts.genre                to chains.text_genre",
        "copy texts.genre                to mentions.text_genre",
        "copy chains.type                to mentions.chain_type",
    )

    if 'source' in db['texts'].columns:
        db = batch(db,
            "copy texts.source           to chains.text_source",
            "copy texts.source           to mentions.text_source",
        )

    return db




def add_relation_copies(db):

    #print("Adding copy annotations for relations...")

    db = batch(db,
        "copy texts.genre                to relations.text_genre",
        "copy chains.type                to relations.chain_type",
    )

    if 'source' in db['texts'].columns:
        db = batch(db,
            "copy texts.source           to relations.text_source",
        )

    return db



def add_relation_annotations(db):

    # relation type

    mention2broad_pspeech = db['mentions']["h_broad_pspeech"].to_dict()

    print("Relation annotation: type...")
    db['relations']['type'] = [
        f"{str(mention2broad_pspeech[m1])}_{str(mention2broad_pspeech[m2])}"
        for _, (m1, m2) in db['relations'][['m1_id', 'm2_id']].iterrows()
    ]

    return db





def run_all(db):

    correct_broad_pspeech(db)
    db = add_relation_annotations(db)
    db = add_annotations(db)
    db = add_copies(db)

    return db


"""
DEBUG CODE FOR add_relation_type()


mentions = pd.DataFrame(
    #data=list("nddpddppdnpdpn"),
    data=list("dnpddnppddpnnp"),
    columns=["h_broad_pspeech"],
)

mentions['text_id'] = 't1'

mentions['text_mention_index'] = [i for i in range(len(mentions))]

relations = pd.DataFrame(
    data=list(itertools.product(mentions.index, mentions.index)),
    columns=["m1_id", "m2_id"],
)

relations['text_id'] = 't1'

relations['type'] = [
    "%s-%s" % (mentions.at[m1, 'h_broad_pspeech'], mentions.at[m2, 'h_broad_pspeech'])
    for _, (m1, m2) in relations[['m1_id', 'm2_id']].iterrows()
]

add_npd_relations(mentions, relations)

print(relations)
relations.to_csv('/tmp/relations.csv')
"""

