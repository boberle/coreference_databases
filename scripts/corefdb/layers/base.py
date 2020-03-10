import numpy as np
import scipy

import corefdb
from corefdb.op import batch, operation
from . import base_helpers

import myt

def add_annotations(db):

    #print("Adding base annotations...")

    mentions = db['mentions']

    # === mentions ===

    #print("... mentions")

    mentions['token_count'] = [
        stop - start
        for start, stop in zip(mentions['start'], mentions['stop'])
    ]


    # === chains ===

    #print("... chains")

    db = batch(db,

        "count mentions.chain_id    to chains.size",

        "mean mentions.level        to chains.mean_mention_level",

        "psplit mentions.is_outer   to chains.outer_proportion keep True",

        "mean mentions.par_mention_rank     to chains.mean_par_mention_rank",
        "mean mentions.sent_mention_rank    to chains.mean_sent_mention_rank",
        "mean mentions.text_mention_rank    to chains.mean_text_mention_rank",

        "median mentions.par_mention_rank     to chains.median_par_mention_rank",
        "median mentions.sent_mention_rank    to chains.median_sent_mention_rank",
        "median mentions.text_mention_rank    to chains.median_text_mention_rank",

        "mean relations.token_dist      to chains.mean_token_dist",
        "mean relations.mention_dist    to chains.mean_mention_dist",
        "mean relations.sent_dist       to chains.mean_sent_dist",
        "mean relations.par_dist        to chains.mean_par_dist",

        "median relations.token_dist      to chains.median_token_dist",
        "median relations.mention_dist    to chains.median_mention_dist",
        "median relations.sent_dist       to chains.median_sent_dist",
        "median relations.par_dist        to chains.median_par_dist",

    )

    db['chains'].rename(
        dict(outer_proportion_True="outer_proportion"),
        inplace=True,
        errors='raise',
        axis=1)

    corefdb.op.add_distribution1(
        src_df=db['mentions'],
        src_col='token_count',
        groupby='chain_id',
        dest_df=db['chains'],
        dest_col='distribution_of_mention_length_',
    )
    corefdb.op.add_distribution1(
        src_df=db['relations'],
        src_col='token_dist',
        groupby='chain_id',
        dest_df=db['chains'],
        dest_col='distribution_of_token_dist_',
    )
    corefdb.op.add_distribution1(
        src_df=db['relations'],
        src_col='mention_dist',
        groupby='chain_id',
        dest_df=db['chains'],
        dest_col='distribution_of_mention_dist_',
    )
    corefdb.op.add_distribution1(
        src_df=db['relations'],
        src_col='sent_dist',
        groupby='chain_id',
        dest_df=db['chains'],
        dest_col='distribution_of_sent_dist_',
    )
    corefdb.op.add_distribution1(
        src_df=db['relations'],
        src_col='par_dist',
        groupby='chain_id',
        dest_df=db['chains'],
        dest_col='distribution_of_par_dist_',
    )

    base_helpers.add_lafon(db)

    corefdb.op.compute_annotations(
        src=db['relations'][ db['relations']['is_consecutive'] == True ],
        src_col='token_dist',
        dest=db['chains'],
        dest_col='dist_skewness',
        groupby='chain_id',
        func=lambda ser: scipy.stats.skew(ser),
        min_len=5,
    )
        
    corefdb.op.compute_annotations(
        src=db['relations'][ db['relations']['is_consecutive'] == True ],
        src_col='token_dist',
        dest=db['chains'],
        dest_col='dist_kurtosis',
        groupby='chain_id',
        func=lambda ser: scipy.stats.kurtosis(ser),
        min_len=5,
    )

    # === texts ===

    #print("... texts")

    db = batch(db,

        "count tokens.text_id       to texts.token_count",
        "count mentions.text_id     to texts.mention_count",
        "count chains.text_id       to texts.chain_count",
        "count sentences.text_id    to texts.sent_count",
        "count paragraphs.text_id   to texts.par_count",

        "psplit mentions.is_outer   to texts.outer_proportion keep True",
        "mean mentions.level        to texts.mean_mention_level",

        "mean chains.mean_token_dist    to texts.mean_token_dist",
        "mean chains.mean_mention_dist  to texts.mean_mention_dist",
        "mean chains.mean_sent_dist     to texts.mean_sent_dist",
        "mean chains.mean_par_dist      to texts.mean_par_dist",

        "median chains.mean_token_dist    to texts.median_token_dist",
        "median chains.mean_mention_dist  to texts.median_mention_dist",
        "median chains.mean_sent_dist     to texts.median_sent_dist",
        "median chains.mean_par_dist      to texts.median_par_dist",

    )

    db['texts'].rename(
        dict(outer_proportion_True="outer_proportion"),
        inplace=True,
        errors='raise',
        axis=1)

    def _get_genre(x):
        tmp = ""
        for c in x:
            if c.isalnum():
                tmp += c
            if len(tmp) >= 2:
                break
        if len(tmp) >= 2:
            return tmp
        return "ge"
        
    db['texts']['genre'] = [
        _get_genre(x) for x in db['texts'].index
    ]

    corefdb.op.add_distribution1(
        src_df=db['mentions'],
        src_col='token_count',
        groupby='text_id',
        dest_df=db['texts'],
        dest_col='distribution_of_mention_length_',
    )
    corefdb.op.add_distribution1(
        src_df=db['chains'],
        src_col='size',
        groupby='text_id',
        dest_df=db['texts'],
        dest_col='distribution_of_chain_size_',
    )

    base_helpers.add_chain_ngrams(
        mentions=db['mentions'],
        data=db['texts'],
        col_id='text_id',
        n=3,
        every=100
    )

    base_helpers.add_ttr(
        mentions=db['mentions'],
        data=db['texts'],
        col_id='text_id',
        every=100
    )

    corefdb.op.compute_annotations(
        src=db['tokens'],
        src_col='string',
        dest=db['texts'],
        dest_col='yule_s_k',
        groupby='text_id',
        func=lambda ser: myt.da.get_yules(ser)[0]
    )

    corefdb.op.compute_annotations(
        src=db['tokens'],
        src_col='string',
        dest=db['texts'],
        dest_col='yule_s_i',
        groupby='text_id',
        func=lambda ser: myt.da.get_yules(ser)[1]
    )


    # === chain ===

    #print("... chains (again)")

    db['chains'] = operation(
        op='max',
        na=np.nan,
        src=db['relations'],
        dest=db['chains'],
        by='chain_id',
        cols=['token_dist'],
        names=['text_span'],
    )

    text_lengths = db['texts']['token_count'].to_dict()
    db['chains']['text_coverage'] = [
        span / text_lengths[text_id]
        for span, text_id in
            zip(db['chains']['text_span'], db['chains']['text_id'])
    ]


    return db



