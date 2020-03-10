"""
This module contains various functions to manipulate mention and coreference
informations from a conll files (last column).

TODO: a summary of each function

"""

import re
from collections import OrderedDict
from warnings import warn

import numpy as np
import scipy.optimize


START_DOC_PATTERN = re.compile(
    #r'#begin document \((.+?)\)(?:; part (\d+))?.*' + '\n')
    r'#begin document (.*?)' + '\n')

END_DOC_STRING = '#end document\n'

CONLL_MENTION_PATTERN = re.compile(
    r'(?:\((?P<mono>\d+)\)|\((?P<start>\d+)|(?P<end>\d+)\))')



def read_files(*fpaths, sep=None, ignore_double_indices=False,
        ignore_comments=True):
    """Read one or several conll files and return a dictionary of documents.

    It just calls `read_file()` for each path.
    """

    docs = OrderedDict()
    for fpath in fpaths:
        docs.update(
                read_file(fpath,
                sep=sep,
                ignore_double_indices=ignore_double_indices,
                ignore_comments=ignore_comments)
            )
    return docs


def read_file(fpath, sep=None, ignore_double_indices=False,
        ignore_comments=True):
    """Read a conll file and return dictionary of documents.

    Dictionary format:
        { name: sentences }

    where `sentences` is a list of sentences,
    * each being a list of tokens,
    * each being a list of annotation (conll cell).
        [
            # a sentence
            [
                # a token
                [docname, index, pos, ..., coref],
                # another token
                [docname, index, pos, ..., coref],
                ...
            ],
            # another sentence
            [
                # a token
                [docname, index, pos, ..., coref],
                # another token
                [docname, index, pos, ..., coref],
                ...
            ],
        ]
    """

    docs = OrderedDict()
    for i, line in enumerate(open(fpath), start=1):
        m = START_DOC_PATTERN.fullmatch(line)
        # new document
        if m:
            key = m.group(1)
            sentences = [] # [ [ tokens... ], [ tokens... ] ]
            new_sentence = True
        elif line == END_DOC_STRING:
            docs[key] = sentences
        elif line == "\n":
            new_sentence = True
        elif line.startswith("#") and ignore_comments:
            pass
        else:
            if new_sentence:
                sentences.append([])
            new_sentence = False
            split = line[:-1].split(sep)
            if ignore_double_indices and "-" in split[0]:
                continue
            sentences[-1].append(split)
    return docs


def write_file(fpath, docs, *, align_right=True, sep=None):
    """Write a conll file.

    Parameters:
    * docs: dictionary as described in `read_file()`
    * align_right: bool (def True) whether to align col to the right
    """

    fh = open(fpath, 'w')
    for key, sents in docs.items():
        fh.write(f'#begin document {key}\n')
        for s, sent in enumerate(sents):
            if s > 0:
                fh.write("\n")
            if sep is None:
                # compute max lengths
                lengths = None
                for tok in sent:
                    if lengths is None:
                        lengths = [0]*len(tok)
                    for c, col in enumerate(tok):
                        lengths[c] = max(lengths[c], len(col))
                for tok in sent:
                    for c, col in enumerate(tok):
                        if align_right:
                            extra = 0 if c == 0 else 3
                            fmt = "%% %ds" % (lengths[c] + extra)
                            fh.write(fmt % col)
                        else:
                            fh.write(col)
                    fh.write("\n")
            else:
                for tok in sent:
                    fh.write("\t".join(tok) + "\n")
        fh.write('#end document\n\n')
    fh.close()



def compute_mentions(column):
    """Compute mentions from the raw last column of the conll file.

    `column` is a list:
        ['*', '(1', '*', '1)', ...]

    Return a list of tuples of the form:
        ( (START, STOP) , CHAIN)
    where CHAIN is the chain number given in the conll file.  It's an
    **integer**.
    """

    # to check for duplicated mentions
    used = set() # {(start, stop)...}
    def is_duplicated(pos):
        if pos in used:
            warn(f"Mention {pos} duplicated. Ignoring.")
            return True
        used.add(pos)

    pending = dict()
    mentions = []
    for i, cell in enumerate(column):
        for m in CONLL_MENTION_PATTERN.finditer(cell):
            if m.lastgroup == 'mono':
                pos = (i, i+1)
                chain = int(m.group(m.lastgroup))
                if not is_duplicated(pos):
                    mentions.append((pos, chain))
            elif m.lastgroup == 'start':
                chain = int(m.group(m.lastgroup))
                if not chain in pending:
                    pending[chain] = []
                pending[chain].append(i)
            elif m.lastgroup == 'end':
                chain = int(m.group(m.lastgroup))
                pos = (pending[chain].pop(), i+1)
                if not is_duplicated(pos):
                    mentions.append((pos, chain))
            else:
                assert False
    for k, v in pending.items():
        if v:
            assert False, pending
    return mentions



