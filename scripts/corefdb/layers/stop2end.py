"""
=== mentions ===
stop
text_stop
par_stop
h_stop
h_text_stop
=== sentences ===
last_token_index
"""


def replace_stop_by_end(db):

    # sentences

    db['sentences']['last_token_index'] = [
        last_token_index - 1
        for last_token_index in db['sentences']['last_token_index']
    ]

    # mentions

    fields = {
        field: field.replace('stop', 'end')
        for field in ['stop','text_stop','par_stop','h_stop','h_text_stop']
        if field in db['mentions'].columns
    }

    for field in fields:
        db['mentions'][field] = [
            x - 1 for x in db['mentions'][field]
        ]

    db['mentions'].rename(fields, axis=1, inplace=True, errors='raise')

    return db
