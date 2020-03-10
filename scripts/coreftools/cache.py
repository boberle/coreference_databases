import os
import json

class PairDictCache:

    def __init__(self, *, name=None, fpath=None, dpath=None, cls=str,
            json_fmt=True):
        self.name = name
        self.cls = cls
        self.data = dict()
        assert not (fpath and dpath)
        self.fpath = fpath if fpath \
            else os.path.join(dpath, name + (".json" if json_fmt else "")) \
            if dpath else None
        if self.fpath:
            self.load()

    def load(self):
        fpath = self.fpath
        if os.path.exists(fpath):
            print(f"Loading cache from '{fpath}'")
            if fpath.endswith('.json'):
                data = json.load(open(fpath))
                self.data = { (a, b): val for a, b, val in data }
            else:
                self.data = {
                    (a, b): val=="True" if self.cls is bool else self.cls(val)
                    for a, b, val
                    in (line[:-1].split("\t") for line in open(fpath))
                }
        else:
            print(f"No cache file found in '{fpath}'")

    def save(self):
        if not self.fpath:
            return
        print(f"Saving cache to {self.fpath}")
        if self.fpath.endswith('.json'):
            json.dump(
                [ [a, b, val] for (a, b), val in self.data.items() ],
                open(self.fpath, 'w')
            )
        else:
            with open(self.fpath, 'w') as fh:
                for (a, b), val in self.data.items():
                    fh.write(f"{a}\t{b}\t{val}\n")


    def get_ordered(self, a, b, func):
        if (a, b) in self.data:
            return self.data[(a, b)]
        val = func(a, b)
        self.data[(a, b)] = val
        return val

    def get_unordered(self, a, b, func):
        if (a, b) in self.data:
            return self.data[(a, b)]
        if (b, a) in self.data:
            return self.data[(b, a)]
        val = func(a, b)
        self.data[(a, b)] = val
        return val

    def __getitem__(self, key):
        return self.get_unordered(*key)

