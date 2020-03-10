import coreftools.formats.conll
from ..annotable import Corpus, Text, Paragraph, Sentence, Token, Mention, Chain



def build_db(*infpaths, outfpath=None, key_callback=None, word_col=3,
        add_mention_string=True, compression=True, sep=None, par_col=None,
        ignore_double_indices=False, ignore_comments=True):

    raw_docs = coreftools.formats.conll.read_files(
        *infpaths,
        sep=sep,
        ignore_comments=ignore_comments,
        ignore_double_indices=ignore_double_indices,
        key_callback=key_callback,
    )
    corpus = Corpus()

    # to check that there is no duplicated key
    used_keys = set()

    for i, raw_doc in enumerate(raw_docs):

        if i and i % 100 == 0:
            print("Done %d documents." % i)

        if raw_doc.key in used_keys:
            raise RuntimeError(f"duplicated doc key {raw_doc.key}")
        used_keys.add(raw_doc.key)

        raw_doc.compute_mentions_n_chains()
        text = Text(id_=raw_doc.key)
        par = Paragraph()
        text.add_paragraph(par)
        raw_mentions2annotable_mentions = dict()

        last_par = None

        for raw_sent in raw_doc.sentences:

            sent = Sentence()

            if par_col is not None:
                cur_par = int(raw_sent.tokens[0][par_col])
                if last_par is None:
                    pass
                elif last_par != cur_par:
                    par = Paragraph()
                    text.add_paragraph(par)
                last_par = cur_par
            par.add_sentence(sent)

            for raw_token in raw_sent.tokens:
                token = Token()
                if word_col is not None:
                    token['string'] = raw_token[word_col]
                sent.add_token(token)

            if word_col:
                words = list(raw_sent.iter_tokens(word_col))
            for raw_mention in raw_sent.mentions:
                mention = Mention(
                    start=raw_mention.start,
                    stop=raw_mention.stop,
                    text_start=raw_mention.text_start,
                    text_stop=raw_mention.text_stop,
                )
                if word_col and add_mention_string:
                    mention['string'] = \
                        " ".join(words[raw_mention.start:raw_mention.stop])
                raw_mentions2annotable_mentions[raw_mention] = mention
                sent.add_mention(mention)

        for raw_chain in raw_doc.chains:
            chain = Chain()
            for raw_mention in raw_chain:
                chain.add_mention(raw_mentions2annotable_mentions[raw_mention])
            text.add_chain(chain)

        corpus.add_text(text)

    if outfpath:
        corpus.export_to_csv_zip(outfpath, compression=compression)

    return corpus.df_dic


