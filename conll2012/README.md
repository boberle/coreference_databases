# The `conll2012` directory

Because the OntoNotes corpus, from which the CoNLL-2012 corpus is derived, is distributed with a license whichi forbid redistribution, you will need to download the data yourself for the LDC and CoNLL-2012 shared task, and then compile your self the database.

The `db_conll_trial_data_only_with_masked_strings.zip` contains a sample datebase made with the trial data available from the [CoNLL-2012 shared task website](http://conll.cemantix.org/2012/).  I have replaced all the tokens from the `mentions` and `tokens` tables by the string `[token]` so that the original text cannot be reconstructed without the original work.