def compute_chains(sents, return_dic=False):
    """Compute and return the chains from the conll data.

    `sents` is a list of sentences as described in `read_file()` (just one of
    the values of the `docs` dictionary).

    Return a list of chains,
    * each being a list of mentions,
    * each being a tuple of (sent, start, end).

        # list of chains
        [
            # a chain
            [
                # a mention
                (sent, start, end),
                # another mention
                (sent, start, end),
                ...
            ],
            # another chain
            [
                # a mention
                (sent, start, end),
                # another mention
                (sent, start, end),
                ...
            ],
            ...
        ]

    where `sent` is just the index (integer) of the sentence in the doc.
    """

    chains = dict()
    for s, sent in enumerate(sents):
        last_col = [tok[-1] for tok in sent]
        for (start, stop), chain_id in compute_mentions(last_col):
            end = stop - 1
            if chain_id not in chains:
                chains[chain_id] = []
            chains[chain_id].append((s, start, end))
    if return_dic:
        return chains
    return list(chains.values())


def sentpos2textpos(mentions, sents):
    """Transform mentions `[SENT, START, STOP]` to `[TEXT_START, TEXT_STOP]`.

    `mentions` is a list of mentions, each mention must be a list that will be
    modified (so you can extract them for chains and passed the references).

    `sents` is the document, as described in `read_file()`.  It is used to
    compute the sentence boundaries.
    """

    offset = 0
    sent2text = []
    for sent in sents:
        sent2text.append([i+offset for i in range(len(sent))])
        offset += len(sent)

    for mention in mentions:
        sent, start, stop = mention
        mention.clear()
        mention.extend((sent2text[sent][start], sent2text[sent][stop]))






def textpos2sentpos(mentions, sents):
    """Transform mentions `[TEXT_START, TEXT_STOP]` to `[SENT, START, STOP]`.

    `mentions` is a list of mentions, each mention must be a list that will be
    modified (so you can extract them for chains and passed the references).

    `sents` is the document, as described in `read_file()`.  It is used to
    compute the sentence boundaries.
    """

    mapping = [
        (i, j)
        for i, sent in enumerate(sents)
            for j, token in enumerate(sent)
    ]

    for mention in mentions:
        start, stop = mention
        sent_start, start = mapping[start]
        sent_stop, stop = mapping[stop]
        assert sent_start == sent_stop
        mention.clear()
        mention.extend([sent_start, start, stop])



def write_chains(sents, chains, append=False, no_chain_char="-"):
    """Convert a list of chains to a conll coreference column.

    `sents` is a list of sentences as described in `read_file()` (just one of
    the values of the `docs` dictionary).

    `chains` is a list of chains as described in the `compute_chains()`.

    If `append`, then the data are added as a new column to `sents`, otherwise
    the last column is replaced by the new informations.
    """

    if isinstance(chains, dict):
        chains = list(chains.values())
    starts = dict() # {sent: {index: [chain_ids]} }
    ends = dict() # {sent: {index: [chain_ids]} }
    monos = dict() # {sent: {index: [chain_ids]} }
    for c, chain in enumerate(chains):
        for sent, start, end in chain:
            if start == end:
                if sent not in monos:
                    monos[sent] = dict()
                if start not in monos[sent]:
                    monos[sent][start] = []
                monos[sent][start].append(c)
            else:
                if sent not in starts:
                    starts[sent] = dict()
                if start not in starts[sent]:
                    starts[sent][start] = []
                starts[sent][start].append(c)
                if sent not in ends:
                    ends[sent] = dict()
                if end not in ends[sent]:
                    ends[sent][end] = []
                ends[sent][end].append(c)
    for s, sent in enumerate(sents):
        for t, tok in enumerate(sent):
            res = []
            if s in monos and t in monos[s]:
                res.extend(["(%d)" % c for c in monos[s][t]])
            if s in starts and t in starts[s]:
                res.extend(["(%d" % c for c in starts[s][t]])
            if s in ends and t in ends[s]:
                res.extend(["%d)" % c for c in ends[s][t]])
            res = "|".join(res) if res else no_chain_char
            if append:
                tok.append(res)
            else:
                tok[-1] = res



