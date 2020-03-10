import io
import re

import pandas as pd
import numpy as np
from scipy import stats



#### count and other aggregation ######################################

def count(src, dest, by, name=None):
    ser = src.groupby(by).size()
    if not name:
        name = "%s_count" % by
    ser.name = name
    dest = pd.merge(dest, pd.DataFrame(ser), how='outer',
        left_index=True, right_index=True)
    dest[name] = dest[name].fillna(0)
    return dest



def operation(op, na, src, dest, by, cols, names=None):
    if not names:
        names = ["%s_%s" % (col_name, op) for col_name in cols]
    op = dict(
        total=pd.core.groupby.DataFrameGroupBy.sum,
        stddev=pd.core.groupby.DataFrameGroupBy.std,
        is_normal=is_normal,
    ).get(op, getattr(pd.core.groupby.DataFrameGroupBy, op))
    df = op(src.groupby(by)[cols])
    df.columns = names
    dest = pd.merge(dest, df, how='outer', left_index=True, right_index=True)
    for name in names:
        dest[name] = dest[name].fillna(na)
    return dest


def mean(**kwargs):
    """kwargs should be `src, dest, by, cols, names=None`."""
    return operation(op='mean', na=0, **kwargs)

def total(**kwargs):
    return operation(op='sum', na=0, **kwargs)

def median(**kwargs):
    return operation(op='median', na=0, **kwargs)



def split_cat(src, dest, by, cols, names=None, proportion=True, keeps=None):

    for col, name, keep in zip(
            cols,
            names if names else [None]*len(cols),
            keeps if keeps else [set()]*len(cols)):

        if not name:
            name = col
        if not name.endswith("_"):
            name += "_"

        values = src[col].unique()

        res = pd.DataFrame(
            index=["%s%s" % (name, str(x)) for x in values])

        for id_, df in src.groupby(by):
            ser = df[col].value_counts(dropna=False)
            if proportion:
                ser = ser / ser.sum()
            ser.index = ["%s%s" % (name, str(x)) for x in ser.index]
            ser.name = id_

            res = pd.concat([res, ser], axis=1, sort=False)

        if keep:
            res = res[ [x[x.rindex('_')+1:] in keep for x in res.index] ]

        new = pd.merge(
            dest, res.T, how='outer', left_index=True, right_index=True)

        # need to fill out na on the new DF because `res` may not contain all the
        # records (`src` may not have a record with all possible `by`)
        new[new.columns] = new[new.columns].fillna(0)

    return new



#### compute annotations ###############################################

def compute_annotations(src, src_col, dest, dest_col, groupby, func,
        sort_col=None, min_len=0):

    gby = src.groupby(groupby)

    def get(id_):

        if id_ not in gby.groups:
            return None

        if sort_col:
            ser = gby.get_group(id_).sort_values(sort_col)[src_col]
        else:
            ser = gby.get_group(id_)[src_col]

        if min_len and len(ser) < min_len:
            return None

        return func(ser)

    dest[dest_col] = [ get(id_) for id_ in dest.index ]


#### copy ##############################################################

def copy(src, dest, cols, join_on, names=None):

    df = pd.merge(
        left=dest,
        right=src[cols],
        #how='outer',
        how='left',
        left_on=join_on,
        right_index=True,
        suffixes=['', '_tmp'] if names else [False, False]
    )

    if names:
        df.columns = list(dest.columns) + names

    return df




#### bins ##############################################################

def to_lmh_bins(data, *cols, copy=True, n=3):

    for col in cols:
        name = col+"_lmh" if copy else col
        if n == 2:
            second = np.percentile(data[col], 50)
            data[name] = [
                0 if x < second else 1
                for x in data[col]
            ]
        elif n == 3:
            first, third = np.percentile(data[col], [25, 75])
            data[name] = [
                0 if x < first else 2 if x > third else 1
                for x in data[col]
            ]
        elif n == 4:
            first, second, third = np.percentile(data[col], [25, 50, 75])
            data[name] = [
                0 if x < first else 1 if x < second else 2 if x < third else 3
                for x in data[col]
            ]


def is_normal(data, p=0.05, include_ks=False, return_details=False):
    if len(data) < 20:
        if return_details:
            return None, []
        return None
    ans = []
    ans.append(stats.shapiro(data))
    ans.append(stats.normaltest(data)) # valid only for len >= 20
    if include_ks:
        ans.append(stats.kstest(data, 'norm'))
        is_normal = sum((int(x[1]>=p) for x in ans)) >=2
    else:
        is_normal = {
            0: False, 1: None, 2: True
        }[sum((int(x[1]>=p) for x in ans))]
    if return_details:
        return is_normal, ans
    return is_normal



#### convenience functions #############################################

_PATTERNS = dict(
    agg=re.compile(
        r'(count|mean|median|stddev) (.+?)\.(.+?) to '
        r'(.+?)\.(.+?)(?: on (.+?))?'
        .replace(' ', '\\s+')),
    copy=re.compile(
        r'copy (.+?)\.(.+?) to (.+?)\.(.+?)(?: on (.+?))?'
        .replace(' ', '\\s+')),
    split=re.compile(
        r'(split|psplit) (.+?)\.(.+?) to (.+?)\.(.+?)(?: on (.+?))?'
        '(?: keep (.+?))?'
        .replace(' ', '\\s+')),
)

def _iter_actions(actions):
    for action in (line.strip() for line in actions.splitlines()):
        found = False
        for type_, pat in _PATTERNS.items():
            m = pat.fullmatch(action)
            if m:
                yield type_, m.groups()
                found = True
        if not found:
            raise RuntimeError("I don't understand: '%s'" % action)


