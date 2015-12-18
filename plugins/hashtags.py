# Written by Scaevolus 2010
from util import hook, http, text, execute, database
import string
import sqlite3
import re

re_lineends = re.compile(r'[\r\n]*')

# some simple "shortcodes" for formatting purposes
shortcodes = {
'[b]': '\x02',
'[/b]': '\x02',
'[u]': '\x1F',
'[/u]': '\x1F',
'[i]': '\x16',
'[/i]': '\x16'}


def db_init(db):
    db.execute("create table if not exists mem(word, data, nick,"
               " primary key(word))")
    db.commit()


def get_memory(db, word):

    row = db.execute("select data from mem where word=lower(?)",
                     [word]).fetchone()
    if row:
        return row[0]
    else:
        return None

#@hook.regex(r'(.*) is (.*)')
#@hook.regex(r'(.*) are (.*)')
@hook.command("learn", adminonly=False)
@hook.command("r", adminonly=False)
@hook.command(adminonly=False)
def remember(inp, nick='', db=None, say=None, input=None, notice=None):
    "remember <word> <data> -- Remembers <data> with <word>."
    db_init(db)

    append = False

    try:
        word, data = inp.split(None, 1)
        #word = inp.group(1)
        #data = inp.group(2)
    except ValueError:
        notice(remember.__doc__)

    old_data = get_memory(db, word)

    #if data.startswith('+') or data.find('also') and old_data:
    if old_data:
        append = True
        # remove + symbol
        new_data = data.replace('+','')
        #new_data = data[1:]
        # append new_data to the old_data
        if len(new_data) > 1 and new_data[1] in (string.punctuation + ' '):
            data = old_data + new_data
        else:
            data = old_data + ' and ' + new_data

    db.execute("replace into mem(word, data, nick) values"
               " (lower(?),?,?)", (word, data.replace('<py>',''), nick))
    db.commit()

    if old_data:
        if append:
            notice("Appending \x02%s\x02 to \x02%s\x02" % (new_data, old_data))
        else:
            notice('Remembering \x02%s\x02 for \x02%s\x02. Type ?%s to see it.'
                % (data, word, word))
            notice('Previous data was \x02%s\x02' % old_data)
    else:
        notice('Remembering \x02%s\x02 for \x02%s\x02. Type ?%s to see it.'
                % (data, word, word))


@hook.command("f", adminonly=True)
@hook.command(adminonly=True)
def forget(inp, db=None, input=None, notice=None):
    "forget <word> -- Forgets a remembered <word>."

    db_init(db)
    data = get_memory(db, inp)

    if data:
        db.execute("delete from mem where word=lower(?)",
                   [inp])
        db.commit()
        notice('"%s" has been forgotten.' % data.replace('`', "'"))
        return
    else:
        notice("I don't know about that.")
        return


@hook.command
def info(inp, notice=None, db=None):
    "info <word> -- Shows the source of a factoid."

    db_init(db)

    # attempt to get the factoid from the database
    data = get_memory(db, inp.strip())

    if data:
        notice(data)
    else:
        notice("Unknown Factoid.")

# @hook.regex(r'^(\b\S+\b)\?$')
@hook.regex(r'^\#(\b\S+\b)')
@hook.regex(r'^\? ?(.+)')
def hashtag(inp, say=None, db=None, bot=None, me=None, conn=None, input=None, chan=None, notice=None):
    "<word>? -- Shows what data is associated with <word>."
    disabledhashes = database.get(db,'channels','disabledhashes','chan',chan)
    split = inp.group(1).strip().split(" ")

    try:
        if chan[0] != '#':
            pass
        elif split[0].lower() in disabledhashes.lower():
            notice('{} is disabled.'.format(split[0]))
            return
    except TypeError:
        pass

    try:
        prefix_on = bot.config["plugins"]["factoids"].get("prefix", False)
    except KeyError:
        prefix_on = False

    db_init(db)

    # split up the input
    split = inp.group(1).strip().split(" ")
    factoid_id = split[0]

    if len(split) >= 1:
        arguments = " ".join(split[1:])
    else:
        arguments = ""

    data = get_memory(db, factoid_id)

    if data:
        # factoid preprocessors
        if data.startswith("<py>"):
            code = data[4:].strip()
            variables = 'input="""%s"""; nick="%s"; chan="%s"; bot_nick="%s";' % (arguments.replace('"', '\\"'),
                        input.nick, input.chan, input.conn.nick)
            result = execute.eval_py(variables + code)
        elif data.startswith("<url>"):
            url = data[5:].strip()
            try:
                result = http.get(url)
            except http.HttpError:
                result = "Could not fetch URL."
        else:
            result = data

        # factoid postprocessors
        result = text.multiword_replace(result, shortcodes)

        if result.startswith("<act>"):
            result = result[5:].strip()
            me(result)
        else:
            if prefix_on:
                say("\x02[%s]:\x02 %s" % (factoid_id, result))
            else:
                say("\x02%s\x02 %s" % (factoid_id, result))

@hook.command(r'keys')
@hook.command(r'key')
@hook.command(autohelp=False)
def hashes(inp, say=None, db=None, bot=None, me=None, conn=None, input=None):
    "hashes -- Shows hash names for all known hashes."

    search = "SELECT word FROM mem"
    if inp: search = "{} WHERE word LIKE '%{}%'".format(search, inp)
    search = "{} ORDER BY word".format(search)

    rows = db.execute(search).fetchall()

    if rows: return ", ".join(tuple(x[0] for x in rows))
    else: return "No results."
