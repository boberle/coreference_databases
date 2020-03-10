import io
import json
from zipfile import ZipFile, ZIP_DEFLATED
import pickle


def load_cache(fpath, as_is=False):
    """Load and return the "data.json" member of the zip file `fpath`."""

    with ZipFile(fpath) as zf:
        with io.TextIOWrapper(zf.open("data.json")) as ufh:
            if as_is:
                return json.load(ufh)
            else:
                return {
                    key: {
                        (start, stop): value
                        for start, stop, value in dat
                    }
                    for key, dat in json.load(ufh).items()
                }



def save_cache(fpath, data, as_is=False):
    """Save the json data into the zip file `fpath`."""

    with ZipFile(fpath, 'w', compression=ZIP_DEFLATED) as zf:
        with io.TextIOWrapper(zf.open("data.json", 'w')) as ufh:
            if as_is:
                json.dump(data, ufh)
            else:
                json.dump({
                    k: [
                        [start, stop, val]
                        for (start, stop), val in v.items()
                    ]
                    for k, v in data.items()},
                ufh)


_text_id = None
_counter = 0

def get_value(data, text, start, stop, extend=False):
    """Return the value of the item (text, start, stop) of data."""
    #global _text_id, _counter
    #if _text_id != text:
    #    if _counter % 100 == 0:
    #        print("Done %d" % _counter)
    #    _counter += 1
    #    _text_id = text

    if (start, stop) in data[text]:
        return data[text][start, stop]
    elif extend == True or extend == 1:
        if extend and (start+1, stop) in data[text]:
            return data[text][start+1, stop]
        if extend and (start, stop+1) in data[text]:
            return data[text][start, stop+1]
        if extend and (start+1, stop+1) in data[text]:
            return data[text][start+1, stop+1]
    elif int(extend) > 1:
        for s in (start-i for i in range(extend)):
            for e in (stop+j for j in range(extend)):
                if (s, e) in data[text]:
                    return data[text][s, e]
    return None


def get_list_value(data, text, start, stop, length):
    if (start, stop) in data[text]:
        return data[text][start, stop]
    return [None]*length