def batch(db, *actions):
    actions = "\n".join(actions)
    for action, data in _iter_actions(actions):
        if action == 'agg':
            func, src, src_col, dest, dest_col, on = data
            if not on:
                on = (dest[:-1] if not '_' in dest \
                    else dest[:dest.index("_")-1]) + "_id"
            db[dest] = operation(func, na=0, src=db[src], dest=db[dest], by=on,
                cols=[src_col], names=[dest_col])
        elif action == 'copy':
            src, src_col, dest, dest_col, on = data
            if not on:
                on = (src[:-1] if not '_' in src \
                    else src[:src.index("_")-1]) + "_id"
            db[dest] = copy(src=db[src], dest=db[dest], cols=[src_col],
                join_on=on, names=[dest_col])
        elif action == 'split':
            func, src, src_col, dest, dest_col, on, keep = data
            if not on:
                on = (dest[:-1] if not '_' in dest \
                    else dest[:dest.index("_")-1]) + "_id"
            db[dest] = split_cat(src=db[src], dest=db[dest], by=on,
                cols=[src_col], names=[dest_col],
                proportion=func=='psplit',
                keeps=[set(keep.split(','))] if keep else None)
    return db




def get_bins1(x):
    if x < 1:
        return "[00-01["
    if x < 2:
        return "[01-02["
    if x < 4:
        return "[02-04["
    if x < 8:
        return "[04-08["
    if x < 16:
        return "[08-16["
    if x < 32:
        return "[16-32["
    return "[33+"


def add_distribution1(src_df, src_col, groupby, dest_df, dest_col):
    dic = dict()
    groupped = src_df.groupby(groupby)
    labels = None
    for group in groupped.groups:
        labels, _, heights = distribution2hist1(
            [get_bins1(x) for x in groupped.get_group(group)[src_col]],
            proportion=True)
        dic[group] = heights
    assert labels
    for l, label in enumerate(labels):
        dest_df[f"{dest_col}{label}"] = [
            dic[index][l] if index in dic else 0
            for index in dest_df.index
        ]


def distribution2hist1(ser, proportion=False):
    labels = ["[00-01[", "[01-02[", "[02-04[", "[04-08[", "[08-16[", "[16-32[", "[33+"]
    x = list(range(len(labels)))
    heights = [0 for i in range(len(x))]
    dic = {v:k for k, v in enumerate(labels)}
    for item in ser:
        heights[dic[item]] += 1
    if proportion:
        total = sum(heights)
        if total:
            heights = [ h / total for h in heights ]
    return labels, x, heights


_ACTION_PAT = re.compile(
    r'(?:(\w+):)?(\w+)(?:\|(\w+))?(?:\s+(.+?))?(\s+\(copy\))?')

def add_custom_annotations_from_csv(db, src_name, *, csv_string=None,
        csv_file=None, df=None):
    """See the jupyter notebook `add_aggregate_annotations`."""

    assert csv_file is not None or csv_string is not None or df is not None

    def _get_agg(string, name, col):
        m = _ACTION_PAT.fullmatch(string)
        if not m:
            raise RuntimeError(f"don't understand '{string}'")
        src, fn, new_name, args, copy = m.groups()
        if args == "(copy)" and not copy:
            copy = args
            args = None
        if fn == 'copy':
            _col = name[:-1] if dest_name.endswith('s') else name
            _col = f"{_col}_{col}"
            dest_col = new_name if new_name else _col
        else:
            dest_col = f"{fn}_{new_name}" if new_name else f"{fn}_{col}"
        src_name = src if src else name
        src_col = dest_col if src else col
        return src_name, src_col, dest_col, fn, args if args else "", copy

    if df is None:
        df = pd.read_csv(
            io.StringIO(csv_string) if csv_string else csv_file,
            index_col=0
        )
        df = df[[isinstance(x, str) for x in df.index]]
        df = df.apply(
            lambda ser: [x.strip() if isinstance(x, str) else x for x in ser])
        df.index = [x.strip() for x in df.index]

    copy_actions = []

    #for src_col, ser in df.index: # doesn't work if lines have same index
    for src_col, ser in df.iterrows():
        for dest_name in df.columns:
            #action = df.at[src_col, dest_name]
            action = ser[dest_name]
            if not action or pd.isnull(action):
                continue
            if action.startswith('#'):
                continue
            _src_name, _src_col, dest_col, func, args, copy = \
                _get_agg(action, src_name, src_col)
            act = f"{func} {_src_name}.{_src_col} to " \
                f"{dest_name}.{dest_col} {args}".strip()
            #input(act)
            if db:
                db = batch(db, act)
            else:
                print(act)
            if copy:
                _col = dest_name[:-1] if dest_name.endswith('s') else dest_name
                _col = f"{_col}_{dest_col}"
                act = f"copy {dest_name}.{dest_col} to {src_name}.{_col}"
                #input(act)
                copy_actions.append(act)

    if copy_actions:
        if db:
            db = batch(db, *copy_actions)
        else:
            print("\n".join(copy_actions))

    return db




def add_custom_annotations(db, actions):

    def go(table, data, index):
        df = pd.DataFrame(data=data, index=index)
        df = df.fillna("")
        #input(df)
        return add_custom_annotations_from_csv(db, table, df=df)

    table_name = None
    for line in (l.strip() for l in actions.split('\n')):
        if not line or line.startswith('#'):
            continue
        if line.startswith('>'):
            if table_name:
                db = go(table_name, data, index)
            table_name = line[1:].strip()
            index = []
            data = []
        else:
            field, dest_tables, action = line.split(maxsplit=2)
            dest_tables = dest_tables.split('+')
            index.append(field)
            data.append({t:action for t in dest_tables})
    if table_name:
        db = go(table_name, data, index)

    return db
