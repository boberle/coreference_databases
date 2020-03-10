"""Elements are all related to the first element of the chain.

With {A B C D}: AB, AC, AD

This function assumes that mentions are sorted.  This is done
with `chain.sort()`.
"""
"""Consecutive relations in a chain.

With {A B C D}: AB, BC, CD

This function assumes that mentions are sorted.  This is done
automatically by the `Chain.mentions` attribute.
"""
"""All possible relations in a chain.

With {A B C D}: AB, AC, AD, BC, BD, CD

This function assumes that mentions are sorted.  This is done
automatically by the `Chain.mentions` attribute.
"""


def relations2groups(objs, pairs, *, add_singletons=True):
    """Make sets from relations.

    Return a list of lists of objects.

    Parameters:
    -----------
    objs: list of objets
        Objets to be groupped together.
    pairs: List of iterables of two integers
        List of pairs, each pair being an iterable of two indices for `objs`
    add_singletons: bool (True)
        If True, objects from `objs` not in a relationship are added to the
        returned list of objects as singletons (sets of one elements).

    To test:

        input(relations2groups((
            tuple("AB"),
            tuple("AC"),
            tuple("DE"),
            tuple("BC"),
            tuple("CA"),
            tuple("EF"),
        )))
    """

    elements2groups = dict()

    for i in range(len(pairs)):
        a, b = pairs[i]
        #print(a, b)
        ca = elements2groups.get(a, None)
        cb = elements2groups.get(b , None)
        if ca is not None and cb is None:
            elements2groups[b] = ca
            ca.add(b)
            #print('ca, not cb', elements2groups)
        elif ca is None and cb is not None:
            elements2groups[a] = cb
            cb.add(a)
            #print('not ca, cb', elements2groups)
        elif ca is None and cb is None:
            c = set((a, b))
            elements2groups[a] = c
            elements2groups[b] = c
            #print('not ca, not cb', elements2groups)
        elif ca is not None and cb is not None:
            if ca is cb:
                pass
            else:
                ca.update(cb)
                for e in cb:
                    elements2groups[e] = ca
            #print('ca, cb', elements2groups)
        else:
            assert False, "%s -- %s" % (str(ca), str(cb))

    groups = list(
        {
            id(g): [objs[e] for e in g]
            for g in elements2groups.values()
        }.values()
    )

    used = {i for group in elements2groups.values() for i in group}

    if add_singletons:
        for i, obj in enumerate(objs):
            if i not in used:
                groups.append([obj])

    return groups


def index2chains(objs, ids):
    """Make sets from indices.

    `ids` is a list of groups ids for each object of `objs`.

    Return a list of lists of objects.
    
    Example:
        [o1, o2, o3]
        [ 1,  4,  1]
        return: [ [ o1, o3 ], [ o2 ] ]

    Parameters:
    -----------
    objs: list of objets
        Objets to be groupped together.
    ids: List of integers.
        Integers are group ids.
    """

    indices = { id_: i for i, id_ in enumerate(set(ids)) }
    groups = [list() for i in range(len(indices))]

    for obj, id_ in zip(objs, ids):
        groups[indices[id_]].append(obj)

    return groups



def group2relations(group, first=True, consecutive=False, custom=None,
        everything=False):
    """Compute relations from groups (chains).

    Return a list of tuples:
    
        [ (m1, m2), (m1, m2), ...]

    Warning: This function assumes that the items are sorted in each group.

    Parameters:
    -----------
    group: list of objects
        Objets to be linked.
    first: bool (def True)
        Compute first to item relations: AB, AC, AD...
    consecutive: bool (def False):
        Compute consecutive relations: AB, BC, CD...
        Note that `first` and `consecutive` may be True at the same time to
        compute all relation.  In this case, the AB relations won't appear
        twice.
    custom: iterable of two callback function
        See description.
    everything: compute all possible relations

    Note:
    -----

    For `custom` chains, use:

        custom = (callback1, callback2)

    Callback 1 is a function that takes one argument and return a bool

        rel = group2relations(
            list("NPDDNPPDDPNNP"),
            first=False,
            consecutive=False,
            custom=(
                lambda head: dict(N=True, P=False, D=False)[head],
                lambda anchor, last, current: \
                    ((anchor, current), False)
                    if current == "N"
                    else ((last, current), True),
            ),
        )

        [('N', 'P'),
         ('P', 'D'),
         ('D', 'D'),
         ('N', 'N'),
         ('N', 'P'),
         ('P', 'P'),
         ('P', 'D'),
         ('D', 'D'),
         ('D', 'P'),
         ('N', 'N'),
         ('N', 'N'),
         ('N', 'P')]

    """

    # it's a set because if first AND consecutive some relations are duplicated
    # (the first one: AB, AC... AB, BC...)
    relations = set()

    if everything:

        relations = {
            (group[i], group[j])
            for i in range(len(group))
                for j in range(i+1, len(group))
        }

    else:

        if first:
            for i in range(1, len(group)):
                relations.add((group[0], group[i]))

        if consecutive:
            for i in range(len(group)-1):
                relations.add((group[i], group[i+1]))

    if custom:
        callback1, callback2 = custom
        iterator = iter(group)
        repeat = None
        try:
            while True:
                if repeat is None:
                    i = next(iterator)
                else:
                    i = repeat
                    repeat = None
                ans1 = callback1(i)
                if ans1 is None:
                    break
                elif ans1:
                    last = i
                    while True:
                        j = next(iterator)
                        rel, cont = callback2(i, last, j)
                        if rel:
                            relations.add(rel)
                        if not cont:
                            repeat = j
                            break
                        last = j
        except StopIteration:
            pass

    """
    if custom:
        callback1, callback2 = custom
        for i in range(len(group)):
            ans1 = callback1(group[i])
            print(group[i], ans1)
            if ans1 is None:
                break
            elif ans1:
                last = None
                for j in range(i+1, len(group)):
                    ans2 = callback2(group[i], last, group[j])
                    print("-", group[j], ans2)
                    if ans2 is None:
                        break
                    elif ans2:
                        relations.add(ans2)
                        last = ans2
    """

    return relations

