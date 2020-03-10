"""
This module parses the Penn TreeBank sentence format used in Conll-2012, where
each each token is on a separate line.  This is useful to pair token and other
informations, like lemmata or named entity boundaries indentified by token
indices.

The `TreeParser` class builds a series of `Node`s representing each level of
the tree: root, clauses, phrases, down to tokens.  `Node`s may be associated to
individual mention (whatever their level: token, phrase, etc.) to compute
attributes like head lemma, head part of speech, the type of mention (phrase,
word), modifiers, etc.; but also to compute relation attributes: are mentions
in the same phrase, clause, sentence, etc.

How to call?
------------

From the conll file, you need:
- word col (`word_col`)
- part of speech col (`pspeech_col`)
- tree col (`tree_col`)
- lemma col (`lemma_col`)

First you need to prepare the data:

(1) join the tree col and add a space before the stars:

    tree_string = "\n".join(tree_col).replace('*', ' *')

(2) replace unknown or same-as-word lemmata by the actual word:

    lemma_col = [
        l if (l and l != '-') else w for w, l in zip(word_col, lemma_col)
    ]

Second, call the parser:

    parser = TreeParser(
        tree_string,
        list(zip(pspeech_col, word_col, lemma_col)),
    )
    parser.parse()
    root = parser.root
    node_list = parser.node_list

Now you browse the tree with `root`, or 




Linguistics
-----------

The module defines a list of tagsets: for clause, phrase, pronoun, etc.  See
the "constituent tree notes" auxiliary document for more information about the
origin and the linguistic context.  See here:
http://www.surdeanu.info/mihai/teaching/ista555-fall13/readings/PennTreebankConstituents.html

For the POS tagset, see the "Part of speech notes" auxiliary document.  Note
here that:
* the `DEFINITE_DET_WORDS` set is defined by myself,
* the `coarse_grained_pos` are derived from the Universal Tag Set proposed by
  PetrovDipanjanMcDonald-2012.

Each `Node` defines some properties useful for mention annotation.  The
motivation and rationale for each is to be found in the docstring of each
property.
"""

CLAUSE_TAGS = { 'S', 'SBAR', 'SBARQ', 'SINV', 'SQ' }
PHRASE_TAGS = { 'ADJP', 'ADVP', 'CONJP', 'FRAG', 'INTJ', 'LST', 'NAC', 'NP',
    'NX', 'PP', 'PRN', 'PRT', 'QP', 'RRC', 'UCP', 'VP', 'WHADJP', 'WHAVP',
    'WHNP', 'WHPP', 'X',
    'NML' # added NML (coordination)
    }

PRONOUN_TAGS = { 'PRP', 'PRP$', 'WP ', 'WP$', }
NOUN_TAGS = { 'NN', 'NNS', 'NNP', 'NNPS' }
CNOUN_TAGS = { 'NN', 'NNS', }
PNOUN_TAGS = { 'NNP', 'NNPS', }
ADJECTIVE_TAGS = { 'JJ', 'JJR', 'JJS', }

# see document on determiners
DETERMINATIVE_TAGS = { 'DT', 'CD', 'PDT', 'PRP$', 'WDT' }
DEFINITE_DET_WORDS = { 'the', 'this', 'that', 'these', 'those',
    'my', 'your', 'his', 'her', 'its', 'our', 'their', 'both' }

PLURAL_TAGS = { 'NNS', 'NNPS' }

POSSESSIVE_TAGS = {"PRP$", "WP$", }
DEFINITE_ARTICLE_WORDS = {"the",}
INDEFINITE_ARTICLE_WORDS = {"a", "an"}
DEMONSTRATIVE_DETERMINER_WORDS = {"this", "these", "that", "those"}
EXHAUSTIVE_DETERMINER_WORDS = {"all", "every", "each"}
INDEFINITE_QUANDITIFIER_WORDS = {"half", "many", "several", "both", "some",
    "most"}
NEGATIVE_DETERMINER_WORDS = {"no", "none", "neither"}
CARDINAL_TAGS = {"CD",}
INTERROGATIVE_DETERMINER_TAGS = {"WDT",}
QUANTIFIER_PHRASE = {"QP",}

