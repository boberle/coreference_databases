# The `ancor` directory

## List of files

The whole corpus, annotated with syntax and named entity information as described in the root README file, in the CoNLL format, is saved in the `ancor_orig_with_ner.conll` file.

The splits used to train and evaluate ODACR and [COFR](https://github.com/boberle/cofr), as described in the LREC 2020 paper, are saved in the `ancor_orig_sg.{dev,test,train}.conll` files.  For [COFR](https://github.com/boberle/cofr), "sentences" (or rather speech turns, as there is no sentence in Ancor) have been split at "euh" interjections when they were longer than 100 tokens.  This version is saved in the `ancor_orig_sg_splitsent100.{dev,test,train}.jsonlines` files.

The datebase format is saved in the `db_ancor.zip`, with the complete list of annotations and fields described in the root README file.

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

This work is adapted from the Ancor-Centre corpus, which is freely available from the [corpus website](http://www.info.univ-tours.fr/~antoine/parole_publique/ANCOR_Centre/index.html).

The corpus is described in the following papers:

> Muzerelle J., Lefeuvre A., Schang E., Antoine J.-Y, Pelletier A., Maurel D., Eshkol I., Villaneau J. 2014. ANCOR-Centre, a Large Free Spoken French Coreference Corpus: description of the Resource and Reliability Measures. _LREC'2014, 9th Language Resources and Evaluation Conference_

> Muzerelle J., Lefeuvre A., Antoine J.-Y., Schang E., Maurel D., Villaneau J., Eshkol I. 2013. ANCOR : premier corpus de français parlé d'envergure annoté en coréférence et distribué librement. _Actes TALN'2013._

It is released under the terms of the [Creative Commons CC-BY-SA-NC](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.en) license for the ESLO part, and the [Creative Commons CC-BY-SA](https://creativecommons.org/licenses/by-sa/4.0/deed.en) license for the rest.  The legal text of the licences are to be found [here](https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode) and [here](https://creativecommons.org/licenses/by-sa/4.0/legalcode).

The modified work (the files in this directory) are released under the terms of the same license as the original work.  If you use them, you must give appropriate credit to the original authors by citing the papers mentionned above and to Rodrigo Wilkens and myself.

Please see the root README file for more details and more legal stuff.