def replace_coref_col(src_docs, tar_docs):
    """Replace the last column of `tar_docs` by the last column of `src_docs`.
    """

    assert len(src_docs) == len(tar_docs)
    for doc_id, src_sents in src_docs.items():
        for src_sent, tar_sent in zip(src_sents, tar_docs[doc_id]):
            for src_token, tar_token in zip(src_sent, tar_sent):
                tar_token[-1] = src_token[-1]



def remove_singletons(infpath, outfpath):
    """Remove the singletons of the conll file `infpath`, and write the version
    without singleton in the conll file `outfpath`.
    """

    docs = read_file(infpath)
    for doc_id, sentences in docs.items():
        chains = compute_chains(sentences)
        chains = filter(lambda x: len(x) > 1, chains)
        write_chains(sentences, chains)
        docs[doc_id] = sentences
    write_file(outfpath, docs)





def filter_pos(mentions, sents, unwanted_pos):
    """Filter mentions that have POS in unwanted_pos, return a new mention list.

    `sents` is a list of sentences as described in `read_file()` (just one of
    the values of the `docs` dictionary).  It is just use to find the POS of
    the mention.

    `mentions` contains the mentions to be checked.  It's a list of tuples
    `(sent, start, end)`:
        mentions = [
            (sent, start, end),
            (sent, start, end),
            ...
        ]

    `unwanted_pos` is a list of unwanted pos.

    Return a new mentions list (like `mentions`).
    """

    # reminder: `sents[sent][start][4]` is the POS
    return [
        (sent, start, end)
        for sent, start, end in mentions
        if sents[sent][start][4] not in unwanted_pos
    ]



def check_no_duplicate_mentions(chains):
    """Return True if there is no duplicate mentions."""

    mentions = [ m for c in chains for m in c ]
    return len(mentions) == len(set(mentions))



def merge_boundaries(coref_docs, boundary_docs, unwanted_pos=None):
    """Add the mentions of `boundary_docs` to `coref_docs` if they don't
    already exist, as singletons.

    `coref_docs` are key documents without singletons.  These are found in:
    *v4_gold_conll files

    Note that if you want "auto" parses, you will need to merge the coref data
    from the gold file to the auto file:

        replace_coref_col(coref_docs, auto_docs)

    where `auto_docs` are read from *v9_auto_conll files.

    For example:

        coref_docs = read_files(["/tmp/all_v4_test_gold_conll"])
        auto_docs = read_files(["/tmp/all_v9_auto_conll"])
        replace_coref_col(coref_docs, auto_docs)
        coref_docs = auto_docs

    `boundary_docs` are all the mention boundaries (singleton or not), but
    without coref informations.  These are found in:
    *v9_gold_parse_mention_boundaries_conll files.

    Note that all boundary mentions must be in the same pseudo chain (that is,
    they must all have the same chain number in the conll file).  Otherwise,
    an assert fails.

    `unwanted_pos` is None or a list of POS that will be filtered out
    from boundaries before the mentions are added to `coref_docs`.  For
    example, for conll-2012, this should be, for example:
    VBN, VB, VBD, VBZ, VBG, VBP, MD, RB, WRB

    The function alters `coref_docs`.  You can then write them with
    `write_file()`
    """

    assert len(coref_docs) == len(boundary_docs)
    parts_of_speech = dict()
    for doc_id, coref_sents in coref_docs.items():
        boundary_sents = boundary_docs[doc_id]
        chains = compute_chains(coref_sents)
        boundaries = compute_chains(boundary_sents)
        assert len(boundaries) == 1
        boundaries = boundaries[0]
        boundaries = filter_pos(
            sents=boundary_sents,
            mentions=boundaries,
            unwanted_pos=unwanted_pos if not None else [],
        )
        mentions = {m for c in chains for m in c}
        boundaries = [b for b in boundaries if not b in mentions]
        chains = chains + [ [b] for b in boundaries ]
        assert check_no_duplicate_mentions(chains), doc_id
        write_chains(coref_sents, chains)


