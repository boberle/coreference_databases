import math
import statistics
import itertools

import scipy.special


##### helpers ##########################################################


def _reset_text_mention_index(m):
    m = m.sort_values('text_mention_index')
    m['text_mention_index'] = list(range(len(m)))
    return m



##### Lafon's burst ####################################################


def lafon_burst_coeff(f, T, obs):
    esp = ( (T-f)*(T-f-1) ) / ( f * (f+1) )
    var = ( esp * T * (T+1) * (f-1) ) / ( f * (f+1) * (f+2) * (f+3) )
    try:
        Z = (obs - esp) / math.sqrt(var)
    except ZeroDivisionError:
        return None
    return Z



def compute_median_mean_diff(m, sort=False, reset_mention_index=True,
        include_round_distance=True):
    if reset_mention_index:
        m = _reset_text_mention_index(m)
    res = dict()
    T = len(m)
    for group, df in m.groupby('chain_id'):
        positions = sorted(df['text_mention_index'].tolist())
        distances = [
            positions[x] - positions[x-1]
            for x in range(1, len(positions))
        ]
        if include_round_distance:
            distances.append(positions[0] + T - positions[-1])
        res[group] = abs(statistics.mean(distances)
            - statistics.median(distances))
        if not include_round_distance:
            res[group] = res[group] / (positions[-1]-positions[0])
    if sort:
        return [ x[0] for x in sorted(res.items(), key=lambda x: x[1],
            reverse=True) ]
    return res




def compute_lafon_burst_coeff(m, sort=False, reset_mention_index=True):
    """Compute Lafon's burst coefficient for the mentions `m`.

    If `sort` is `False`, return a dictionary of the form
    `{ chain_id: coeff, ... }`.  Otherwise, return a list of chain ids in
    reverse order of the coefficient value.

    `m` is a dataframe containing at least two columns: `chain_id` and
    `text_mention_index`.

    All the mentions in `m` are assumed to belong to the same text.
    """

    if reset_mention_index:
        m = _reset_text_mention_index(m)
    res = dict()
    T = len(m)
    for group, df in m.groupby('chain_id'):
        obs = compute_obs_for_lafon_burst_coeff(
            T=T,
            positions=df['text_mention_index'].tolist())
        burst = lafon_burst_coeff(f=len(df), T=T, obs=obs)
        res[group] = burst
    if sort:
        return [ x[0] for x in sorted(res.items(), key=lambda x: x[1],
            reverse=True) ]
    return res



def compute_obs_for_lafon_burst_coeff(T, positions):
    """Compute the observed values for `lafon_burst_coeff()`.

    Positions are the positions (index) of the mentions in the text.
    """

    positions = sorted(positions)
    distances = [
        positions[x] - positions[x-1]
        for x in range(1, len(positions))
    ]
    distances.append(positions[0] + T - positions[-1])
    f = len(positions)
    obs = sum([x*(x-1)/2 for x in distances]) / f
    return obs

 

def _check_lafon_bursts():
    """Test function.  Data are taken from and compare to Lafon's 1984 book.
    """

    #print(lafon_burst_coeff(f=38, T=8274, obs=134540))

    T = 8274
    positions = [
        852, 1484, 1624, 3216, 3510, 3868, 4403, 5350, 5960, 6194, 7144, 7650
    ]
    #distances = [
    #    positions[x] - positions[x-1]
    #    for x in range(1, len(positions))
    #]
    #distances.append(positions[0] + T - positions[-1])
    #print(distances)
    #obs = sum([x*(x-1)/2 for x in distances]) / f
    obs = compute_obs_for_lafon_burst_coeff(T=T, positions=positions)

    f = 12
    print(obs)
    print(lafon_burst_coeff(f=f, T=T, obs=obs))



##### Lafon's entanglement #############################################



def lafon_entanglement_coeff(f, g, k):
    prob_entanglement = 0
    for i in range(k, min(f, g)+1):
        p = scipy.special.comb(f, i) * scipy.special.comb(g, i) / \
            scipy.special.comb(f+g, f)
        #return p
        prob_entanglement += p
    return prob_entanglement



def lafon_entanglement_distance(f, g, k, T, obs):
    u = f + g
    esp = (T-u) / (u+1)
    var = ( (T-u)*(u+1-k)*(T+1) ) / ( (u+1)*k*(u+1)*(u+2) )
    Z = (obs - esp) / math.sqrt(var)
    return Z



def compute_lafon_entanglement_coeff(m):
    """Compute Lafon's entanglement coefficient for the mentions `m`.

    `m` is a dataframe containing at least two columns: `chain_id` and
    `text_start` (index of the token where the mention is starting).

    All the mentions in `m` are assumed to belong to the same text.
    """

    m = _reset_text_mention_index(m)
    T = len(m)
    chains = m['chain_id'].unique()
    res = dict()
    not_entangled = set()
    for c1, c2 in itertools.product(chains, chains):
        if c1 == c2:
            continue
        #if c1 not in (35, 575):
        #    continue
        #if c2 not in (35, 575):
        #    continue
        m_ = m[(m["chain_id"]==c1) | (m["chain_id"]==c2)]
        f = len(m_[m_["chain_id"]==c1])
        g = len(m_) - f
        fg_pairs = 0
        mean = []
        for i in range(len(m_)-1):
            if m_.iloc[i]['chain_id'] == c1 and m_.iloc[i+1]['chain_id'] == c2:
                fg_pairs += 1
                mean.append(m_.iloc[i+1]['text_start']
                    - m_.iloc[i]['text_start'])
        # we reject when no pair (means is 0 and division by 0 error) but also
        # when pair is 1, because this mean that the chain follows each other
        # (first F then G, hence a pair fg): this is not entangled
        if fg_pairs < 2:
            not_entangled.add((c1, c2))
        else:
            mean = statistics.mean(mean)
            entanglement = lafon_entanglement_coeff(f, g, fg_pairs)
            distance = lafon_entanglement_distance(f, g, fg_pairs, T, mean)
            assert f+g == len(m_)
            res[(c1, c2)] = entanglement, distance, fg_pairs, f+g-1, mean
        #print(c1, c2, fg_pairs, f, g, f+g, entanglement)
    return res, not_entangled



def _check_lafon_entanglement():
    """Test function.  Data are taken from and compare to Lafon's 1984 book.
    """

    #print(lafon_entanglement_coeff(8, 22, 2))
    import statistics
    #mean = statistics.mean((85, 768, 32, 19, 488, 316, 22))
    mean = statistics.mean((4, 1, 39, 1, 1, 1, 1, 1))
    print(mean)
    print(lafon_entanglement_distance(8, 22, 7, 8274, mean))
    print(lafon_entanglement_distance(8, 22, 8, 8274, mean))



##### main() ###########################################################


if __name__ == "__main__":
    _check_lafon_bursts()
    #_check_lafon_entanglement()
