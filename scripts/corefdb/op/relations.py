import pandas as pd

from coreftools.chains import group2relations


def build_relations(mentions, first=True, consecutive=False, custom=None):

    relations = pd.DataFrame(
        data = (
            (chain_id, rel[0], rel[1])
            for chain_id, df in mentions.groupby("chain_id")
            for rel in group2relations(
                df.sort_values(
                    by=['text_start', 'text_stop'],
                    ascending=[True, False],
                ).index,
                first=first,
                consecutive=consecutive,
                custom=custom)
        ),
        #columns=['text_id', 'chain_id', 'm1_id', 'm2_id'],
        columns=['chain_id', 'm1_id', 'm2_id'],
    )
    relations.index.name = "id"

    # DEBUG
    # print(relations)
    # input(len(relations))
    # relations = pd.merge(relations, mentions[['text_id', 'string']],
    #     how='left', left_on='m1_id', right_index=True)
    # print(relations)
    # input(len(relations))
    # relations = pd.merge(relations, mentions[['string']],
    #     how='left', left_on='m2_id', right_index=True)
    # print(relations)
    # input(len(relations))

    relations = pd.merge(relations, mentions[['text_id']],
        how='left', left_on='m1_id', right_index=True)

    return relations






def compute_annotations(mentions, relations, comparisons=None,
        differences=None, absolutes=None, lambdas=None, copies=None):

    # merging m1
    df = pd.merge(
        left=relations,
        right=mentions,
        how='inner',
        left_on='m1_id',
        right_index=True,
        suffixes=('','_rm1'),
    )
    df.columns = list(relations.columns) \
        + ["m1_%s" % x for x in mentions.columns]

    # merging m2
    col_nb = len(df.columns)
    df = pd.merge(
        left=df,
        right=mentions,
        how='inner',
        left_on='m2_id',
        right_index=True,
        suffixes=('','_rm2'),
    )
    df.columns = list(df.columns[:col_nb]) \
        + ["m2_%s" % x for x in mentions.columns]

    #input(df)
    #input(list(df.columns))

    col_nb = len(df.columns)

    # difference
    if differences:
        for i in differences:
            src, dest = i.split() if ' ' in i else (i, "diff_"+i)
            df[dest] = [
                m2-m1 for m1, m2 in zip(df["m1_"+src], df["m2_"+src])
            ]

    # absolute difference
    if absolutes:
        for i in absolutes:
            src, dest = i.split() if ' ' in i else (i, "diff_"+i)
            df[dest] = [
                abs(m2-m1) for m1, m2 in zip(df["m1_"+src], df["m2_"+src])
            ]

    # comparisons
    if comparisons:
        for i in comparisons:
            src, dest = i.split() if ' ' in i else (i, "same_"+i)
            df[dest] = [
                m1 == m2 for m1, m2 in zip(df["m1_"+src], df["m2_"+src])
            ]

    # lambdas
    if lambdas:
        for i, func in lambdas:
            src, dest = i.split() if ' ' in i else (i, "altered_"+i)
            df[dest] = [
                func(m1, m2) for m1, m2 in zip(df["m1_"+src], df["m2_"+src])
            ]

    # copies
    copied_cols = []
    if copies:
        new_names = dict()
        for i in copies:
            if ' ' in i:
                src, dest = i.split()
                new_names['m1_'+src] = 'm1_'+dest
                new_names['m2_'+src] = 'm2_'+dest
                copied_cols.append('m1_'+dest)
                copied_cols.append('m2_'+dest)
            else:
                copied_cols.append('m1_'+i)
                copied_cols.append('m2_'+i)
        if new_names:
            df.rename(columns=new_names)


    return df[
          list(relations.columns)
        + list(df.columns[col_nb:])
        + copied_cols
    ]



def batch(mentions, relations, actions):

    differences = []
    absolutes = []
    comparisons = []
    copies = []

    if isinstance(actions, str):
        actions = actions.split("\n")

    for action in actions:
        action = action.strip()
        if not action or action.startswith("#"):
            continue
        field, *methods = action.split()
        for method in methods:
            if method == 'diff':
                differences.append(field)
            elif method == 'abs':
                absolutes.append(field)
            elif method == 'comp':
                comparisons.append(field)
            elif method == 'copy':
                copies.append(field)
            else:
                raise RuntimeError(f"Unknown method: '{method}'")
    return compute_annotations(mentions, relations,
        comparisons=comparisons,
        differences=differences,
        absolutes=absolutes,
        copies=copies,
    )