#COARSE_PSPEECH = {fine:coarse
#    for coarse, fines in {
#        'VERB':{ 'MD', 'VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ', },
#        'NOUN':{ 'NN', 'NNS', 'NNP', 'NNPS', },
#        'PRON':{ 'PRP', 'PRP$', 'WP', 'WP$', },
#        'ADJ':{ 'JJ', 'JJR', 'JJS', },
#        'ADV':{ 'RB', 'RBR', 'RBS', 'WRB', },
#        'ADP':{ 'IN' },
#        'CONJ':{ 'CC' },
#        'DET':{ 'DT', 'EX', 'PDT', 'WDT', },
#        'NUM':{ 'CD' },
#        'PRT':{ 'POS', 'RP', 'TO', },
#        'X':{ 'FW', 'LS', 'SYM', 'UH', }}.items()
#        for fine in fines }
#COARSE_DEFAULT = 'PUNCT' # = punctuation

def ptb2ud(ptb_pos):
    # https://universaldependencies.org/tagset-conversion/en-penn-uposf.html
    return {
        "#": "SYM",
        "$": "SYM",
        "''": "PUNCT",
        ",": "PUNCT",
        "-LRB-": "PUNCT",
        "-RRB-": "PUNCT",
        ".": "PUNCT",
        ":": "PUNCT",
        "AFX": "ADJ",
        "CC": "CCONJ",
        "CD": "NUM",
        "DT": "DET",
        "EX": "PRON",
        "FW": "X",
        "HYPH": "PUNCT",
        "IN": "ADP",
        "JJ": "ADJ",
        "JJR": "ADJ",
        "JJS": "ADJ",
        "LS": "X",
        "MD": "VERB",
        "NIL": "X",
        "NN": "NOUN",
        "NNP": "PROPN",
        "NNPS": "PROPN",
        "NNS": "NOUN",
        "PDT": "DET",
        "POS": "PART",
        "PRP": "PRON",
        "PRP$": "DET",
        "RB": "ADV",
        "RBR": "ADV",
        "RBS": "ADV",
        "RP": "ADP",
        "SYM": "SYM",
        "TO": "PART",
        "UH": "INTJ",
        "VB": "VERB",
        "VBD": "VERB",
        "VBG": "VERB",
        "VBN": "VERB",
        "VBP": "VERB",
        "VBZ": "VERB",
        "WDT": "DET",
        "WP": "PRON",
        "WP$": "DET",
        "WRB": "ADV",
        "``": "PUNCT",
    }.get(ptb_pos, None)


def _count(items):
    counter = 0
    for item in items:
        counter += 1
    return counter

_CURRENT_ID = 0