def add_relation_annotations(db):

    #print("Adding base annotations for relations...")

    comparisons = [
        "sent_id",
        "par_id",
        "string",
        "is_outer",
    ]

    diff = [
        "text_mention_index             mention_dist",
        "text_sent_index                sent_dist",
        "text_par_index                 par_dist",
        "text_start                     token_dist"
    ]

    lambdas = [
        ("chain_mention_index    is_consecutive", lambda m1, m2: m2-m1 == 1),
        ("chain_mention_index    is_to_first", lambda m1, m2: m1 == 0),
    ]

    db["relations"] = corefdb.op.relations.compute_annotations(
        db['mentions'],
        db["relations"],
        comparisons=comparisons,
        differences=diff,
        lambdas=lambdas,
    )

    return db



def add_copies(db):

    #print("Adding copy annotations...")

    db = batch(db,

        # chains

        "copy texts.token_count          to chains.text_token_count",
        "copy texts.mention_count        to chains.text_mention_count",
        "copy texts.chain_count          to chains.text_chain_count",

        # mentions

        "copy texts.token_count          to mentions.text_token_count",
        "copy texts.mention_count        to mentions.text_mention_count",
        "copy texts.chain_count          to mentions.text_chain_count",

        "copy chains.size               to mentions.chain_size",
        "copy chains.text_coverage      to mentions.chain_coverage",
        "copy chains.mean_token_dist    to mentions.chain_mean_token_dist",
        "copy chains.median_token_dist  to mentions.chain_median_token_dist",

    )

    return db



def add_relation_copies(db):

    #print("Adding copy annotations for relations...")

    db = batch(db,

        "copy chains.size               to relations.chain_size",
        "copy chains.text_coverage      to relations.chain_coverage",
        "copy chains.mean_token_dist    to relations.chain_mean_token_dist",
        "copy chains.median_token_dist  to relations.chain_median_token_dist",

        "copy texts.token_count         to relations.text_token_count",
        "copy texts.mention_count       to relations.text_mention_count",
        "copy texts.chain_count         to relations.text_chain_count",
    )

    return db



def run_all(db):

    db = add_relation_annotations(db)
    db = add_annotations(db)
    db = add_copies(db)
    db = add_relation_copies(db)

    return db

