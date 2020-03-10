import corefdb
import shutil
import os
import argparse


CACHE_DIR = "/tmp/cache_build_db"
INVENTORIES2WORDNET_FPATH = "../helpers/inventories2wordnet.json"
FASTTEXT = "/tmp/fasttext_%s_filtered"



def build_db(*infpaths, corpus_name):

    print(f"Building db for {corpus_name}.")

    if corpus_name == 'conll2012':
        db = corefdb.importers.conll.build_db(
            *infpaths,
            word_col=3,
            #key_callback=get_callback(corpus),
        )
    elif corpus_name in ('dem1921', 'ancor'):
        db = corefdb.importers.conll.build_db(
            *infpaths,
            word_col=1,
            sep="\t",
            par_col=-4,
            ignore_double_indices=True,
            ignore_comments=True,
            #key_callback=get_callback(corpus),
        )
    elif corpus_name == 'conll':
        db = corefdb.importers.conll.build_db(
            *infpaths,
            word_col=3,
            #ignore_comments=True,
        )
    elif corpus_name == 'conllu':
        db = corefdb.importers.conll.build_db(
            *infpaths,
            word_col=1,
            sep="\t",
            ignore_double_indices=True,
            #ignore_comments=True,
        )
    else:
        raise RuntimeError(f"unknown corpus: {corpus} (load db)")

    print("Computing relations.")

    db['relations'] = corefdb.op.relations.build_relations(
        db['mentions'],
        first=False,
        consecutive=True,
        custom=None,
    )

    print("Computing base annotations.")

    db = corefdb.layers.base.run_all(db)

    return db



def add_linguistic_annotations(db, *infpaths, corpus_name):

    print(f"Adding corpus specific annotations ({corpus_name}).")

    if corpus_name == "conll2012":
        if os.path.exists(CACHE_DIR):
            shutil.rmtree(CACHE_DIR)
        corefdb.layers.conll.build_cache_conll2012(
            *infpaths,
            cache_dir=CACHE_DIR,
            inventories2wordnet_fpath=INVENTORIES2WORDNET_FPATH,
        )
        db = corefdb.layers.conll.add_conll2012_specific_annotations(
            db, CACHE_DIR, *infpaths)
    else:
        db = corefdb.layers.dem1921.add_dem1921_specific_annotations(
            db, *infpaths, replace_genre=corpus_name=="dem1921")

    print("Computing linguistic annotations.")

    db = corefdb.layers.ling.run_all(db)

    return db




def add_advanced_annotations(db, *infpaths, corpus_name):

    print("Computing advanced annotations.")

    path = FASTTEXT % corpus_name

    db = corefdb.layers.advanced.run_all(
        db,
        word_vectors_fpath=path,
        wn_lang="eng" if corpus_name == "conll2012" else "fra",
    )

    return db




def parse_args():
    # definition
    parser = argparse.ArgumentParser(prog="db_builder.py",
        description="build coref db",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    # arguments (not options)
    parser.add_argument("infpaths", nargs="+", help="input files")
    # options
    parser.add_argument("--corpus-name", dest="corpus_name",
        choices="dem1921 ancor conll2012 conll conllu".split(),
        required=True, default=None,
        help="corpus name (dem1921, ancor, conll2012, conllu)")
    parser.add_argument("--linguistic", dest="linguistic", default=False,
       action="store_true", help="add linguistic annotations")
    parser.add_argument("--advanced", dest="advanced", default=False,
       action="store_true", help="add advanced annotations")
    parser.add_argument("-o", dest="outfpath",
        help="output file", metavar="FILE", required=True)
    # reading
    args = parser.parse_args()
    return args


def main():

    args = parse_args()

    db = build_db(*args.infpaths, corpus_name=args.corpus_name)
    if args.linguistic:
        db = add_linguistic_annotations(
            db,
            *args.infpaths,
            corpus_name=args.corpus_name)
        if args.advanced:
            db = add_advanced_annotations(
                db,
                *args.infpaths,
                corpus_name=args.corpus_name)

    db = corefdb.layers.stop2end.replace_stop_by_end(db)

    print(f"Saving to {args.outfpath}")

    corefdb.save(db, args.outfpath)


if __name__ == '__main__':
    main()

