import os, tempfile, sys
import getopt
import Image
from dimensions import interpret_dimension
import re
import cStringIO

version = 'epstoimg 1.0'
copyright = '''Copyright (C) 2003 Doug Zongker
This is free software; see the accompanying license for copying conditions.
There is NO warranty; not even for MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.'''

err = sys.stderr

output_formats = ('BMP', 'GIF', 'JPEG', 'PCX', 'PNG', 'PPM', 'TIFF')
extension_map = { '.bmp' : 'BMP', '.dib' : 'BMP',
                  '.gif' : 'GIF',
                  '.jpeg' : 'JPEG', '.jpe' : 'JPEG', '.jpg' : 'JPEG',
                  '.pcx' : 'PCX',
                  '.png' : 'PNG',
                  '.ppm' : 'PPM', '.pgm' : 'PPM', '.pbm' : 'PPM',
                  '.tiff' : 'TIFF', '.tif' : 'TIFF',
                  }
                  

bbox_re = re.compile( r'^%%BoundingBox:\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)' )
orient_re = re.compile( r'^%%(?:Page)?Orientation:\s*([a-zA-Z]+)' )
pagesize_re = re.compile( r'PageSize \[([\d\.]+) ([\d\.]+)\]' )

class Parameters:
    def __init__( self ):
        self.verbose = 10
        self.grayscale = 0
        
        self.margin = 0
        self.padding = 0
        self.paddingcolor = (255, 255, 255)
        self.res = None

        self.width = None
        self.height = None

        self.output = None
        self.format = None

        self.turns = 0

        self.gs = '+gs'

    def finish( self ):
        if self.gs and self.gs[0] == '+':
            self.found_gs = self.find_program( self.gs[1:] )
        else:
            self.found_gs = os.path.abspath( self.gs )
        if not self.found_gs or not os.path.isfile(self.found_gs) or \
               not os.access(self.found_gs,os.X_OK):
            print >> err, 'Ghostscript interpreter "%s" not found' % (self.gs,)
            sys.exit(1)
        if params.verbose >= 20:
            print >> err, 'Ghostscript is [%s]' % (self.found_gs,)

    def find_program( self, progname ):
        try:
            paths = os.environ['PATH'].split( os.pathsep )
        except KeyError:
            paths = ['']
        for path in paths:
            p = os.path.join( path, progname )
            if os.path.exists( p ):
                return os.path.abspath( p )

        print >> err, '"%s" not found in PATH' % (progname,)
        return None

params = Parameters()


def read_headers( fn ):
    bfound = 0
    ofound = 0
    bbox = None
    orient = 0
    
    f = open( fn )
    for i in f:
        if not bfound:
            m = bbox_re.match( i )
            if m:
                bbox = tuple([int(i) for i in m.groups()])
                bfound = 1
        if not ofound:
            m = orient_re.match( i )
            if m:
                o = m.groups(1)[0].lower()
                if o == 'portrait':
                    orient = 0
                    ofound = 1
                elif o == 'landscape':
                    orient = 3
                    ofound = 1
                else:
                    print >> err, 'skipping bad DSC comment: %r' % (i.rstrip(),)
        if bfound and ofound:
            break
                
    if params.verbose >= 20:
        print >> err, 'bbox is %r\norient is %d' % (bbox,orient)
    return bbox, orient

def apply_margin( bbox ):
    m = params.margin
    if m < 0 and (bbox[2]-bbox[0] <= 2*m or bbox[3]-bbox[1] <= 2*m):
        print >> err, "negative margin leaves bbox empty!"
        sys.exit(1)
    return bbox[0]-m, bbox[1]-m, bbox[2]+m, bbox[3]+m

def compute_resolution( bbox ):
    if params.res:
        return params.res

    if bbox:
        bw, bh = bbox[2]-bbox[0], bbox[3]-bbox[1]
        w, h = get_desired_size( (bw, bh) )
        rx = 288.0 * w / bw
        ry = 288.0 * h / bh
        return '%sx%s' % (rx, ry)
    else:
        return '300'
    

