#!/usr/bin/env python

import sys

if sys.hexversion < 0x02020000:
    print
    print 'This package requires Python 2.2 or later!'
    print
    print 'You have:', sys.version
    print
    print '   see http://www.python.org/'
    print
    sys.exit(-1)

try:
    from distutils.core import setup, Extension
except ImportError:
    print
    print 'This installer requires the Python Distutils.'
    print
    print '   see http://www.python.org/sigs/distutils-sig/'
    print
    sys.exit(-1)


def get_yesno( prompt, default ):
    while 1:
        answer = raw_input(prompt)
        if answer == '':
            return default
        elif answer[0] == 'Y' or answer[0] == 'y':
            return 1
        elif answer[0] == 'N' or answer[0] == 'n':
            return 0

try:
    import Image
except ImportError:
    print
    print 'This package requires the Python Imaging'
    print 'Library to be installed.'
    print
    print 'Installation can continue, but the programs'
    print 'won\'t run until you install the imaging'
    print 'library.'
    print
    print '   see http://www.pythonware.com/products/pil/'
    print
    if not get_yesno( 'Do you want to continue installing? [Y/n] ', 1 ):
        print
        print 'Installation cancelled.'
        print
        sys.exit(0)
        

scripts = ['imgtops']

print
print 'To use "epstoimg" you will need the Ghostscript interpreter'
print 'installed.  (see http://www.ghostscript.com/)'
print
if get_yesno( 'Do you want to install epstoimg? [Y/n] ', 1 ):
    if sys.platform == 'win32':
        default = '+gswin32c.exe'
    else:
        default = '+gs'
        
    print
    print 'Enter the full pathname of the Ghostscript interpreter,'
    print 'or "+foo" to search the PATH for "foo" at runtime:'
    gs = raw_input( '[%s] ' % (default,) )
    if gs == '':
        gs = default

    f = open( 'epstoimg', 'w' )
    f.write( '#!/usr/bin/python\n' )
    f.write( 'from imgtopslib import epstoimg\n' )
    f.write( 'import sys\n' )
    f.write( 'try:\n' )
    f.write( '  epstoimg.main( gs=%r )\n' % (gs,) )
    f.write( 'except KeyboardInterrupt:\n' )
    f.write( '  sys.exit(1)\n' )
    f.close()
    scripts.append( 'epstoimg' )

print
print 'Installing imgtops...'
print

    
import os

os.umask( 0022 )

setup( name = "imgtops",
       version = "1.0",
       description = "imgtops: make EPS files from images",
       author = "Doug Zongker",
       author_email = "dzongker@sourceforge.net",
       url = "http://imgtops.sourceforge.net",
       packages = ['imgtopslib'],
       scripts = scripts,
       data_files = [('man/man1', ["imgtops.1", "epstoimg.1"])],
       )

