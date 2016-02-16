from __future__ import print_function
import sys

def error(message):
    print('level="%s" process="%s", message="%s"' % ('error', __name__, message), file=sys.stderr)

def warn(message):
    print('level="%s" process="%s", message="%s"' % ('warn', __name__, message), file=sys.stderr)

def info(message):
    print('level="%s" process="%s", message="%s"' % ('info', __name__, message), file=sys.stderr)

def debug(message):
    print('level="%s" process="%s", message="%s"' % ('debug', __name__, message), file=sys.stderr)