def process_ps_file( fn, bbox ):
    res = compute_resolution( bbox )
    if params.verbose >= 20:
        print 'Ghostscript resolution is [%s]' % (res,)
    
    tmpdir = tempfile.mktemp()
    os.mkdir( tmpdir )
    page1 = None
    try:
        cmd = params.found_gs + ' -sDEVICE=ppmraw -sOutputFile=%s/page%%08d.ppm -r%s' % (tmpdir, res)

        to_gs, from_gs = os.popen2( cmd )

        to_gs.write( '<< ' )
        if bbox:
            to_gs.write( '/PageSize [ %f %f ] /BeginPage { pop %f %f translate } ' %
                         (bbox[2]-bbox[0], bbox[3]-bbox[1], -bbox[0], -bbox[1]) )
        to_gs.write( '/EndPage { exch pop 2 ne (%stdout) (w) file (\nPageSize ) writestring currentpagedevice /PageSize get == }' )
        to_gs.write( '>> setpagedevice <%s> run quit\n' % (fn.encode('hex'),) )
        to_gs.flush()

        page = 1
        while 1:
            line = from_gs.readline()
            if line == '':
                break
            m = pagesize_re.match( line )
            if m:
                pagesize = tuple([float(i) for i in m.groups()])
                
            elif line.find( 'press <return> to continue' ) != -1:
                imagefile = '%s/page%08d.ppm' % (tmpdir, page)

                if params.output:
                    if page == 1:
                        page1 = cStringIO.StringIO()
                        f = page1
                    else:
                        root, ext = os.path.splitext( params.output )
                        outfn = root + '.%04d' % (page,) + ext
                        f = open( outfn, 'wb' )
                else:
                    buffer = cStringIO.StringIO()
                    f = buffer
                        
                process_image( imagefile, bbox, pagesize, page, f )
                os.remove( imagefile )

                if not params.output:
                    sys.stdout.write( buffer.getvalue() )
                    buffer.close()
                    if params.verbose >= 20:
                        print >> err, '  wrote to <stdout>'
                elif page > 1:
                    f.close()
                    if params.verbose >= 10:
                        print >> err, 'wrote page %d to [%s]' % (page, outfn)
                
                page += 1
                try:
                    to_gs.write( '\n' )
                    to_gs.flush()
                except IOError, errno:
                    if sys.platform == 'win32' and errno.errno == 22:
                        pass
                    else:
                        raise
    finally:
        for i in os.listdir( tmpdir ):
            os.remove( os.path.join(tmpdir, i) )
        os.rmdir( tmpdir )

    if page1:
        if page > 2:
            root, ext = os.path.splitext( params.output )
            outfn = root + '.0001' + ext
        else:
            outfn = params.output

        f = open( outfn, 'wb' )
        f.write( page1.getvalue() )
        f.close()
        page1.close()
    
        if params.verbose >= 10:
            print >> err, 'wrote page 1 to [%s]' % (outfn,)

def process_image( fn, bbox, pagesize, pagenum, f ):
    if params.verbose >= 10:
        print >> err, 'processing page %d...' % (pagenum,)
        
    if params.verbose >= 20:
        print >> err, '  temp image is [%s]' % (fn,)
        print >> err, '  page size: %.3f %.3f' % pagesize
        
    newsize = get_desired_size( pagesize )

    im = Image.open( fn )
    if im.size != newsize:
        if params.verbose >= 20:
            print >> err, '  reducing size from %r to %r' % (im.size, newsize)
        im = im.resize( newsize, Image.ANTIALIAS )
    if params.grayscale and im.mode != 'L':
        if params.verbose >= 20:
            print >> err, '  converting to grayscale'
        im = im.convert( 'L' )
    if params.turns:
        if params.verbose >= 20:
            print >> err, '  rotating %d quarter-turns' % (params.turns,)
        im = im.transpose( (Image.ROTATE_90,Image.ROTATE_180,Image.ROTATE_270)[params.turns-1] )
    if params.padding > 0:
        if params.verbose >= 20:
            print >> err, '  padding image'
        p = params.padding
        im2 = Image.new( 'RGB', (newsize[0]+2*p, newsize[1]+2*p), params.paddingcolor )
        im2.paste( im, (p,p) )
        im = im2

    if params.verbose >= 20:
        print >> err, '  writing in %s format' % (params.format,)
    im.save( f, params.format )


def get_desired_size( pagesize ):
    w = params.width
    h = params.height
    p = 2 * params.padding

    if params.turns % 2:
        w, h = h, w
        
    if w and h:
        w -= p
        h -= p
    elif w:
        w -= p
        h = int( float(w) / pagesize[0] * pagesize[1] ) 
    elif h:
        h -= p
        w = int( float(h) / pagesize[1] * pagesize[0] )
    else:
        w = int( pagesize[0] )
        h = int( pagesize[1] )

    return w, h
        
        


