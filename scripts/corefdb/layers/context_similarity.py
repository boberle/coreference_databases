import pandas as pd
from gensim.models import KeyedVectors

from coreftools.cache import PairDictCache


vectors = None

def set_vector_file(fpath):
    global vectors
    vectors = KeyedVectors.load_word2vec_format(fpath, binary=False)



def add_relation_annotations(db, word_col, cache_dir=None):

    mention2word = db['mentions'][word_col].to_dict()

    #for attr in ('similarity', 'rank'):
    for attr in ('similarity',):

        cache = PairDictCache(name=f'emb_{attr}', dpath=cache_dir)
        def compute(m1_id, m2_id):
            word1 = mention2word[m1_id]
            word2 = mention2word[m2_id]
            if vectors and word1 in vectors and word2 in vectors:
                # float because otherwise can't store np.float32 in json
                return float(getattr(vectors, attr)(word1, word2))
            return None
        db['relations'][f'context_{attr}'] = [
            cache[m1, m2, compute]
            for _, (m1, m2) in db['relations'][['m1_id', 'm2_id']].iterrows()
        ]
        cache.save()

    return db