def remove_col(docs, *cols):
    """Remove columns *cols from all tokens in docs.

    Columns indices may be negative.

    Return a new collections of docs, don't touch the original.
    """
    input("experimental")

    docs = \
    [
        [        
            [
                [ tok[col] for col in cols ]
                for tok in sent
            ] for sent in doc
        ]
        for doc in docs
    ]

    return docs
    


def align_mention_boundaries(key_docs, resp_docs, remove_non_aligned=False):
    """Align mention boundaries from resp to match mention boundaries of key.

    This uses the Munkres algorithm.

    The algorithm is described in comments in the code.
    """

    assert len(key_docs) == len(resp_docs)
    for doc_id, key_sents in key_docs.items():

        resp_sents = resp_docs[doc_id]

        # STEP 1: we extract the mentions, with the format:
        #   (SENT_ID, START, STOP)

        key_chains = compute_chains(key_sents)
        key_mentions = [ mention for chain in key_chains for mention in chain ]
        resp_chains = compute_chains(resp_sents)

        # we need to transform tuple to list for the resp mentions because we
        # need to assign the <start> and <stop> of these mentions to correct
        # them!

        resp_chains = [
            [ list(mention) for mention in chain ]
            for chain in resp_chains
        ]
        resp_mentions = \
            [ mention for chain in resp_chains for mention in chain ]

        mentions = key_mentions + resp_mentions
        # NOTE: mentions are triplets (SENT, START_IN_SENT, stop_IN_SENT).
        # Because start/stop sentence-specific, you must sort by start AND by
        # sentence!
        mentions.sort(key=lambda mention: mention[1])
        mentions.sort(key=lambda mention: mention[0])

        #print(mentions)

        # STEP 2: we make groups of overlapping mentions:
        #   key:   [A     ]   [B    ]   [C    ]
        #   resp:   [a           ]
        # group1: ABa
        # group2: C
        #
        # At the end, only group with more than 1 elements are kept

        groups = []
        cur = None # current group
        # don't forget: you must take sentences into account
        for mention in mentions:
            # reminder: mention[1] = start
            if cur and not (mention[1] <= cur['stop']
                                and mention[0] == cur['sent']): 
                if len(cur['items']) > 1:
                    groups.append(cur['items'])
                cur = None
            if cur is None:
                cur = dict(
                    sent=mention[0],
                    stop=mention[2], # mention[2]=stop
                    items=[mention]
                )
            else:
                cur['items'].append(mention)
                cur['stop'] = max(cur['stop'], mention[2])

        if cur and len(cur['items']) > 1:
            groups.append(cur['items'])

        #input(groups)

        # STEP 3: we compute a similarity matrix, where the similarity function
        # is
        #   abs(m2_start-m1_start) + abs(m2_stop-m1_stop)
        # and we apply the Munkres algorithm to get an optimal alignment

        for group in groups:

            key_gr = []
            resp_gr = []
            for mention in group:
                if isinstance(mention, tuple):
                    key_gr.append(mention)
                else:
                    resp_gr.append(mention)

            # if only 2 members in the group, one key and one resp, just pair
            # them:
            if len(key_gr) == 1 and len(resp_gr) == 1:
                rows = [0]
                cols = [0]

            # else, run the Munkres algorithm
            else:
                mat = np.array(
                    [
                        [
                            abs(r[1]-k[1]) + abs(r[2]-k[2])
                            for k in key_gr
                        ]
                        for r in resp_gr
                    ]
                )
                #for i, r in enumerate(resp_gr):
                #    for j, k in enumerate(key_gr):
                #        f = abs(r[1]-k[1]) + abs(r[2]-k[2])
                #        print(i, r, j, k, f)
                #print(mat)
                rows, cols = scipy.optimize.linear_sum_assignment(mat)

            #print(rows)
            #print(cols)

            assert len(rows) == len(cols)

            # STEP 4: correcting the alignment
            # The problem is that the alignment chosen by the Munkres algorithm
            # may result in overlapping mentions in the response.  For example:
            #   key:      [A    ]    [B     ]
            #   resp:    [a   ][b     ][c    ]
            # Let's say we have A->a and B->c.  In this cas, b and c will
            # overlap.
            # So we try to get rid of overlapping by removing some alignments
            # made by the Munkres algorithm, starting with the least favorable
            # (those with a lesser similarity).
            #
            # NOTE: this make the algorithm not optimal.

            ans = [ (row, col) for row, col in zip(rows, cols) ]
            ans.sort(key=lambda x: mat[x[0], x[1]], reverse=True)

            def overlap(items, true_if_nested=False):
                items = sorted(items, key=lambda x: x[2])
                items = sorted(items, key=lambda x: x[1])
                for i in range(1, len(items)):
                    m1_start, m1_end = items[i-1][1], items[i-1][2]
                    m2_start, m2_end = items[i][1], items[i][2]
                    if m2_start <= m1_end and \
                            (true_if_nested or not m2_end <= m1_end):
                        return True
                return False

            saved_resp = []
            for row, col in ans:
                # there must be some overlap!
                assert overlap([resp_gr[row], key_gr[col]], true_if_nested=True)
                saved_resp.append(dict(
                    mention=resp_gr[row],
                    start=resp_gr[row][1],
                    stop=resp_gr[row][2],
                ))
                resp_gr[row][1] = key_gr[col][1] # [1] is start
                resp_gr[row][2] = key_gr[col][2] # [2] is end

            while saved_resp and overlap(resp_gr):
                saved = saved_resp.pop()
                saved['mention'][1] = saved['start']
                saved['mention'][2] = saved['stop']

            #for row, col in zip(rows, cols):
            #    #print(resp_gr[row], " -> ", key_gr[col])
            #    resp_gr[row][1] = key_gr[col][1] # [1] is start
            #    resp_gr[row][2] = key_gr[col][2] # [2] is end
            #print("sum", mat[rows, cols].sum())
            #print("====")

            # STEP 5: We remove the non-aligned mentions, if asked

            if remove_non_aligned:
                for i in range(len(resp_gr)):
                    if i not in rows:
                        resp_gr[i][0] = None

        # STEP 6: We remove the non-aligned chains, if asked

        if remove_non_aligned:
            new_resp_chains = []
            for chain in resp_chains:
                new_chain = filter(lambda x: x[0] is not None, chain)
                if new_chain:
                    new_resp_chains.append(new_chain)
            resp_chains = new_resp_chains

        # STEP 7: write back the response mentions

        write_chains(resp_sents, resp_chains, append=False)