class Node:
    """Represent a Node in a Conll-2012 parse tree.
    
    Each node is characterized by some attributes, usually on the form of
    properties (see under each properties).  General attributes are explained
    below.

    Attributes
    ----------
    parent: Node
        The parent node, or None if the node is the root.
    start: int
        The index of the first token of the node.
    stop: int
        The index of the token **after** the last token of the node.  Use the
        `end` attribute to get the index of the last token.
    content: `list|str`
        If the node is a leaf: the content string (the word(s)/token(s)).
        If the node is not a leaf: a list of child `Node`.  This should be set
        only with the `add_string()` and `add_child()` methods, not directly.
    """

    _counter = 0

    def __init__(self, tag, content=None, lemma=None):
        self.id_ = self.__class__._counter
        self.__class__._counter += 1
        self._tag = ""
        self._function_tag = ""
        self.tag = tag
        self.parent = None
        self.start = 0
        self.stop = 0
        self.lemma = lemma
        self.content = content if content != None else []
            # either a list or a string
        self._head = None

    @property
    def tag(self): # str: TOP, NP, SUB, ADJ... (POS or type of node)
        """The tag of the node.

        It is the POS for leaf, or the type of node otherwise (NP, SUB, etc).

        In the parse tree, some tags contain also function information (eg
        "PP-DTV" for "PP dative").  Assuming the function information is
        separated with a hyphen, this kind of mixed tag is split **in the setter**.
        The `tag` property returns only the first part, the `function_tag` property
        returns the second part.
        """
        return self._tag

    @tag.setter
    def tag(self, value):
        if '-' in value[1:-1]: # -LRB-
            self._tag, self._function_tag = value.split('-')
        else:
            self._tag = value

    @property
    def pspeech(self): # same as tag
        """Alias for `tag`."""
        return self.tag

    @property
    def function_tag(self): # function tag after hyphen in POS, eg DTC (tag is "PP-DTV" for "PP dative")
        """See `tag`."""
        return self._function_tag

    def add_child(self, node): # -
        """Add a child node (assuming the node is not a leaf)."""
        assert not isinstance(self.content, str)
        self.content.append(node)
        node.parent = self

    def add_string(self, string): # -
        """Add the content string (the word/token): use this only if self
        is a leaf.  Do not set the string for other type of nodes."""
        assert not self.content
        self.content = string

    def get_infos(self, indent=0): # -
        """Return a string describing self.

        This is for debugging purpose.  The returned string include the tag,
        the position (start, stop) and the children of self.

        You should use this method on the root node, to print the whole tree
        once.
        """
        res = " " * indent + self.tag + " [%d:%d]" % (self.start, self.stop)
        if self.is_leaf:
            return res + ": " + self.content
        for child in self.content:
            if res:
                res += "\n"
            res += child.get_infos(indent=indent+2)
        return res

    def get_string(self): # content string
        """Compute and return the content string.

        If self is not a leaf, concatenate the content string of all the
        children.
        """
        if self.is_leaf:
            return self.content
        return " ".join(child.get_string() for child in self.content)

    def __str__(self): # -
        """Return string of the form "TAG: STRING"."""
        return "%s: %s" % (self.tag, self.get_string())

    def __len__(self): # length in tokens
        """Compute and return the length of self, using `start` and `stop`.

        If `start` and `stop` are not set, return 0.
        """
        return self.stop - self.start

    @property
    def pos(self): # (start, stop)
        """Return the tuple (start, stop)."""
        return self.start, self.stop

    @property
    def is_leaf(self): # bool
        """Return True if self is a leaf, False otherwise."""
        return isinstance(self.content, str)

    @property
    def is_clause(self): # bool
        """Return True if self is a clause (its tag is in CLAUSE_TAGS),
        False otherwise."""
        return self.tag in CLAUSE_TAGS

    @property
    def is_phrase(self): # bool
        """Return True if self is a phrase (its tag is in PHRASE_TAGS),
        False otherwise."""
        return self.tag in PHRASE_TAGS

    @property
    def parent_clause(self): # -
        """Return the parent clause (a Node), that is, the node which has a tag
        in CLAUSE_TAGS.
        
        If no clause has been found, return Top.
        """
        parent = self.parent
        while parent and parent.tag != "TOP" and not parent.is_clause:
            parent = parent.parent
        return parent

    @property
    def parent_clause_id(self): # int
        return self.parent_clause.id_

    @property
    def parent_phrase(self): # -
        """Return the parent phrase (a Node), that is, the node which has a tag
        in PHRASE_TAGS.
        
        If no phrase has been found, return Top.
        """
        parent = self.parent
        while parent and parent.tag != "TOP" and not parent.is_phrase:
            parent = parent.parent
        return parent

    @property
    def parent_phrase_id(self): # int
        return self.parent_phrase.id_

    @property
    def is_top(self): # bool
        """Alias for `is_root`."""
        return self.is_root

    @property
    def is_root(self): # bool
        """Return True if self is the root of the tree."""
        return self.parent is None

    @property
    def pp(self): # -
        """Return the PP (Prepositional Phrase) in which self is.

        The PP must be the parent phrase of self, or the grandparent if the
        parent is a NP.
        """
        parent = self.parent_phrase
        if parent and parent.tag == "NP":
           parent = parent.parent_phrase
        if parent and parent.tag == "PP":
            return parent
        return None

    @property
    def in_pp(self): # bool
        """Return True if self is in a pp, that is `self.pp` is not None."""
        return bool(self.pp)

    @property
    def preposition(self): # -
        """Return the first IN child of a PP if self is a PP.  If none is
        found, return None.

        Note that the preposition is not necessarily the first child, as in
        "only between them".
        """
        if self.tag == "PP" and self.content:
            for child in self.content:
                if child.tag == "IN":
                    return child
        return None


    @property
    def clause_depth(self): # int
        """Return the number of clauses encountered while walking up to the
        root (excluding self if self is a clause).
        """
        parent = self.parent
        counter = 0
        while parent:
            if parent.is_clause:
                counter += 1
            parent = parent.parent
        return counter

    @property
    def phrase_depth(self): # int
        """Return the number of phrases encountered while walking up to the
        root (excluding self if self is a phrase).
        """
        parent = self.parent
        counter = 0
        while parent:
            if parent.is_phrase:
                counter += 1
            parent = parent.parent
        return counter

    @property
    def node_depth(self): # int
        """Return the number of node encountered while walking up to the
        root.
        """
        parent = self.parent
        counter = 0
        while parent:
            counter += 1
            parent = parent.parent
        return counter

    @property
    def is_in_main_clause(self): # bool
        """Return True if self is in the main clause, that is if the clause
        depth is 1 (which is different from "parent is the main clause")."""
        return self.clause_depth == 1

    @property
    def is_main_clause(self): # bool
        """Return True if self is the top clause."""
        return self.is_clause and self.clause_depth == 0

    @property
    def is_matrix(self): # bool
        """Return True if self is a matrix clause, that is if it is a clause
        and some of its children (or descendants) is an embedded clause.  Note
        that relative clause are considered here as clauses."""
        if not self.is_clause:
            return False
        if self.is_leaf:
            return False
        for child in self.content:
            if child.is_clause:
                return True
            if child.is_matrix:
                return True
        return False

    @property
    def is_in_matrix(self): # bool
        """Return True if the parent clause is a matrix clause."""
        parent = self.parent_clause
        return parent and parent.is_matrix

    @property
    def is_embedded(self): # bool
        """Return True if self is a clause and any of its ancestors is another
        clause."""
        if not self.is_clause:
            return False
        for ancestor in self.ancestors:
            if ancestor.is_clause:
                return True
        return False

    @property
    def is_in_embedded(self): # bool
        """Return True if the parent clause is embedded."""
        parent = self.parent_clause
        return parent and parent.is_embedded


    @property
    def ancestors(self): # -
        """Yields all ancestors"""
        parent = self.parent
        while parent:
            yield parent
            parent = parent.parent

    @property
    def root(self): # -
        """Return the root node of the tree (self is self is root)"""
        node = self
        while True:
            parent = node.parent
            if not parent:
                return parent
            node = parent

    @property
    def root_id(self): # int
        """Return the id of the root."""
        return self.root.id_

    @property
    def sentence_id(self): # int; alias for `root_id`
        """Alias for `root_id`."""
        return self.root_id

    @property
    def top(self): # -
        """Alias for root."""
        return self.root

    def get_common_ancestor(self, other): # NotImplementedError
        raise NotImplementedError

    def is_in_same_sentence(self, other): # REL: bool
        """Return True if both nodes are in the same sentence (ie. tree)."""
        return self.root is other.root

    def is_in_same_clause(self, other): # REL: bool
        """Return True if both nodes are in the same clause."""
        return self.parent_clause is other.parent_clause

    def is_in_same_phrase(self, other): # REL: bool
        """Return True if both nodes are in the same phrase."""
        return self.parent_phrase == other.parent_phrase

    def is_other_in_dependent_clause(self, other): # TODO
        clause = self.parent_clause
        parent = other
        while parent:
            if parent is clause:
                return True
            parent = parent.parent
        return False

    @property
    def is_adjective(self): # bool
        return self.tag in ADJECTIVE_TAGS

    @property
    def is_noun(self): # bool
        return self.tag in NOUN_TAGS

    @property
    def is_pronoun(self): # bool
        return self.tag in PRONOUN_TAGS

    @property
    def is_cnoun(self): # bool
        return self.tag in CNOUN_TAGS

    @property
    def is_pnoun(self): # bool
        return self.tag in PNOUN_TAGS

    @property
    def is_det(self): # bool
        return self.tag in DETERMINATIVE_TAGS

    def set_head(self, node):
        self._head = node

    @property
    def head(self): # -
        """Return the head Node (see doc)."""
        if not self._head:
            if self.is_leaf:
                return self
            assert self.content, self.content
            last = None
            for child in self.content:
                if child.is_leaf:
                    if child.is_pronoun and not child.is_possessive:
                        return child
                    if child.is_noun:
                        if child.is_leaf:
                            if child.content not in ("Co Co. Inc Inc."):
                                last = child
                        else:
                            last = child
            if last:
                return last
            self._head = self.content[0].head
        return self._head

    @property
    def head_string(self): # content of head
        head = self.head
        if head:
            return head.string
        return None

    def get_dependents(self, only_pre=False, only_post=False): # -
        """Yield dependents Nodes.

        If the node is a leaf, yield nothing

        Dependents are all the children of self, except the head.
        """
        if self.is_leaf:
            return
        head = self.head
        post = False
        for child in self.content:
            if child is head:
                if only_pre:
                    return
                post = True
            else:
                if only_post and not post:
                    pass
                else:
                    for x in ('adjective', 'noun', 'clause', 'phrase'):
                        if getattr(child, 'is_'+x):
                            yield child
                            break

    @property
    def dependent_type_counters(self): # dict(adjective=0, noun=0, clause=0, phrase=0, other=0)
        if hasattr(self, '_dependent_type_counters'):
            return self._dependent_type_counters
        dic = {x: 0 for x in ('adjective', 'noun', 'clause', 'phrase', 'other')}
        for dep in self.get_dependents():
            found = False
            for x in ('adjective', 'noun', 'clause', 'phrase'):
                if getattr(dep, 'is_'+x):
                    dic[x] += 1
                    found = True
                    break
            if not found:
                dic['other'] += 1
        self._dependent_type_counters = dic
        return dic

    @property
    def adjective_dependent_counter(self):
        return self.dependent_type_counters['adjective']
        
    @property
    def noun_dependent_counter(self):
        return self.dependent_type_counters['noun']
        
    @property
    def clause_dependent_counter(self):
        return self.dependent_type_counters['clause']
        
    @property
    def phrase_dependent_counter(self):
        return self.dependent_type_counters['phrase']

    @property
    def other_dependent_counter(self):
        return self.dependent_type_counters['other']
        
    @property
    def dependent_count(self): # int
        return _count(self.get_dependents())

    @property
    def predependent_count(self): # int
        return _count(self.get_dependents(only_pre=True))

    @property
    def postdependent_count(self): # int
        return _count(self.get_dependents(only_post=True))

    def get_descendants(self): # -
        """Yield all descendants Nodes."""
        if self.is_leaf:
            return
        for child in self.content:
            yield child
            yield from child.get_descendants()

    @property
    def descendant_list(self):
        """Return a list of all self's descendants' ids."""
        return [ node.id_ for node in self.get_descendants() ]

    @property
    def phrase_descendant_list(self):
        """Return a list of all self's phrase's descendants' ids."""
        parent = self.parent_phrase
        if parent:
            return [ node.id_ for node in parent.get_descendants() ]
        return []

    @property
    def clause_descendant_list(self):
        """Return a list of all self's clause's descendants' ids."""
        parent = self.parent_clause
        if parent:
            return [ node.id_ for node in parent.get_descendants() ]
        return []

    @property
    def determiner(self): # -
        """Return a Node or a **list** of Node.

        If NP:
        * Amongst the children:
            * if the first is a QP, return that QP (the head is the whole thing)
            * if the first is_genitive, return that children (the head is the
              whole thing)
            * otherwise, return the lists of all DETERMINATIVE_TAGS at the
              beginning of self (the head must be the last one).  If there is
              only one such element, return a Node, otherwise return a list.

        Sometimes, the NP we are interested is inside another NP:
                       A    DT  (TOP(NP(NP*   (96
            conversation    NN            *)    -
                    with    IN         (PP*     -
               columnist    NN         (NP*   (53
                     Tom   NNP            *     -
                Friedman   NNP           *))   53)
                      /.     .           *))   96)

        So if the first child is a NP, go recursive to find the determiner of
        this NP.

        Otherwise, return None
        """
        if self.tag == "NP":
            if self.content and self.content[0].tag in QUANTIFIER_PHRASE:
                return self.content[0]
            if self.content and self.content[0].is_genitive:
                return self.content[0]
            res = []
            for child in self.content:
                if child.tag in DETERMINATIVE_TAGS:
                    res.append(child)
            if len(res) == 1:
                return res[0]
            if len(res) > 1:
                return res
            if self.content and self.content[0].tag == "NP":
                return self.content[0].determiner
            if len(res) == 0:
                return None
        return None
    
    @property
    def determiner_string(self): # str
        """Return a concatenated string of the words of the `determiner`."""
        det = self.determiner
        if isinstance(det, list):
            return " ".join(x.string for x in det)
        return det.string if det else ""

    @property
    def determiner_head(self): # -
        """Return a Node (or None), according to the definition of "head" in
        the documentation for `determiner`."""
        res = self.determiner
        if isinstance(res, list):
            return res[-1]
        return res

    @property
    def determiner_head_string(self): # str
        """Return the `determiner_head` string."""
        head = self.determiner_head
        return head.string if head else ""

    @property
    def string(self): # str
        """Return the `content` if leaf, or the contanated string contents if
        not a leaf."""
        if self.is_leaf:
            return self.content
        return " ".join(child.string for child in self.content)

    @property
    def is_genitive(self): # bool
        """Return True if the last child is POS ("John['s] cat")."""
        return not self.is_leaf and self.content[-1].tag == "POS"

    @property
    def is_possessive(self): # bool
        """Return True if tag is in POSSESSIVE_TAGS."""
        return self.tag in POSSESSIVE_TAGS

    @property
    def determiner_type(self): # str
        """See helper document on determiner."""
        det = self.determiner
        if det is None:
            return "bare"
        if isinstance(det, list):
            for word in (x.string for x in det):
                if word.lower() in EXHAUSTIVE_DETERMINER_WORDS:
                    return 'def-quant'
            det = det[-1]
        if det.tag in QUANTIFIER_PHRASE:
            for word in (x.string for x in det.content):
                if word.lower() in EXHAUSTIVE_DETERMINER_WORDS:
                    return 'def-quant'
            return 'ind-quant'
        if det.is_genitive:
            return 'def-gen'
        if det.tag in POSSESSIVE_TAGS:
            return 'def-poss'
        if det.string.lower() in DEFINITE_ARTICLE_WORDS:
            return 'def-art'
        if det.string.lower() in INDEFINITE_ARTICLE_WORDS:
            return 'indef-art'
        if det.string.lower() in DEMONSTRATIVE_DETERMINER_WORDS:
            return 'def-dem'
        if det.string.lower() in INDEFINITE_QUANDITIFIER_WORDS:
            return 'ind-quant'
        if det.string.lower() in NEGATIVE_DETERMINER_WORDS:
            return 'neg'
        if det.tag in INTERROGATIVE_DETERMINER_TAGS:
            return 'interr'
        if det.tag in CARDINAL_TAGS:
            return 'ind-quant'
        return 'ind-other'

    @property
    def has_bare_determiner(self): # bool
        return self.determiner is None

    @property
    def has_complex_determiner(self): # bool
        det = self.determiner
        if isinstance(det, list):
            return False
        return not det.is_leaf if det else False

    @property
    def has_genetive_determiner(self): # bool
        det = self.determiner
        if isinstance(det, list):
            return False
        return det.is_genitive if det else False

    @property
    def ariel1(self): # TODO
        res = None
        heads = self.heads
        head = heads[0]
        if head.is_noun and self.determination != 'definite':
            res = 0
        elif len(heads) > 1:
            res = 1
        elif head.is_noun and self.determination == 'definite':
            res = 2
        elif head.is_name:
            res = 3
        elif head.is_pronoun:
            res = 4
        return res

    @property
    def ariel2(self): # TODO
        ariel1 = self.ariel1
        if ariel1 == 0:
            res = 0
        elif ariel1 == 1:
            if self.expansions:
                res = 1
            res = 2
        elif ariel1 == 2:
            if self.expansions:
                res = 3
            res = 4
        elif ariel1 == 3:
            res = 5
        elif ariel1 == 4:
            res = 6
        else:
            res = ariel1
        return res

    def get_node_by_pos(self, start, stop, strict=True): # -
        """Return a descendant node matching start and stop.

        Return None if no such node exists.

        If two or more nodes have the same position, return the deeper one.
        """

        if not self.is_leaf:
            for child in self.content:
                node = child.get_node_by_pos(start, stop)
                if node:
                    return node
        op = int.__eq__ if strict else int.__le__
        if op(self.start, start) and op(stop, self.stop):
            return self
        return None

    def get_non_leaf_by_pos(self, start, stop, strict=True): # -
        """Return a non leaf descendant matching start and stop

        If strict is False (default is True), return the nearest smaller non
        leaf descendant.

        Return None if no such node can be found.
        """
        if self.is_leaf:
            return None
        for child in self.content:
            node = child.get_phrase_by_pos(start, stop, strict=True)
            if node:
                return node
        op = int.__eq__ if strict else int.__le__
        if op(self.start, start) and op(stop, self.stop):
            return self
        return None

    def get_leaf_by_pos(self, start, stop): # -
        """Return the descendant leaf matching start and stop.

        Return None if no such leaf can be found, that is, if stop - start is
        greater than 1.
        """
        if stop - start > 1:
            return None
        if self.is_leaf and self.start == start and self.stop == stop:
            return self
        for child in self.content:
            node = child.get_leaf_by_pos(start, stop)
            if node:
                return node
        return None

    def get_outer_node_by_pos(self, start, stop): # -
        if self.start <= start and stop <= self.stop:
            return self
        if not self.is_leaf:
            for child in self.content:
                node = child.get_node_by_pos(start, stop)
                if node:
                    return node
        return None

    def collapse(self, tag, content=None): # -
        # remove parent references to avoid memory leak
        self._clear()
        self.tag = tag
        self.content = content if content != None else self.get_string()

    def _clear(self): # -
        if not self.is_leaf:
            for child in self.content:
                child._clear()
        del self.parent

    def print_all_np_heads(self): # -
        raise NotImplementedError
        ##if self.tag in ("NP", "NML"):
        #    print(str(self))
        #    print("- head: %s" % self.head)
        #if not self.is_leaf:
        #    for child in self.content:
        #        child.print_all_np_heads()

    @property
    def is_plural_noun(self): # bool
        """Return True if the tag is NNS or NNPS."""
        return self.tag in PLURAL_TAGS

    #@property
    #def coarse_pspeech(self): # str
    #    """Return one of COARSE_PSPEECH or COARSE_DEFAULT."""
    #    if not self.is_leaf:
    #        return None
    #    if self.tag in COARSE_PSPEECH:
    #        return COARSE_PSPEECH[self.tag]
    #    return COARSE_DEFAULT

    @property
    def ud_pspeech(self): # str
        return ptb2ud(self.tag)



    @property
    def broad_pspeech(self): # str
        """WordNet-like POS: n/p/d for noun/pro/det, and else like WN or None.
        """
        if self.is_noun:
            return 'n'
        if self.is_pronoun:
            return 'p'
        if self.is_det:
            return 'd'
        if self.tag:
            wntag = self.tag.upper()
            if wntag.startswith('J'):
                return 'a'
            if wntag.startswith('RB'):
                return 'r'
            if wntag.startswith('V'):
                return 'v'
        return None

    @property
    def noun_type(self): # str
        """Return "cnoun", "pnoun" or None."""
        if self.is_cnoun:
            return 'cnoun'
        if self.is_pnoun:
            return 'pnoun'
        return None



