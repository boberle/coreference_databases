import numpy as np
import pandas as pd

import textdistance as td
import corefdb


def add_annotations(db, word_vectors_fpath, wn_lang='eng',
        wn_max_senses=5, wn_col=None):

    mention2string = db['mentions']['string'].to_dict()

    ### levenshtein ###

    print("Adding Levensthein distance...")
    db['relations']['levensthein'] = [
        td.levenshtein.normalized_distance(
            mention2string[m1],
            mention2string[m2]
        )
        for _, (m1, m2) in db['relations'][['m1_id','m2_id']].iterrows()
    ]

    ### sorensen-dice ###

    print("Adding Sorensen-Dice distance...")
    db['relations']['sorensen_dice'] = [
        td.sorensen_dice.normalized_distance(
            mention2string[m1].split(),
            mention2string[m2].split()
        )
        for _, (m1, m2) in db['relations'][['m1_id','m2_id']].iterrows()
    ]

    ### context similarity ###

    print("Adding context similarity...")
    corefdb.layers.context_similarity.set_vector_file(word_vectors_fpath)
    db = corefdb.layers.context_similarity.add_relation_annotations(
        db,
        word_col='head',
        cache_dir=None,
    )

    ### Wordnet ###

    print("Adding wordnet...")

    db = corefdb.layers.wordnet.add_relation_annotations(
        db,
        lemma_col='h_lemma',
        pos_col='h_broad_pspeech',
        wn_col=wn_col if wn_col else None,
        cache_dir=None,
        lang=wn_lang,
        max_senses=wn_max_senses,
    )

    return db



def run_all(db, word_vectors_fpath, wn_lang='eng', wn_max_senses=5,
        wn_col=None):

    db = add_annotations(
        db,
        word_vectors_fpath=word_vectors_fpath,
        wn_lang=wn_lang,
        wn_max_senses=wn_max_senses,
        wn_col=wn_col,
    )

    return db