def write_mentions(sent, mentions, append=False):
    """Opposite for `compute_mentions()`.  Write the last column in `sent`.

    `sent` is a list of tokens as described in `read_file()`.
    WARNING: it's just ONE sentence.

    `mentions` is a list of tuples:
        ( (start, stop), chain )
    where `chain` is an integer.

    `append`: the column is added, otherwise the last is replaced.
    """

    def append(cur, val):
        if cur == "*":
            return val
        else:
            return "%s_%s" % (cur, val)

    col = ["*"]*len(sent)
    for (start, stop), chain in mentions:
        end = stop - 1
        if start == end:
            col[start] = append(col[start], "(%d)" % chain)
        else:
            col[start] = append(col[start], "(%d" % chain)
            col[end] = append(col[end], "%d)" % chain)
    
    for i, tokens in enumerate(sent):
        if append:
            tokens.append(col[i])
        else:
            tokens[-1] = col[i]

def compare_coref_cols(base, *others, outfpath, kept_cols):
    """Build a conll file that merge the corefcols of several other files.

    This is for debugging purpose.

    Parameters:
    * base: path of the base file
    * others: path of other files, from where to take the corefcol
    * outfpath: output file
    * kept_cols: list of index of columns to include from the `base` file,
      besides the corefcol
    """

    base = read_file(base)
    others = [ read_file(f) for f in others ]
    
    new_docs = dict()
    for doc_id, base_sents in base.items():
        new_sents = [
            [
                [ token[i] for i in kept_cols ]
                for token in sent
            ]
            for sent in base_sents
        ]
        for sents in [base_sents] + [ x[doc_id] for x in others ]:
            for sent, new_sent in zip(sents, new_sents):
                for i in range(len(sent)):
                    new_sent[i].append(sent[i][-1])
        new_docs[doc_id] = new_sents

    write_file(outfpath, new_docs)



