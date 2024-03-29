import sys, os.path
import Image
import cStringIO
import time
import getopt
from dimensions import interpret_dimension
import psimage

version = 'imgtops 1.0'
copyright = '''Copyright (C) 2003 Doug Zongker
This is free software; see the accompanying license for copying conditions.
There is NO warranty; not even for MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.'''



timestamp = time.asctime( time.localtime() )

paper_sizes = {
    'letter' : (612, 792),
    'legal' : (612, 1008),
    'a4' : (595, 849),
    }

err = sys.stderr

class Parameters:
    def __init__( self ):
        self.level = 2
        self.force_hex = 0
        self.skip_rle = 0
        self.verbose = 10
        self.strict_eps = 0
        self.binary_output = 0
        self.line_length = 75
        
        self.width = None
        self.height = None
        self.paper_size = paper_sizes['letter']
        self.margin = interpret_dimension( '1in' )
        self.landscape = 0
        
        self.batch = 0
        self.input = None
        self.output = None

    def dump( self, f ):
        print >> f, 'level %d  force_hex %d  skip_rle %d  strict_eps %d  verbose %d' % \
              (self.level, self.force_hex, self.skip_rle, self.strict_eps, self.verbose)
        print >> f, 'width %r  height %r' % (self.width, self.height)
        print >> f, 'paper_size %r  margin %.2f  landscape %d' % (self.paper_size, self.margin, self.landscape)
        print >> f, 'batch %d' % (self.batch,)
        print >> f, 'inputs:', self.input
        print >> f, 'outputs:', self.output
        

params = Parameters()

def usage():
    print 'usage: %s [options] [filename(s)]' % (sys.argv[0],)
    print 
    print '  -?, --help                   show this message and exit'
    print '  --version                    print version info and exit'
    print 
    print '  -w, --width=<dim>            set image width'
    print '  -h, --height=<dim>           set image height'
    print '  -s, --paper-size=SIZE        set page size'
    print '        available sizes:         letter, legal, a4, or "<dim>,<dim>"'
    print '        default:                 letter'
    print '  -l, --landscape              use landscape mode'
    print '  -m, --margin=<dim>           set page margin (default 1 inch)'
    print
    print '        example dimensions:      4in, 35mm, 30.1cm, 144pt'
    print
    print '  -e, --strict-eps             strict EPS bounding box'
    print '  -2, --level-2                only level 2 postscript (default)'
    print '  -3, --level-3                allow level 3 postscript'
    print '  -x, --hex-encoding           force hex encoding'
    print '  -8, --allow-8-bit            allow binary data in output'
    print '  -n, --line-length=#          limit ASCII data lines to # characters'
    print 
    print '  -b, --batch                  accept multiple input images'
    print '  -o, --output <filename>      output file name (non-batch mode)'
    print '  -o, --output <dirname>       output directory (batch mode)'
    print
    print '  -q, --quiet                  run silently, except for errors'
    print '  -v, --verbose                be verbose'
    

def showversion():
    print version
    print
    print copyright
    

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], '?w:h:ls:m:e238xbo:qvn:',
                                   ['width=',
                                    'height=',
                                    'paper-size=',
                                    'landscape',
                                    'margin=',
                                    'strict-eps',
                                    'level-2',
                                    'level-3',
                                    'allow-8-bit',
                                    'line-length=',
                                    'hex-encoding',
                                    'batch',
                                    'output=',
                                    'quiet',
                                    'verbose',
                                    'version',
                                    ])
    except getopt.GetoptError:
        usage()
        return 2
    output = None
    for o, a in opts:
        if o in ('-?', '--help'):
            usage()
            return 0
        elif o == '--version':
            showversion()
            return 0
        elif o in ('-v', '--verbose'):
            params.verbose = 20
        elif o in ('-q', '--quiet'):
            params.verbose = 0
        elif o in ('-w', '--width'):
            params.width = interpret_dimension(a)
            if params.width is None:
                print >> err, "didn't understand width dimension %r" % (a,)
                return 1
            elif params.width <= 0:
                print >> err, "image width must be positive"
                return 1
        elif o in ('-h', '--height'):
            params.height = interpret_dimension(a)
            if params.height is None:
                print >> err, "didn't understand height dimension %r" % (a,)
                return 1
            elif params.height <= 0:
                print >> err, "image height must be positive"
                return 1
        elif o in ('-s', '--paper-size'):
            params.paper_size = interpret_papersize(a)
            if params.paper_size is None:
                print >> err, "didn't understand paper size %r" % (a,)
                return 1
        elif o in ('-m', '--margin'):
            params.margin = interpret_dimension(a)
            if params.margin is None:
                print >> err, "didn't understand margin dimension %r" % (a,)
                return 1
            elif params.margin < 0:
                print >> err, "margin must be nonnegative"
                return 1
        elif o in ('-l', '--landscape'):
            params.landscape = 1
        elif o in ('-e', '--strict-eps'):
            params.strict_eps = 1
        elif o in ('-x', '--hex-encoding'):
            params.force_hex = 1
        elif o in ('-2', '--level-2'):
            params.level = 2
        elif o in ('-3', '--level-3'):
            params.level = 3
        elif o in ('-8', '--allow-8-bit'):
            params.binary_output = 1
        elif o in ('-n', '--line-length'):
            try:
                params.line_length = int(a)
            except ValueError:
                print >> err, "line length must be integer"
                return 1
        elif o in ('-b', '--batch'):
            params.batch = 1
        elif o in ("-o", "--output"):
            params.output = a

    if not params.strict_eps and \
           (params.margin * 2 >= params.paper_size[0] or
            params.margin * 2 >= params.paper_size[1]):
        print >> err, "margin leaves no room on page for image"
        return 1

    if params.batch and len(args) == 0:
        print >> err, "image filenames must be specified for batch mode"
        return 1

    if not params.batch and len(args) > 1:
        print >> err, "multiple input filenames given; perhaps use batch mode?"
        return 1

    if params.batch:
        params.input = args
        if params.output is None:
            params.output = ''
        else:
            if not os.path.isdir( params.output ):
                print >> err, "in batch mode, -o must specify a directory"
                return 1
    else:
        if args:
            params.input = args[0]

    if params.batch:
        run_batch_mode()
    else:
        run_single_mode()