def usage( gs ):
    print 'usage: %s [options] <filename>' % (sys.argv[0],)
    print 
    print '  -?, --help                   show this message'
    print '  --version                    print version info and exit'
    print 
    print '  -w, --width=#                set output image width (in pixels)'
    print '  -h, --height=#               set output image height (in pixels)'
    print '  -m, --margin=<dim>           set bbox margin (default none)'
    print '        example dimensions:      4in, 35mm, 30.1cm, 144pt'
    print '  -p, --padding=#              set image padding (in pixels; default=0)'
    print '  -b, --black                  pad with black instead of white'
    print '  -r, --rotation=#             integer # of quarter-turns to rotate (ccw)'
    print '  -s, --resolution=<res>       set GS resolution manually'
    print '  -g, --grayscale              output grayscale image'
    print
    print '  -o, --output=<filename>      output file name'
    print '  -f, --format=FMT             output image format (overrides extension)'
    print '          formats: ', ', '.join(output_formats)
    print
    print '  -i, --interpreter=<gs>       location of Ghostscript'
    print '          prefix with "+" to search PATH'
    print '          default: "%s"' % (gs,)
    print '  -q, --quiet                  run silently, except for errors'
    print '  -v, --verbose                be verbose'

def showversion():
    print version
    print
    print copyright
    
        
def main( **kw ):
    for k, v in kw.iteritems():
        setattr( params, k, v )
    
    if len(sys.argv) < 2:
        usage( params.gs )
        return 2

    try:
        opts, args = getopt.getopt(sys.argv[1:], '?w:h:m:p:bo:qvgf:r:s:i:',
                                   ['width=',
                                    'height=',
                                    'margin=',
                                    'padding=',
                                    'black',
                                    'output=',
                                    'quiet',
                                    'verbose',
                                    'grayscale',
                                    'format=',
                                    'rotation=',
                                    'resolution=',
                                    'interpreter=',
                                    'version',
                                    ])
    except getopt.GetoptError:
        usage( params.gs )
        return 2
    output = None
    for o, a in opts:
        if o in ('-?', '--help'):
            usage( params.gs )
            return 0
        elif o == '--version':
            showversion()
            return 0
        elif o in ('-v', '--verbose'):
            params.verbose = 20
        elif o in ('-q', '--quiet'):
            params.verbose = 0
        elif o in ('-g', '--grayscale'):
            params.grayscale = 1
        elif o in ('-b', '--black'):
            params.paddingcolor = (0,0,0)
        elif o in ('-w', '--width'):
            try:
                params.width = int(a)
            except ValueError:
                print >> err, "didn't understand width value %r" % (a,)
                return 1
        elif o in ('-h', '--height'):
            try:
                params.height = int(a)
            except ValueError:
                print >> err, "didn't understand height value %r" % (a,)
                return 1
        elif o in ('-p', '--padding'):
            try:
                params.padding = int(a)
            except ValueError:
                print >> err, "didn't understand padding value %r" % (a,)
                return 1
        elif o in ('-m', '--margin'):
            params.margin = interpret_dimension(a)
            if params.margin is None:
                print >> err, "didn't understand margin dimension %r" % (a,)
                return 1
        elif o in ('-o', '--output'):
            params.output = a
        elif o in ('-f', '--format'):
            if a.upper() not in output_formats:
                print >> err, "output format %r is unknown" % (a,)
                return 1
            params.format = a.upper()
        elif o in ('-r', '--rotation'):
            try:
                params.turns = int(a)
            except ValueError:
                print >> err, "bad value %r for rotation, must be integer" % (a,)
                return 1
        elif o in ('-s', '--resolution'):
            nums = a.lower().split('x')
            if len(nums) != 1 and len(nums) != 2:
                print >> err, "didn't understand resolution %r" % (a,)
                return 1
            try:
                nums = [str(float(i)) for i in nums]
            except ValueError:
                print >> err, "didn't understand resolution %r" % (a,)
                return 1
            params.res = 'x'.join(nums)
        elif o in ('-i', '--interpreter'):
            params.gs = a

    params.finish()
            

    if params.width is not None:
        if params.width <= 0:
            print >> err, "width must be positive"
            return 1
        if params.width - 2 * params.padding <= 0:
            print >> err, "padding too big for width"

    if params.height is not None:
        if params.height <= 0:
            print >> err, "height must be positive"
            return 1
        if params.height - 2 * params.padding <= 0:
            print >> err, "padding too big for height"

    if len(args) == 0:
        print >> err, "no input file specified!"
        return 1
    
    if len(args) > 1:
        print >> err, "too many input files specified!"
        return 1

    if params.output is None:
        if params.format is None:
            print >> err, "must specify output filename and/or format!"
            return 1
        
        if sys.platform == "win32":
            import msvcrt
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    else:
        if params.format is None:
            root, ext = os.path.splitext( params.output )
            try:
                params.format = extension_map[ext.lower()]
            except KeyError:
                print >> err, "can't determine output format from file extension"
                return 1
        

    user_ps = args[0]
    user_path = os.path.abspath( user_ps )
    bbox, orient = read_headers( user_path )
    params.turns = (params.turns + orient) % 4
    if bbox:
        bbox = apply_margin( bbox )
    
    process_ps_file( user_path, bbox )

if __name__ == "__main__":
    r = main()
    sys.exit( r )
    
