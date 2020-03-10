"""
Note: use the `Annotable.reset_counter()` method to reset the counter if you
plan to pass several corpora and you do mind having large index number.
"""


import pandas as pd

import corefdb


class Annotable:

    #_class_annotation_list = [] # not here, but in __init__
    _id_counter = 0

    @classmethod
    def reset_counter(cls):
        cls._id_counter = 0

    def __init__(self, **kwargs):
        self.id_ = self.__class__._id_counter
        self.__class__._id_counter += 1
        self.annotations = dict()
        if kwargs:
            self.annotations.update(kwargs)

    @property
    def id(self):
        """Alias for `id_`."""
        return self.id_

    def __setitem__(self, key, value):
        self.annotations[key] = value

    def __getitem__(self, key):
        return self.annotations[key]

    def __contains__(self, key):
        return key in self.annotations

    def __getattr__(self, attr):
        if attr in self.annotations:
            return self.annotations[attr]
        raise AttributeError("%s has no attribute '%s'"
            % (self.__class__.__name__, attr))



class Text(Annotable):

    def __init__(self, id_=None, **kwargs):
        super().__init__(**kwargs)
        self.paragraphs = []
        if id_:
            self.id_ = id_
        self.chains = []

    def add_paragraph(self, paragraph):
        self.paragraphs.append(paragraph)

    def add_chain(self, chain):
        self.chains.append(chain)


class Paragraph(Annotable):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sentences = []

    def add_sentence(self, sentence):
        self.sentences.append(sentence)


class Sentence(Annotable):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tokens = []
        self.mentions = []

    def add_token(self, token):
        self.tokens.append(token)

    def add_mention(self, mention):
        self.mentions.append(mention)



class Token(Annotable):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)



class Mention(Annotable):


    @staticmethod
    def sort(mentions):
        mentions.sort(key=lambda x: x['text_stop'], reverse=True)
        mentions.sort(key=lambda x: x['text_start'])

    @staticmethod
    def add_levels(mentions):
        Mention.sort(mentions)
        filo = []
        for mention in mentions:
            while filo and filo[-1].text_stop <= mention.text_start:
                filo.pop()
            if filo:
                assert mention.text_start < filo[-1].text_stop
            mention['level'] = len(filo)
            mention['parent'] = filo[-1].id_ if filo else None
            filo.append(mention)
        for mention in mentions:
            mention['is_outer'] = mention['level'] == 0



    def __init__(self, **kwargs):
        super().__init__(**kwargs)



class Chain(Annotable):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._mentions = []
        self._mentions_are_sorted = False

    @property
    def mentions(self):
        if not self._mentions_are_sorted:
            Mention.sort(self._mentions)
            self._mentions_are_sorted = True
        return self._mentions

    def add_mention(self, mention):
        self._mentions.append(mention)
        self._mentions_are_sorted = False




class Corpus:

    def __init__(self):
        self.token_df = None
        self.sentence_df = None
        self.paragraph_df = None
        self.text_df = None
        self.mention_df = None
        self.chain_df = None
        self._df_initialized = False


    @property
    def df_dic(self):
        return {
            name[:-3] + "s": getattr(self, name)
            for name in self.__dir__() if name.endswith("_df")
        }


    def add_text(self, text):
        self._count(text)

        data = (
            ('token', (tok for par in text.paragraphs for sent in par.sentences
                for tok in sent.tokens)),
            ('sentence', (sent for par in text.paragraphs
                for sent in par.sentences)),
            ('paragraph', (par for par in text.paragraphs)),
            ('mention', (mention for chain in text.chains
                for mention in chain.mentions)),
            ('chain', (chain for chain in text.chains)),
            ('text', (text, ))
        )

        for attr, items in data:
            attr += "_df"
            items = list(items)
            df = pd.DataFrame(
                data=[item.annotations for item in items],
                index=[item.id_ for item in items],
            )
            df.index.name = "id"
            if getattr(self, attr) is not None:
                df = pd.concat([getattr(self, attr), df], axis=0)
            setattr(self, attr, df)


    def _count(self, text):

        # indices
        text_sent_index = 0
        text_cumulative_token_count = 0
        text_mention_index = 0
        for text_par_index, par in enumerate(text.paragraphs):
            par['text_id'] = text.id_
            par['text_par_index'] = text_par_index
            par_sent_index = 0
            par_mention_index = 0
            par_cumulative_token_count = 0
            par['first_token_index'] = text_cumulative_token_count
            for par_sent_index, sent in enumerate(par.sentences):
                sent['text_id'] = text.id_
                sent['par_id'] = par.id_
                sent['text_par_index'] = text_par_index
                sent['text_sent_index'] = text_sent_index
                sent['par_sent_index'] = par_sent_index
                sent['first_token_index'] = text_cumulative_token_count
                for sent_token_index, token in enumerate(sent.tokens):
                    token['text_token_index'] \
                        = text_cumulative_token_count + sent_token_index
                    token['text_id'] = text.id_
                    token['par_id'] = par.id_
                    token['sent_id'] = sent.id_
                mentions = sent.mentions
                Mention.sort(mentions)
                for sent_mention_index, mention in enumerate(mentions):
                    mention['text_id'] = text.id_
                    mention['par_id'] = par.id_
                    mention['sent_id'] = sent.id_
                    mention['text_par_index'] = text_par_index
                    mention['text_sent_index'] = text_sent_index
                    mention['par_sent_index'] = par_sent_index
                    mention['sent_mention_index'] = sent_mention_index
                    mention['par_mention_index'] = par_mention_index
                    mention['text_mention_index'] = text_mention_index
                    mention['par_start'] \
                        = par_cumulative_token_count + mention.start
                    mention['par_stop'] \
                        = par_cumulative_token_count + mention.stop
                    mention['text_start'] \
                        = text_cumulative_token_count + mention.start
                    mention['text_stop'] \
                        = text_cumulative_token_count + mention.stop
                    # increment
                    par_mention_index += 1
                    text_mention_index += 1
                # increment
                text_sent_index += 1
                par_cumulative_token_count += len(sent.tokens)
                text_cumulative_token_count += len(sent.tokens)
                sent['last_token_index'] = text_cumulative_token_count
            par['last_token_index'] = text_cumulative_token_count

        # chains and mentions, including "rank".  Rank means the 1st,
        # 2st... mention of the chain in the text, paragraph, sentence.
        for chain in text.chains:
            chain['text_id'] = text.id_
            text_counter = 0
            par_counter = 0
            sent_counter = 0
            last_par = None
            last_sent = None
            mentions = chain.mentions # sorted
            for i, mention in enumerate(mentions):
                mention['chain_id'] = chain.id_
                mention['text_mention_rank'] = text_counter
                text_counter += 1
                if mention['par_id'] != last_par:
                    last_par = mention['par_id']
                    par_counter = 0
                mention['par_mention_rank'] = par_counter
                par_counter += 1
                if mention['sent_id'] != last_sent:
                    last_sent = mention['sent_id']
                    sent_counter = 0
                mention['sent_mention_rank'] = sent_counter
                sent_counter += 1
                mention['chain_mention_index'] = i
                mention['chain_mention_rindex'] = len(mentions) - i - 1


        mentions = [m for chain in text.chains for m in chain.mentions]
        Mention.add_levels(mentions)

    def export_to_csv_zip(self, fpath, compression=True):
        corefdb.save(self.df_dic, fpath, compression=compression)


