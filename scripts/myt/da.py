from collections import Counter
import statistics

def get_ngrams(data, n=3, every=0, count=False):
    """Compute n-grams in data.  And return Counter object.

    Parameters:
    -----------
    every: int (default 0)
        If not zero, cut the input data at `every` items and return a Counter
        for each piece.
    count: bool (default False)
        Return the number of unique n-grams, or the mean for each piece if
        `every` is True.
    """

    if not every:
        every = len(data)

    points = []

    for d in (data[i:i+every] for i in range(0, len(data), every)):
        if len(d) < n:
            continue
        gen = (tuple(d[j:j+n]) for j in range(min(every, len(d))-n+1))
        if count:
            points.append(len(Counter(gen)))
        else:
            points.append(Counter(gen))

    if count:
        if len(points) == 0:
            return None
        if len(points) == 1:
            return points[0]
        return statistics.mean(points)

    if len(points) == 0:
        return None
    if len(points) == 1:
        return points[0]
    return points


def get_yules(tokens):
    """ 
    Returns a tuple with Yule's K and Yule's I.

    (cf. Oakes, M.P. 1998. Statistics for Corpus Linguistics: 204, and
    Turenne N 2016. Analyse de données textuelles sous R: 48)

    Source of the code:
    https://gist.github.com/magnusnissel/d9521cb78b9ae0b2c7d6

    I checked with the original formula by Yule 1944: 53 (The Statistical study
    of Literary Vocabulary).

    See also:
    https://swizec.com/blog/measuring-vocabulary-richness-with-python/swizec/2528 
    """

    # adapted from the source code:
    token_counter = Counter(tok.upper() for tok in tokens)
    m1 = sum(token_counter.values())
    m2 = sum([freq ** 2 for freq in token_counter.values()])
    if not m2 - m1:
        return (0, None) # all words are different
    i1 = (m1*m1) / (m2-m1)
    k1 = 1/i1 * 10000
    return (k1, i1) # comment if you want to check below

    # from Yule's book:
    #s1 = len(tokens)
    #token_counter = Counter(tok.lower() for tok in tokens)
    #freq_counter = Counter(token_counter.values())
    #s2 = sum([fx*X**2 for X, fx in freq_counter.items()])
    #i2 = (m1*m1) / (m2-m1)
    #k2 = 10000 * (s2 - s1) / (s1**2)

    #print(i1, i2, k1, k2)
    ##input('foo')
    #assert int(i1) == int(i2)
    #assert int(k1) == int(k2)
    #return (k2, i2)