def interpret_papersize( a ):
    try:
        return paper_sizes[a]
    except KeyError:
        pass
    
    wh = a.split(',')
    if len(wh) != 2:
        return None

    try:
        w = interpret_dimension(wh[0])
        h = interpret_dimension(wh[1])
    except ValueError:
        return None

    if w > 0 and h > 0:
        return w, h
    else:
        return None


def run_single_mode():
    if params.verbose >= 10:
        if params.input is None:
            print >> err, "processing [<stdin>]..."
        else:
            print >> err, "processing [%s]..." % (params.input,)
    
    try:
        lim = load_image( params.input )
    except IOError, msg:
        print >> err, "  image read error: %s" % (msg,)
        return 1

    if params.output:
        try:
            f = open( params.output, 'wb' )
        except IOError, msg:
            print >> err, "  PS write error: %s" % (msg,)
            return 1
    else:
        f = sys.stdout

        # change stdout's mode to binary, to avoid
        # newlines getting translated to CRLFs.
        
        if sys.platform == "win32":
            import os, msvcrt
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

    process_one_image( lim, f )
    f.close()
    return 0
            
def run_batch_mode():
    if params.strict_eps:
        newext = '.eps'
    else:
        newext = '.ps'
    result = 0
        
    for i in params.input:
        if params.verbose >= 10:
            print >> err, "processing [%s]..." % (i,)
            
        try:
            lim = load_image( i )
        except IOError, msg:
            print >> err, "  image read error: %s; skipping" % (msg,)
            result = result or 1
            del lim
            continue

        dir, name = os.path.split( i )
        base, ext = os.path.splitext( name )
        outpath = os.path.join( params.output, base+newext )

        try:
            f = open( outpath, 'wb' )
        except IOError, msg:
            print >> err, "  PS write error: %s; skipping" % (msg,)
            result = result or 1
            continue

        process_one_image( lim, f )
        del lim
        f.close()

    return result

def process_one_image( lim, f ):
    d = { 'Creator' : '(%s)' % (version),
          'CreationDate' : '(%s)' % (timestamp,),
          'Title' : '(%s)' % (lim.filename,) }

    imbuffer = cStringIO.StringIO()
    level = psimage.write_ps_image( imbuffer, lim, params )
    
    fit = psimage.compute_fit( lim.size, params )
    psimage.write_postscript_header( fit, params, f, d, level )
    f.write( imbuffer.getvalue() )
    imbuffer.close()
    psimage.write_postscript_footer( fit, params, f )
    


class LoadedImage:
    pass
            
def load_image( filename ):
    if filename == None:
        buffer = cStringIO.StringIO( sys.stdin.read() )
    else:
        f = open( filename, 'rb' )
        buffer = cStringIO.StringIO( f.read() )
        f.close()
    im = Image.open( buffer )

    lim = LoadedImage()
    lim.buffer = buffer
    lim.im = im
    lim.size = im.size
    if filename:
        lim.filename = filename
    else:
        lim.filename = '<stdin>'

    return lim

if __name__ == "__main__":
    r = main()
    sys.exit( r )


# lim = load_image( sys.argv[1] )
# f = open( 'test.eps', 'w' )
# write_ps_image( f, lim )
# f.close()
