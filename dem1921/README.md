# The `dem1921` directory

## List of files

_Dem1921_ is a subset of the Democrat corpus, containing all the texts from the 19th to the 21st centuries, except the five legal texts.

The whole subcorpus, annotated with syntax and named entity information, as described in the root README file, in the CoNLL format, is saved in the `dem1921_v1_parsed_corrected_byhand_lemmatized_with_ner.conll` file.

The splits used to train and evaluate ODACR and [COFR](http://github.com/boberle/cofr), as described in the LREC 2020 paper cited below, are saved in the `dem1921_sg.{dev,test,train}.conll` files.  For [COFR](http://github.com/boberle/cofr), the 10k word-long documents have been split into 2k word-long documents, available in the `dem1921_sg_cut2000.{dev,test,train}.{conll,jsonlines}` files.

The datebase format is saved in the `db_dem1921.zip`, with the complete list of annotations and fields described in the root README file.

The LREC 2020 paper:

> [Wilkens Rodrigo, Oberle Bruno, Landragin Frédéric, Todirascu Amalia (2020). **French coreference for spoken and written language**, _Proceedings of the 12th Edition of the Language Resources and Evaluation Conference (LREC 2020)_, Marseille, France](https://lrec2020.lrec-conf.org/en/).

## Formats

See the root README file for details.  Here is a reminder of the columns for the conll format:

1. **index** of the token in the sentence
1. **form** of the token
1. **lemma** of the token
1. universal **part-of-speech** tag.
1. always `_` (language-specific part-of-speech tag, not used)
1. **morphological features** (see [universal dependencies](https://universaldependencies.org))
1. **head** of the current token (an **index** of another word or 0 for root)
1. universal **dependency relation** to the **head** (or `root`) (see [universal dependencies](https://universaldependencies.org))
1. always `_` (enhanced dependencies, not used)
1. always `_` (other annotation, not used)
1. speaker (or `_` for Democrat, where no speaker is recorded)
1. paragraph number
1. named entity in the format `(PER * * *)` (ex. with 4 tokens)
1. named entity in the format `(PER PER PER PER)` (ex. with 4 tokens)
1. coreference in conll-2012 style



## License

This work is adapted from the Democrat corpus, which is freely available from the [ortolang website](http://ortolang.fr).

The corpus is described in the following paper:

> Frédéric Landragin. Description, modélisation et détection automatique des chaînes de référence (DEMOCRAT). _Bulletin de l'Association Française pour l'Intelligence Artificielle, AFIA, 2016, pp.11-15._

It is released under the terms of the [Creative Commons CC-BY-SA](https://creativecommons.org/licenses/by-sa/4.0/deed.en) license, which can be read in full [here](https://creativecommons.org/licenses/by-sa/4.0/legalcode).

The modified work (the files in this directory) are released under the terms of the same license as the original work.  If you use it, you must give appropriate credit to the original authors by citing the paper mentionned above and to myself.

Please see the root README file for more details and more legal stuff.
