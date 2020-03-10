"""
Collection of function to add properties to a class (eg Token):
- is_noun
- is_nominal
- is_punct
- etc.

"""


# if deplabel is one of these, then it is a clause
CLAUSE_DEPLABELS = ('csubj', 'ccomp', 'xcomp', 'advcl', 'acl',)


# if deplabel is one of these, then it is a subject/object/non-core (like an
# adverbial).  These are attached to verbs
SUBJECT_DEPLABELS = ('nsubj', 'csubj',)
OBJECT_DEPLABELS = ('obj', 'iobj', 'ccomp', 'xcomp',)
NON_CORE_DEPLABELS = ('obl', 'vocative', 'expl', 'dislocated', 'advcl',)


DEPENDENT_DEPLABELS = (
    'nmod',         # a noun: genitive ("'s") preposition "of"; in French:
                    # "la roue de la voiture", etc.
    'appos',        # apposition: Sam, my brother, reads...
    'nummod',       # numeric modifier, either a det (some are tagged det)
                    # or an object like "he spent $40"
    'acl',          # clausal modifier "Cette affaire à suivre.",
                    # "I have a parakeet named cookie"
                    # For relative clause, the subdeplabel is "acl:relcl"
    'amod',         # an adjective
)


# this is based on analysis of "determiner_string"s in Dem1921 and Ancor
DET_TYPE_DIC = { word: type_
   for type_, words in {
      "bare": "",
      "def-art": ["l", "l'", "la", "le", "les", "du" ],
      "def-quant": ["tous", "tout", "toute", "toute une", "toutes", "toutes les"],
      "def-gen": ["def-poss", "", "leur", "leurs", "ma", "mes", "mon", "vos", "votre", "tes", "ton", "ta", "sa", "ses", "son", "notre", "nos"],
      "def-dem": ["ces", "cet", "cette", "ce"],
      "ind-art": ["de", "d'", "de", "des", "un", "une"],
      "ind-quant": ["trop d'", "très d'", "très de", "quelqu'", "quelque", "quelques", "peu", "peu d'", "peu de", "peu peu", "plus", "plus de", "plus en plus de", "plusieurs", "peu", "peu de", "assez de", "autant presque de", "beaucoup", "beaucoup d'", "beaucoup de", "beaucoup de de", "certaines", "certains", "chaque", "le moins"],
      "ind-other": ["tel", "telle", "telles", "quels", "quel", "quelle", "quelles", "importe", "importe quel", "importe quelle", "divers", "diverses"],
      "neg": ["aucun", "aucune", "pas de", "nul"]}.items()
   for word in words
}



def set_tagset(cls):

    cls.is_noun = property(lambda self: self.pos in ('NOUN', 'PROPN'))

    cls.is_cnoun = property(lambda self: self.pos in ('NOUN',))

    cls.is_pnoun = property(lambda self: self.pos in ('PROPN',))

    cls.is_pronoun = property(lambda self: self.pos in ('PRON',))

    cls.is_nominal = \
        property(lambda self: self.pos in ('NOUN', 'PROPN', 'PRON'))

    cls.is_adjective = property(lambda self: self.pos in ('ADJ',))

    cls.is_adverb = property(lambda self: self.pos in ('ADV',))
    
    cls.is_punct = \
        property(lambda self: self.pos in ('PUNCT',))

    cls.is_preposition = \
        property(lambda self: self.pos in ('ADP',))

    cls.is_conjuction = \
        property(lambda self: self.pos in ('SCONJ', 'CCONJ'))

    cls.is_fixed_rel = \
        property(lambda self: self.deplabel == "fixed")

    cls.is_case_rel = \
        property(lambda self: self.deplabel == "case")

    cls.is_relative_pronoun = \
        property(lambda self: self.pos == "PRON" and self['PronType'] == "Rel")

    cls.is_copula = property(lambda self: self.deplabel == "cop")

    cls.is_reciprocal = property(lambda self: self['PronType'] == "Rcp" \
            or (self.pos == "PRON" and self.lemma == "se"))

    cls.is_reflexive = property(lambda self: self['Reflex'] == "Yes" \
            or (self.pos == "PRON" and self.lemma == "se"))

    cls.is_expletive = property(lambda self: self.deplabel == "expl" \
        or self.deplabel.startswith("expl:"))

    @property
    def has_relative_pronoun(self):
        for child in self.children:
            if child.is_relative_pronoun:
                return True
        return False
    cls.has_relative_pronoun = has_relative_pronoun

    @property
    def is_complement(self):
        for child in self.children:
            #if child.lemma == "être" and child.pos == "AUX":
            if child.deplabel == "cop":
                return True
        return False
    cls.is_complement = is_complement

    @property
    def is_apposition_strict(self):
        if self.deplabel in ("acl", "appos") \
                and self.children and self.children[0].is_punct:
            return True
    cls.is_apposition_strict = is_apposition_strict

    @property
    def is_apposition(self):
        if self.deplabel in ("acl", "appos"):
            return True
    cls.is_apposition = is_apposition


    cls.is_verb = property(lambda self: self.pos in ("VERB",))

    @property
    def is_verb_without_subject(self):
        if self.pos == "VERB":
            for child in self.children:
                if child.is_subject:
                    return False
            return True
        return False
    cls.is_verb_without_subject = is_verb_without_subject


    cls.is_subject = property(lambda self: self.deplabel in SUBJECT_DEPLABELS)

    cls.is_object = property(lambda self: self.deplabel in OBJECT_DEPLABELS)

    cls.is_non_core = property(lambda self: self.deplabel in NON_CORE_DEPLABELS)

    cls.is_clause = property(lambda self: self.deplabel in CLAUSE_DEPLABELS)

    cls.is_dependent = property(
        lambda self: self.deplabel in DEPENDENT_DEPLABELS)

    cls.dependent_type = property(
        lambda self: 'noun' if self.deplabel == 'nmod' else
            'appos' if self.deplabel == 'appos' else
            'num' if self.deplabel == 'nummod' else
            'clause' if self.deplabel == 'acl' else
            'adj' if self.deplabel == 'amod' else
            None
    )



    # Note on determiners:
    # --- French ---
    # The deplabel is `det`.  The possessive is marked with the feature
    # `Poss=Yes`.  Prefer the det label because the determiner may be an
    # adverbial like "beaucoup de"
    # --- English ---
    # The deplabel is `det` but in for the possessive it may be `nmod`:
    # - the possessive determiner like "my": the deplabel is `nmod:poss` (the
    #   pos is `DET` or `PRON`)
    # - the genitive ('s): the deplabel is also `nmod:poss`

    cls.is_determiner = property(
        lambda self: self.deplabel == "det"
            or (self.deplabel == 'nmod' and self.subdeplabel == 'poss')
    )

    cls.is_possessive_determiner = property(
        lambda self: (self.deplabel == "det" and self['Poss'] == "Yes")
            or (self.deplabel == 'nmod' and self.subdeplabel == 'poss')
    )

    cls.is_genitive_determiner = property(
        lambda self: self.deplabel == 'nmod'
            and self.subdeplabel == 'poss'
            and not self.pos in ("DET", "PRON")
    )





    cls.is_aux_passive = property(
        lambda self: self.deplabel == 'aux'
            and self.subdeplabel == 'pass'
    )



    cls.is_aux_passive = property(
        lambda self: self.deplabel == 'aux'
            and self.subdeplabel == 'pass'
    )


    cls.determiner_type = property(
        lambda self: DET_TYPE_DIC.get(self.determiner_string, None)
    )


