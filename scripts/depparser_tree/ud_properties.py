"""
TODO: Put some explanations here.
"""


def set_tagset(cls):


    @staticmethod
    def get_head(tokens):
        """Return the highest (lowest level) node in `tokens`.

        Punctuation is excluded from the tokens.
        """
        new_tokens = [t for t in tokens if not t.is_punct]
        if new_tokens:
            tokens = new_tokens
        upper = tokens[0]
        upper_level = upper.level
        for token in tokens[1:]:
            if token.level < upper_level:
                upper_level = token.level
                upper = token
        return upper
    cls.get_head = get_head


    ##### parents, clauses, depths, etc. ###################################


    cls.parent_pos = \
        property(lambda self: self.parent.pos if self.parent else None)


    cls.parent_deplabel = \
        property(lambda self: self.parent.deplabel if self.parent else None)


    cls.parent_subdeplabel = \
        property(lambda self: self.parent.subdeplabel if self.parent else None)


    @property
    def parent_clause(self):
        parent = self.parent
        while parent:
            if parent.is_clause:
                return parent
            parent = parent.parent
        return None
    cls.parent_clause = parent_clause


    @property
    def parent_clause_pos(self):
        clause = self.parent_clause
        return clause.pos if clause else None
    cls.parent_clause_pos = parent_clause_pos


    @property
    def parent_clause_deplabel(self):
        clause = self.parent_clause
        return clause.deplabel if clause else None
    cls.parent_clause_deplabel = parent_clause_deplabel


    @property
    def parent_clause_subdeplabel(self):
        clause = self.parent_clause
        return clause.subdeplabel if clause else None
    cls.parent_clause_subdeplabel = parent_clause_subdeplabel


    @property
    def parent_clause_id(self):
        clause = self.parent_clause
        return clause.id_ if clause else None
    cls.parent_clause_id = parent_clause_id


    @property
    def preposition(self):
        for child in self.children:
            if child.is_preposition:
                return child
        return None
    cls.preposition = preposition


    cls.in_pp = property(lambda self: bool(self.preposition))


    cls.node_depth = property(lambda self: self.level)


    @property
    def clause_depth(self):
        counter = 0
        for parent in self.parents:
            if parent.is_clause:
                counter += 1
        return counter
    cls.clause_depth = clause_depth


    cls.is_in_main_clause = property(lambda self: not self.parent_clause)


    cls.is_in_embedded = property(lambda self: bool(self.parent_clause))


    @property
    def is_in_matrix(self):
        """True if the is no embedded clause in the sentence."""
        for descendant in self.root.descendants:
            if descendant.is_clause:
                return False
        return True
    cls.is_in_matrix = is_in_matrix

    ##### dependents #######################################################

    @property
    def dependent_count(self):
        counter = 0
        for child in self.children:
            if child.dependent_type:
                counter += 1
        return counter
    cls.dependent_count = dependent_count


    @property
    def predependent_count(self):
        counter = 0
        for child in self.left_children:
            if child.dependent_type:
                counter += 1
        return counter
    cls.predependent_count = predependent_count


    @property
    def postdependent_count(self):
        counter = 0
        for child in self.right_children:
            if child.dependent_type:
                counter += 1
        return counter
    cls.postdependent_count = postdependent_count


    @property
    def dependent_dict(self):
        if not hasattr(self, '_dependent_dict'):
            self._dependent_dict = dict(
                noun=0,
                appos=0,
                num=0,
                clause=0,
                adj=0,
            )
            for child in self.children:
                type_ = child.dependent_type
                if type_ in self._dependent_dict:
                    self._dependent_dict[type_] += 1
        return self._dependent_dict
    cls.dependent_dict = dependent_dict


    cls.noun_dependent_counter = property(
        lambda self: self.dependent_dict['noun'])


    cls.appos_dependent_counter = property(
        lambda self: self.dependent_dict['appos'])


    cls.num_dependent_counter = property(
        lambda self: self.dependent_dict['num'])


    cls.clause_dependent_counter = property(
        lambda self: self.dependent_dict['clause'])


    cls.adjective_dependent_counter = property(
        lambda self: self.dependent_dict['adj'])


    ##### determiner #######################################################

    @property
    def determiner(self):
        for child in self.children:
            if child.is_determiner:
                return child
        return None
    cls.determiner = determiner

    
    @property
    def determiner_string(self):
        det = self.determiner
        if det:
            return " ".join(det.text)
        return None
    cls.determiner_string = determiner_string


    @property
    def determiner_head_string(self):
        det = self.determiner
        return det.form if det else None
    cls.determiner_head_string = determiner_head_string


    @property
    def determiner_head_lemma(self):
        det = self.determiner
        return det.lemma if det else None
    cls.determiner_head_lemma = determiner_head_lemma


    @property
    def has_genitive_determiner(self):
        det = self.determiner
        return det.is_genitive_determiner if det else False
    cls.has_genitive_determiner = has_genitive_determiner


    @property
    def has_complex_determiner(self):
        det = self.determiner
        return len(list(det.leaves)) > 1 if det else False
    cls.has_complex_determiner = has_complex_determiner


    ##### head #############################################################


    @property
    def h_broad_pspeech(self):
        """WordNet-like POS: n/p/d for noun/pro/det, and else like WN or None.
        """
        if self.is_noun:
            return 'n'
        if self.is_pronoun:
            return 'p'
        if self.is_determiner:
            return 'd'
        if self.is_verb:
            return 'v'
        if self.is_adjective:
            return 'a'
        if self.is_adverb:
            return 'r'
        return None
    cls.h_broad_pspeech = h_broad_pspeech


    cls.h_noun_type = property(
        lambda self: 'pnoun' if self.is_pnoun
            else 'cnoun' if self.is_cnoun
            else None
    )

    cls.h_person = property(lambda self: self.get("Person"))

    cls.h_pronoun_type = property(lambda self: self.get("PronType"))

    cls.h_number = property(lambda self: self.get("Number"))

    cls.h_gender = property(lambda self: self.get("Gender"))

    cls.h_reflex = property(lambda self: self.get("Reflex"))

    cls.h_poss = property(lambda self: self.get("Poss"))

    cls.h_definite = property(lambda self: self.get("Definite"))

    cls.h_start = property(lambda self: self.index)
    cls.h_stop = property(lambda self: self.index+1)


    ##### structure ########################################################

    cls.is_arg = property(
        lambda self: self.is_subject or self.is_object or self.is_non_core)


    @property
    def parent_verb(self):
        for parent in self.parents:
            # for copula:
            for child in parent.children:
                if child.deplabel == 'cop':
                    return parent
            if parent.is_verb:
                return parent
        return None
    cls.parent_verb = parent_verb


    @property
    def struct_id(self):
        parent_verb = self.parent_verb
        if parent_verb:
            return parent_verb.id_
        return None
    cls.struct_id = struct_id


    @property
    def arg_index(self):
        parent = self.parent
        if parent:
            counter = 0
            for child in self.parent.children:
                if child is self:
                    return counter
                if child.is_subject or child.is_object or child.is_non_core:
                    counter += 1
        return None
    cls.arg_index = arg_index


    cls.arg_type = property(
        lambda self: 'subj' if self.is_subject
            else 'obj' if self.is_object else 'non' if self.is_non_core
            else None)


    ##### other informations ############################################### 


    @property
    def struct_is_negative(self):
        parent_verb = self.parent_verb
        if parent_verb:
            for child in parent_verb.children:
                # English:
                if child.pos == "PART" and child.lemma.lower() == "not":
                    return True
                # French:
                elif child.pos == "ADV" and child["Polarity"] == "Neg":
                    return True
            return False
        return None
    cls.struct_is_negative = struct_is_negative


    @property
    def struct_is_passive(self):
        parent_verb = self.parent_verb
        if parent_verb:
            for child in parent_verb.children:
                if child.is_aux_passive:
                    return True
            return False
        return None
    cls.struct_is_passive = struct_is_passive


    @property
    def struct_tense(self):
        parent_verb = self.parent_verb
        if parent_verb:
            return parent_verb.get('Tense', None)
        return None
    cls.struct_tense = struct_tense


    @property
    def struct_mood(self):
        parent_verb = self.parent_verb
        if parent_verb:
            return parent_verb.get('Mood', None)
        return None
    cls.struct_mood = struct_mood


    @property
    def struct_person(self):
        parent_verb = self.parent_verb
        if parent_verb:
            return parent_verb.get('Person', None)
        return None
    cls.struct_person = struct_person

