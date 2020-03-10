import sys

import pandas as pd

import corefdb

dbs = (
    ("CoNLL-2012", "/tmp/db_conll.zip"),
    ("Democrat", "/tmp/db_dem1921.zip"),
    ("Ancor", "/tmp/db_ancor.zip"),
)

allowed = "pos".split()

print("# Complete List Of Possible Values\n")

print("Table of contents:\n")

for db_name, _ in dbs:
    print(f'- <a href="#{db_name}">{db_name}</a>\n')
    for table in \
        "chains mentions paragraphs relations sentences texts tokens".split():
        print(f'    - <a href="#{db_name}-{table}">{table}</a>\n')


for db_name, path in dbs:

    db = corefdb.load(path)

    print(f'## Corpus <a name="{db_name}">{db_name}</a>\n')

    for table_name, table in sorted(db.items(), key=lambda x: x[0]):

        print(f'### Table <a name="{db_name}-{table_name}">`{table_name}`</a>\n')

        for field in sorted(table.columns):

            n = table[field].nunique()

            print(f"Field: `{field}`\n")

            if n > 20 and field not in allowed:
                if str(table.dtypes[field]) == "object":
                    print(f"`{n} string values\n")
                else:
                    print(f"min={table[field].min()}, "
                        f"max={table[field].max()}\n")

            else:
                counts = table[field].value_counts()
                print("<table>")
                print(f"<tr><td>value</td><td>counts</td></tr>")
                for k, v in counts.iteritems():
                    print(f"<tr><td><code>{k}</code></td><td>{v}</td></tr>")
                print("</table>\n")

