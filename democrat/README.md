# The `democrat` directory

## List of files

The whole corpus (all the texts, including Old French), with the original tokenization and sentence splitting, is avalaible in the `dem_all_corrected.conll` file.

The five legal texts from the 19th and 21st centuries, with parsing (as described in the root README file) but without named entities, is saved in the `demjur_parsed_corrected.conll` file.  These texts, with the original tokenization and sentence splitting, are also available in the `demjur_base.conll` file.

The datebase format, with only the base annotation (field marked with a green circle in the root README file), is saved in the `db_dem_all_corrected_base.zip` file (for the whole corpus) and in the `db_demjur_base.zip` file (for the legal texts).

## Formats

See the root README file for details.  Here is just a reminder of the
conll columns.  For the whole corpus and the non parsed legal texts, the
format is the original CoNLL-2012 format:

```
1.    Document ID
2.    Part number
3.    Word number
4.    Word
5.    Part of Speech
6.    Parse bit
7.    Lemma
8.    Predicate Frameset ID
9.    Word sense
10.   Speaker/Author
11.   Named Entities
12:N. Predicate Arguments
N.    Coreference
```

For the parsed legal texts, it is an extension of CoNLL-U:

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

The modified work (the files in this directory) are released under the terms of the same license as the original work.  If you use it, you must give appropriate credit to the original authors by citing the papers mentionned above and to myself.

Please see the root README file for more details and more legal stuff.