def to_corefcol(infpath, outfpath):
    """Write the conll file `outfpath` with just the last column (coref) of the
    conll file `infpath`.

    Assume there is no space inside a cell.
    """

    fh = open(outfpath, 'w')
    for line in open(infpath):
        if line.startswith("#") or line == "\n":
            fh.write(line)
        else:
            fh.write(line.split()[-1] + "\n")
    fh.close()



_conll_2012_key_pattern = re.compile(
    r'\(((?:[^/]+/)*(.+?))\); part (\d+)')

def get_conll_2012_key_pattern(key=None, fmt=None):
    """Return a compiled pattern object to match conll2012 key format.

    The conll2012 format is:
        (path/to/doc); part 001

    The pattern defines three groups:
    * `path/to/doc`
    * `doc`
    * `001`
    """

    if key:
        m = _conll_2012_key_pattern.fullmatch(key)
        path, name, part = m.groups()
        if fmt == "lee18":
            return "%s_%d" % (path, int(part))
        elif not fmt:
            return path, name, part
        else:
            raise RuntimeError(f"unknown format 'fmt'")

    return _conll_2012_key_pattern


def merge_amalgams(docs, amalgams, reset_cols=True, outfpath=None, sep=None):
    """Add amalgams in documents from where they have been removed.

    Some parsers (eg stanfordnlp) decompose amalgams:
        1-2 du ...
        1 de ...
        2 le ...
    
    You can ignore amalgams when reading a file with `read_files()` with the
    `ignore_double_indices` parameter.

    Use this function to add the amalgams back into the documents.

    This will shift indices, so don't compute chains before using this
    function, but after.

    Parameters:
    -----------
    docs: dict or str
        documents without amalgams, the one that will be modified.  If string,
        read the file.
    amalgams: dict
        documents with amalgams.  If string, read the file.
    reset_cols: bool
        reset columns by inserting an underscore on every column, otherwise
        just insert the amalgam line as is
    outfpath: None (def) or str
        outfpath (None: don't save)
    sep: None (def) or str
        seperator when outputing the file
    """

    if isinstance(docs, str):
         docs = read_file(docs)
    if isinstance(amalgams, str):
         amalgams = read_file(amalgams)

    for id_, doc_sents in docs.items():
        amalgam_sents = amalgams[id_]
        for doc_sent, amalgam_sent in zip(doc_sents, amalgam_sents):
            d, a = 0, 0
            while d < len(doc_sent):
                if doc_sent[d][0] == amalgam_sent[a][0]:
                    d, a = d+1, a+1
                    continue
                if "-" not in amalgam_sent[a][0]:
                    raise RuntimeError(f"not an amalgam: {amalgam_sent[a]}")
                if reset_cols:
                    new_amalgam = amalgam_sent[a][:2] \
                        + ["_"] * (len(doc_sent[d])-2)
                else:
                    new_amalgam = amalgam_sent[a]
                doc_sent.insert(d, new_amalgam)
                d, a = d+1, a+1

    if outfpath:
        write_file(outfpath, docs, sep=sep)

    return docs



def test_mention_alignment():
    key_fpath = "test_cases/boundary_alignment_text1_key.conll"
    resp_fpath = "test_cases/boundary_alignment_text1_resp.conll"
    key_docs = read_file(key_fpath)
    resp_docs = read_file(resp_fpath)
    align_mention_boundaries(key_docs, resp_docs)
    write_file("/tmp/res.conll", resp_docs)
    compare_coref_cols(key_fpath, resp_fpath, "/tmp/res.conll",
        outfpath="/tmp/res_compared.conll", kept_cols=[0, 1])


if __name__ == "__main__":
    pass
    #test_mention_alignment()