class _ParsingError(Exception):
    pass



class TreeParser:

    def __init__(self, string, leaves=None):
        self.string = string
        self._index = 0
        self.leaves = leaves
        self._leaf_index = 0
        self.root = None
        self.node_list = []

    def parse(self):
        try:
            self.root = self._get_node()
        except (_ParsingError, IndexError):
            raise RuntimeError("can't parse '%s', at pos %d" % (self.string,
                self._index))

    def _get_node(self):
        self._eat_white()
        self._get_open_paren()
        tag = self._get_tag()
        node = Node(tag=tag)
        self.node_list.append(node)
        node.start = self._leaf_index
        while True:
            self._eat_white()
            if self._next_is_leaf():
                #print(self.leaves[self._leaf_index])
                new_node = Node(*self.leaves[self._leaf_index])
                self.node_list.append(new_node)
                new_node.start = self._leaf_index
                new_node.stop = new_node.start + 1
                node.add_child(new_node)
                self._leaf_index += 1
                self._eat_leaf()
            elif not self._next_is_open_paren():
                break
            else:
                node.add_child(self._get_node())
        if not node.content:
            node.add_string(self._get_string())
        self._get_close_paren()
        node.stop = self._leaf_index
        return node

    def _eat_white(self):
        while self.string[self._index].isspace():
            self._index += 1

    def _next_is_leaf(self):
        return self.string[self._index] == '*'

    def _eat_leaf(self):
        self._index += 1

    def _next_is_open_paren(self):
        return self.string[self._index] == '(' # )

    def _get_open_paren(self):
        self._eat_white()
        if self.string[self._index] == '(': # )
            self._index += 1
            return
        raise _ParsingError()

    def _get_close_paren(self):
        self._eat_white() # (
        if self.string[self._index] == ')':
            self._index += 1
            return
        raise _ParsingError()

    def _get_string(self):
        string = "" # (
        while self.string[self._index] not in "()":
            string += self.string[self._index]
            self._index += 1
        if string:
            return string
        raise _ParsingError()

    def _get_tag(self):
        string = ""
        while self.string[self._index] not in " ()":
            string += self.string[self._index]
            self._index += 1
        if string:
            return string
        raise _ParsingError()

