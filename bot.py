#!/usr/bin/env python

__author__ = "InfinityLabs"
__authors__ = ["Infinity"]
__copyright__ = "Copyright 2013, InfinityLabs"
__copyright__ = "Copyright 2012, ClouDev"
__credits__ = ["infinity","thenoodle", "_frozen", "rmmh"]
__license__ = "GPL v3"
__version__ = "DEV"
__maintainer__ = "InfinityLabs"
__email__ = "root@infinitylabs.us"
__status__ = "Development"

import os
import Queue
import sys
import time
import platform

sys.path += ['plugins']  # so 'import hook' works without duplication
sys.path += ['lib']
os.chdir(sys.path[0] or '.')  # do stuff relative to the install directory


class Bot(object):
    pass

print 'UguuBot %s (%s) <http://github.com/infinitylabs/UguuBot>' % (__version__, __status__)

# print debug info
opsys = platform.platform()
python_imp = platform.python_implementation()
python_ver = platform.python_version()
architecture = ' '.join(platform.architecture())

print "Operating System: %s, Python " \
        "Version: %s %s, Architecture: %s" \
        "" % (opsys, python_imp, python_ver, architecture)

bot = Bot()
bot.start_time = time.time()

print 'Loading plugins...'

# bootstrap the reloader
eval(compile(open(os.path.join('core', 'reload.py'), 'U').read(),
    os.path.join('core', 'reload.py'), 'exec'))
reload(init=True)

config()
if not hasattr(bot, 'config'):
    exit()

print 'Connecting to IRC...'

bot.conns = {}

try:
    for name, conf in bot.config['connections'].iteritems():
        print 'Connecting to server: %s' % conf['server']
        if conf.get('ssl'):
            bot.conns[name] = SSLIRC(name, conf['server'], conf['nick'], conf=conf,
                    port=conf.get('port', 6667), channels=conf['channels'],
                    ignore_certificate_errors=conf.get('ignore_cert', True))
        else:
            bot.conns[name] = IRC(name, conf['server'], conf['nick'], conf=conf,
                    port=conf.get('port', 6667), channels=conf['channels'])
except Exception as e:
    print 'ERROR: malformed config file', e
    sys.exit()

bot.persist_dir = os.path.abspath('persist')
if not os.path.exists(bot.persist_dir):
    os.mkdir(bot.persist_dir)

print 'Connection(s) made, starting main loop.'

while True:
    reload()  # these functions only do things
    config()  # if changes have occured

    for conn in bot.conns.itervalues():
        try:
            out = conn.out.get_nowait()
            main(conn, out)
        except Queue.Empty:
            pass
    while all(conn.out.empty() for conn in bot.conns.itervalues()):
        time.sleep(.1)
