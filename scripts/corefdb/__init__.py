"""
Loading the database from a zip file is done through the `DatabaseZip` class.
Helpers functions are defined to ease the process.

Tables of the db are stored as members of the zip file, so they are called
"members".

Synopsis:

    # to extract:
    chain, tokens = iterate("path/to/file.zip", 'chains', 'tokens'...)

    # getting a dictionary (keys are name of the zip file members without the
    # .csv extension):  { chains: DF, tokens: DF, etc. }
    db = load("path/to/file.zip")

    # to load some members only:
    db = load("path/to/file.zip", 'chains', 'tokens'...)

    # to save:
    save(db, "path/to/file.zip", 'chains', 'tokens'...)
"""

import io
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED

import pandas as pd

# imports to be used directly from corefdb
import corefdb.importers.conll
import corefdb.op
import corefdb.op.relations
import corefdb.layers
import corefdb.layers.conll
import corefdb.layers.dem1921
import corefdb.layers.base
import corefdb.layers.ling
import corefdb.layers.advanced
import corefdb.layers.context_similarity
import corefdb.layers.wordnet
import corefdb.layers.stop2end


__version__ = "1.0.0"


class DatabaseZip:
    """Extract dataframes from a zip file."""



    def __init__(self, fpath):
        self.fpath = fpath



    def _read_head(self, zf, member, n=10):
        with io.TextIOWrapper(zf.open(member)) as ufh:
            lines = ""
            for i in range(n):
                line = ufh.readline()
                if not line:
                    break
                lines += line
        return lines



    def iter_members(self, *members, head=0):
        """Iter over all csv members and yield `(name_no_ext, dataframes)`.

        `members` is the list of members to extract, with or without the .csv
        extension.  If None, all members are returned.

        `head` is None (the whole df is returned) or a number of rows read
        (including the header).

        The index of the df is the `id` column if it exists, or the first
        column otherwise.
        """
        res = dict()
        with ZipFile(self.fpath) as zf:
            if members:
                # remove all non .csv
                members = [
                    (x + ".csv") if not x.endswith(".csv") else x
                    for x in members
                ]
            else:
                members = filter(lambda x: x.endswith(".csv"), zf.namelist())
            for member in members:
                if head:
                    head_content = self._read_head(zf, member, head)
                    df = pd.read_csv(io.StringIO(head_content),
                        keep_default_na=False, na_values="")
                else:
                    df = pd.read_csv(io.TextIOWrapper(zf.open(member)),
                        keep_default_na=False, na_values="", low_memory=False)
                    #input("foo")
                if 'id' in df.columns:
                    df.set_index('id', drop=True, inplace=True)
                elif df.shape[1] > 1:
                    df.set_index(df.columns[0], drop=True, inplace=True)
                yield member[:-4], df
    


    def extract_members(self, *members, head=0):
        """Extract all csv members and return a dictionary.

        Return a dictionary { NAME: DF, ... } were NAME is the name of members
        without the csv extension.

        The rest is like `iter_members()`.
        """
        return {
            member: df
            for member, df in self.iter_members(*members, head=head)
        }



    @property
    def members(self):
        """Return the list of members in the zip file, with extensions."""
        with ZipFile(self.fpath) as zf:
            return zf.namelist()



def load(zipfile, *members, head=0):
    """Read the zipfile and load the requested csv members in a dictionary.

    Convenience function for DatabaseZip.extract_members().
    """
    return DatabaseZip(zipfile).extract_members(*members, head=head)



def load_list(zipfile, *members, head=0):
    """Load the requested csv members and return them as list of dfs.
    """
    dic = load(zipfile, *members, head=head)
    return [ dic[k] for k in members ]


def iterate(zipfile, *members, head=0):
    """Iter over the requested csv member.

    Convenience function for DatabaseZip.iter_members().
    """
    return DatabaseZip(zipfile).iter_members(*members, head=head)


def save(dic, fpath, *members, compression=True):
    """Export the dictionary of dataframes.

    `dic` is a dictionary of dataframe `{ NAME: DF }` where NAME is the name of
    a member, with or without a csv extension (added if necessary).

    Only requested `members` (= keys of dictionary), if defined, are written.
    """

    if compression == True:
        compression = ZIP_DEFLATED
    elif compression == False or compression is None:
        compression = ZIP_STORED

    with ZipFile(fpath, 'w', compression=compression) as zf:
        for member, df in dic.items():
            if members and member not in members:
                continue
            if not member.endswith('.csv'):
                member += '.csv'
            with io.TextIOWrapper(zf.open(member, 'w')) as ufh:
                df.to_csv(ufh)



def browse_by_corpora(zipfiles, *members, text_member='texts', text_ids=None):
    """Yield a by text divided db for each corpus (zipfile).

    Yield a series of tuple `(zipfile, lst)`, where `lst` is a list of tuples
    `(text_id, df)`.

    Read only `members` (or all members if nothing).  They should have a `text_id`
    columns.  If they don't, they won't be filtered out by text and will be yield
    as is.

    `text_member` is the member use for the text list.  Default is `texts`.

    `text_ids` is an iterable with the text ids to yield, in order.  If None
    (default), yields all texts found in the first zipfile.

    Note that if a text id is not in a df, a empty df (but with all the columns) is
    returned.
    """

    for zipfile in zipfiles:
        
        db = load(zipfile, *members)

        if text_ids is None:
            text_ids = db[text_member].index

        gby = {
            k: ((v.groupby('text_id') if 'text_id' in v.columns else None), v)
            for k, v in db.items()
        }

        yield zipfile, [
            (
                text_id, {
                    k: (
                        v[0].get_group(text_id)
                        if text_id in v[0].groups
                        else v[1][[False]*v[1].shape[0]]
                       )
                       if v[0] is not None
                       else v[1]
                    for k, v in gby.items()
                }
            )
            for text_id in text_ids
        ]



def browse_by_corpora_and_texts(zipfiles, *members, text_member='texts',
        text_ids=None):
    """Same as `browse_by_corpora()` but yield a tuple `(zipfile, text_id, df)`.
    """

    for zipfile, lst in browse_by_corpora(zipfiles, *members,
            text_member=text_member, text_ids=text_ids):
        for text_id, df in lst:
            yield zipfile, text_id, df



def browse_by_texts(zipfiles, *members, text_member='texts', text_ids=None):
    """Same as `browse_by_corpora()` but by texts."""

    text_list = None
    data = dict() # { text1: {zipfile1: gby_df, zipfile2: gby_df...}, text2...}
    #data = dict() # { zipfile1: {text1: gby_df, text2: gby_df...}, zipfile2...}

    for zipfile, lst in browse_by_corpora(zipfiles, *members,
            text_member=text_member, text_ids=text_ids):
        if text_list is None:
            text_list = [x[0] for x in lst]
        for text_id, df in lst:
            if not text_id in data:
                data[text_id] = dict()
            data[text_id][zipfile] = df
    
    for text_id in text_list:
        yield text_id, [
            (zipfile, data[text_id][zipfile]) for zipfile in zipfiles
        ]



def browse_by_texts_and_corpora(zipfiles, *members, text_member='texts',
        text_ids=None):
    """Same as `browse_by_corpora_and_texts()` but by text then by corpus.

    Yielded tuples are `(zipfile, text_id, df)`.
    """

    for text_id, lst in browse_by_texts(zipfiles, *members,
            text_member=text_member, text_ids=text_ids):
        for zipfile, df in lst:
            yield zipfile, text_id, df




