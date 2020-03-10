"""
Tree reprensetation of a dependency parser, ideally in a CONLL format.

Let `doc` be a document representation as follows:
    [ # a collection of sentences
        [ # a sentence
            # a token = a list of features (columns in a CONLL format):
            [ index, form, lemma, NER, etc. ],
            # another token:
            [ index, form, lemma, NER, etc. ],
            ...
        ],
        [ # another sentence
            # a token...
            [ index, form, lemma, NER, etc. ],
            ...
        ],
        ...
    ]

Pass this `doc` to `iter_sentences` to yield a tree for each sentence.  The
value returned by `iter_sentences` is:
    (ROOT, TOKENS)
where ROOT is the root Token and TOKENS is a list of all Token instances, in
order, present in the tree.
"""

CONLLU_INDICES = dict(
    form=1,
    lemma=2,
    pos=3,
    feats=5,
    parent_index=6,
    deplabel=7,
)


def iter_sentences(doc, indices=None, cls=None):
    """Yield a tree and a list of Token instances for each sentence.

    Parameters:
    -----------
    doc: list of sentences
        see the module docstring
    indices: dict
        column indices, see CONLLU_INDICES for an example
    cls: class
        Token by default
    """

    if not indices:
        indices = CONLLU_INDICES

    if not cls:
        cls = Token

    def get_attrs(split, index):
        deplabel, subdeplabel = split[indices['deplabel']], ""
        if ":" in deplabel:
            deplabel, subdeplabel = deplabel.split(":")
        return dict(
            index=index,
            form=split[indices['form']],
            lemma=split[indices['lemma']],
            pos=split[indices['pos']],
            feats=dict(x.split("=") for x in split[indices['feats']].split("|"))
                if split[indices['feats']] != "_" else None,
            parent_index=int(split[indices['parent_index']]),
            deplabel=deplabel,
            subdeplabel=subdeplabel,
        )

    for sent in doc:
        tokens = [
            cls(get_attrs(t, i))
            for i, t in enumerate(sent)
        ]
        root = None
        for token in tokens:
            if token.parent_index == 0:
                root = token
            else:
                tokens[token.parent_index-1].add_child(token)
        assert root
        add_level_to_nodes(root)
        yield root, tokens



class Token:
    """A token in the tree.

    Constructor:
    ------------
    attrs: dict
        list of attributes to add to the instance (name, value)
    feats: dict
        list of feats to add in the `feats` attribute
    """


    counter = 0


    def __init__(self, attrs=None, feats=None):
        self.id_ = self.__class__.counter
        self.__class__.counter += 1
        # tree
        self.children = []
        self.parent = None
        self.is_right = False
        self.feats = feats if feats is not None else dict()
        if attrs:
            for attr, value in attrs.items():
                setattr(self, attr, value)


    def add_child(self, token):
        self.children.append(token)
        token.parent = self
        token.is_right = token.index > self.index


    #def __getattr__(self, name):
    #    if self.feats and name in self.feats:
    #        return self.feats[name]
    #    #TODO PATCH (replace by AttributeError)
    #    #raise RuntimeError("object '%s' has no attribute '%s'" %
    #    #    (self.__class__.__name__, name))
    #    raise AttributeError("I don't have a feature '%s'.  "
    #        "Here are my features: %s" % (name, str(self.feats)))

    def __getitem__(self, key):
        if self.feats:
            return self.feats.get(key, None)
        return None


    def __contains__(self, key):
        if isinstance(key, Token):
            for tok in self.tokens:
                if tok is key:
                    return True
        elif isinstance(key, str):
            if self.feats:
                return key in self.feats
            return None
        else:
            assert False, type(key)
        return False

    def get(self, key, default=None):
        """Like `dict.get` but for features."""
        if self.feats:
            return self.feats.get(key, default)
        return default


    @property
    def parents(self):
        parent = self.parent
        while parent:
            yield parent
            parent = parent.parent

    @property
    def left_children(self):
        for child in self.children:
            if not child.is_right:
                yield child

    @property
    def right_children(self):
        for child in self.children:
            if child.is_right:
                yield child


    @property
    def descendants(self):
        for token in self.tokens:
            if not token is self:
                yield token


    @property
    def left_descendants(self):
        for descendant in self.descendants:
            if descendant is self:
                break
            yield descendant


    @property
    def right_descendants(self):
        fire = False
        for descendant in self.descendants:
            if fire:
                yield descendant
            if descendant is self:
                fire = True


    @property
    def tokens(self):
        fired = False
        for child in self.children:
            if not fired and child.is_right:
                fired = True
                yield self
            for token in child.tokens:
                yield token
        if not fired:
            yield self


    @property
    def reversed_tokens(self):
        for token in reversed(list(self.tokens)):
            yield token


    @property
    def leaves(self):
        for token in self.tokens:
            if not token.has_children:
                yield token

    @property
    def text(self):
        return [leaf.form for leaf in self.leaves]

    @property
    def has_children(self):
        return bool(self.children)


    @property
    def first_token(self):
        first = self
        for token in self.tokens:
            if token.index < first.index:
                first = token
        return first


    @property
    def first_non_punct_token(self):
        for token in self.tokens:
            if not token.is_punct:
                return token


    @property
    def last_token(self):
        last = self
        for token in self.tokens:
            if token.index > last.index:
                last = token
        return last


    @property
    def last_non_punct_token(self):
        for token in self.reversed_tokens:
            if not token.is_punct:
                return token


    @property
    def nodes(self):
        for child in self.children:
            yield child
            for node in child.nodes:
                yield node


    @property
    def left_side_up(self):
        token = self.first_token
        while not token is self:
            yield token
            token = token.parent


    @property
    def left_side_to_the_root(self):
        yield from self.left_side_up
        yield self


    @property
    def right_side_up(self):
        token = self.last_token
        while not token is self:
            yield token
            token = token.parent


    @property
    def right_side_to_the_root(self):
        yield from self.right_side_up
        yield self


    @property
    def root(self):
        token = self
        while token.parent:
            token = token.parent
        return token
            


def add_level_to_nodes(root, level=0):
    """Add the depth level (root at `level`) for each node under the root."""
    root.level = level
    for child in root.children:
        add_level_to_nodes(child, level+1)



#def correct_nodes(nodes):
#
#    for i in range(1, len(nodes)-1):
#        a, b, c = nodes[i-1], nodes[i], nodes[i+1]
#        if a.level < b.level and b.level <



