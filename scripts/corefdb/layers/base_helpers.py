import statistics

import myt.da
import corefdb
from coreftools.lafon import compute_lafon_burst_coeff

def add_chain_ngrams(mentions, data, col_id='text_id', n=3, every=100):

    def func(ser):
        if len(ser) < every:
            return None
        return myt.da.get_ngrams(ser, n=3, every=every, count=True) / len(ser)

    corefdb.op.compute_annotations(
        src=mentions,
        src_col='chain_id',
        dest=data,
        dest_col='chain_ngrams',
        groupby='text_id',
        func=func,
        sort_col='text_mention_index'
    )


def add_ttr(mentions, data, col_id='text_id', every=100):

    def func(ser):
        points = [
            ser[i:i+every].nunique() / every
            for i in range(0, len(ser), every)
            if i + every < len(ser)
        ]
        if points:
            return statistics.mean(points)
        return None

    corefdb.op.compute_annotations(
        src=mentions,
        src_col='string',
        dest=data,
        dest_col='ttr',
        groupby='text_id',
        func=func,
    )


def add_lafon(db):
    dic = dict()
    for group, df in db['mentions'].groupby('text_id'):
        dic.update(compute_lafon_burst_coeff(df))
    db['chains']['lafon'] = [
        dic.get(id_, None) for id_ in db['chains'].index
    ]