##### test data ########################################################

STRING = """
(TOP (S (foo (more most))
        (chose truc)))

"""

STRING2 = """
(TOP (S (foo *)
        *))

"""

STRING3 = """
(TOP(S(NP(NP *
*
*
*)
(PP *
(NP(NP *
*)
(PP *
(NP *
*
*
*
*)))))
(VP *
(VP *
(VP *
(ADVP(ADVP *
*)
(PP *
(NP *)))
*
(PP *
(PP *
(NP *
*))))))
*))
"""


TEST =  \
[
("DT","The"),
("CD","two"),
("JJ","main"),
("NNS","suspects"),
("IN","in"),
("DT","the"),
("NN","bombing"),
("IN","of"),
("DT","the"),
("``","``"),
("NNP","USS"),
("NNP","Cole"),
("''","''"),
("MD","could"),
("VB","be"),
("VBN","charged"),
("RB","as"),
("RB","soon"),
("IN","as"),
("NNP","Tuesday"),
(",",","),
("VBG","according"),
("IN","to"),
("NNP","Associated"),
("NNP","Press"),
(".","."),
]


if __name__ == '__main__':
    parser = TreeParser(STRING)
    parser.parse()
    print(parser.root.get_infos())

    print('---')
    parser = TreeParser(STRING2, [('one', 'un'), ('two', 'deux')])
    parser.parse()
    print(parser.root.get_infos())

    print('---')
    parser = TreeParser(STRING3, FOO)
    parser.parse()
    print(parser.root.get_infos())
    print(parser.root.get_node_by_pos(19, 20).parent_phrase.get_infos())
    print(parser.root.get_node_by_pos(10, 12).get_infos())
    parser.root.print_all_np_heads()

    print('----')
    phrase = parser.root.get_node_by_pos(8, 13)
    print(phrase.get_string())
    print(" ".join(p.get_string() for p in phrase.heads))

    print('----')
    phrase = parser.root.get_node_by_pos(23, 25)
    print(phrase.get_string())
    print(" ".join(p.get_string() for p in phrase.heads))

    print('----')
    #print(parser.root.get_node_by_pos(16, 20).get_infos())
    #parser.root.get_node_by_pos(16, 20).collapse('DATE')
    parser.root.get_node_by_pos(16, 20).collapse('ADVP', [Node('DATE',
        parser.root.get_node_by_pos(16, 20).get_string())])
    print(parser.root.get_infos())



