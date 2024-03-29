import encoders
import math, sys

err = sys.stderr

ps_filternames = {
    'jpeg'    : ('/DCTDecode', 2),
    'deflate' : ('/FlateDecode', 3),
    'rle'     : ('/RunLengthDecode', 2),
    'hex'     : ('/ASCIIHexDecode', 2),
    'ascii85' : ('/ASCII85Decode', 2),
    }

ps_colorspaces = {
    'monochrome' : '/DeviceGray',
    'rgb'        : '/DeviceRGB',
    'cmyk'       : '/DeviceCMYK',
    }


unsupported = """ image
} {
  0 0 moveto 1 0 lineto 1 1 lineto 0 1 lineto closepath 0.9 setgray fill
  0 setgray /Helvetica-Bold findfont 0.8 scalefont setfont
  0 0 moveto (%d) dup true charpath pathbbox exch 4 1 roll
  add 2 div 0.5 exch sub 3 1 roll add 2 div 0.5 exch sub exch translate 
  0 0 moveto show
  1024 string %d { currentfile exch readstring pop } repeat
  0 %d getinterval currentfile exch readstring pop pop
}"""

def write_ps_image( f, lim, params ):
    w, h = size = lim.size

    palette, color, data, pipeline, maxlevel, skiplen = encode_image( lim, params )

    filters = 'currentfile'
    for i in pipeline:
        filters += ' %s filter' % (ps_filternames[i][0],)

    if maxlevel > 2:
        f.write( 'languagelevel %d ge {\n' % (maxlevel,) )

    if palette is not None:
        f.write( '[ /Indexed %s %d\n  %s\n  ] setcolorspace\n' % (ps_colorspaces[color], palette[0]-1, palette[1]) )
    else: 
        f.write( '%s setcolorspace\n' % (ps_colorspaces[color],) )
        
    f.write( '<<\n' )
    f.write( '  /ImageType 1\n' )
    f.write( '  /Width %d /Height %d\n' % size )
    f.write( '  /BitsPerComponent 8\n' )
    f.write( '  /ImageMatrix [%d 0 0 -%d 0 %d]\n' % (w,h,h) )

    if palette is not None:
        f.write( '  /Decode [0 255]\n' )
    elif color == 'monochrome':
        f.write( '  /Decode [0 1]\n' )
    elif color == 'rgb':
        f.write( '  /Decode [0 1 0 1 0 1]\n' )
    elif color == 'cmyk':
        f.write( '  /Decode [0 1 0 1 0 1 0 1]\n' )
        
    f.write( '  /DataSource ' )
    f.write( filters )
    f.write( '\n' )
    f.write( '>>' )

    if maxlevel > 2:
        f.write( unsupported % (maxlevel, skiplen / 1024, skiplen % 1024) )

    f.write( '\n' )
    f.write( data )

    return maxlevel

def encode_image( lim, params ):
    filters = []
    pal = None
    maxlevel = 2

    if lim.im.format == 'JPEG':
        if lim.im.mode == 'L':
            color = 'monochrome'
        elif lim.im.mode == 'RGB':
            color = 'rgb'
        elif lim.im.mode == 'CMYK':
            color = 'cmyk'
        else:
            raise ValueError, 'image mode "%s" not supported' % (im.mode,)
        if params.verbose >= 20:
            print >> err, '  image uses the', color, 'color space'
            print >> err, '  using DCT (JPEG) encoding'
        binary = lim.buffer.getvalue()
        filters.append( 'jpeg' )
    else:
        im = lim.im
        if im.mode == 'P':
            pal = im.palette
            if hasattr(pal, 'getdata'):
                # PIL 1.1.4 (and higher?)
                rawmode, rawdata = pal.getdata()
            else:
                # PIL 1.1.3 (and earlier?)
                rawmode = pal.rawmode
                rawdata = pal.data
                
            if rawmode == 'L':
                color = 'monochrome'
                size = 1
            elif rawmode == 'RGB':
                color = 'rgb'
                size = 3
            elif rawmode == 'CMYK':
                color = 'cmyk'
                size = 4
            else:
                raise ValueError, 'image mode "P-%s" not supported' % (pal.rawmode,)

            if params.verbose >= 20:
                print >> err, '  image uses a palette'

            size = len(rawdata) / size

            if params.force_hex:
                pal = size, '<\n' + encoders.linebreak( rawdata.encode('hex'), params.line_length ) + '\n>'
            else:
                pal = size, '<~\n' + encoders.linebreak( encoders.ascii85_encode( rawdata ), params.line_length ) + '\n~>'
        else:
            if im.mode in ('L', '1', 'I', 'F'):
                color = 'monochrome'
                if im.mode != 'L':
                    im = im.convert('L')
            elif im.mode in ('RGB', 'RGBA', 'YCbCr'):
                color = 'rgb'
                if im.mode != 'RGB':
                    im = im.convert('RGB')
            elif im.mode == 'CMYK':
                color = 'cmyk'
            else:
                raise ValueError, 'image mode "%s" not supported' % (im.mode,)

        if params.verbose >= 20:
            print >> err, '  image uses the', color, 'color space'

        binary = im.tostring()

        if params.level == 3:
            if params.verbose >= 20:
                print >> err, '  using zlib compression ',
            cbinary = binary.encode('zlib')
            if params.verbose >= 20:
                print >> err, '[factor %.4f]' % (len(cbinary)/float(len(binary)),)
            filters.append( 'deflate' )
        else:
            if params.verbose >= 20:
                print >> err, '  using rle compression ',
                sys.stdout.flush()
            cbinary = encoders.runlength_encode( binary )
            if params.verbose >= 20:
                print >> err, '[factor %.4f]' % (len(cbinary)/float(len(binary)),)
            filters.append( 'rle' )

        if len(cbinary) < len(binary):
            binary = cbinary
        else:
            filters.pop()
            if params.verbose >= 20:
                print >> err, '  compression is not a win, discarding'

    for i in filters:
        maxlevel = max(maxlevel, ps_filternames[i][1])
    if maxlevel == 2:
        operator = 'image'
    else:
        operator = 'ifelse'

    if params.binary_output:
        if params.verbose >= 20:
            print >> err, '  putting binary data in output'
        data = '%%%%BeginData: %d Binary Bytes\n%s\n' % (len(binary)+len(operator)+2,operator) + \
               binary + '\n%%EndData\n'
        skiplen = len(binary)
    else:
        if params.force_hex:
            if params.verbose >= 20:
                print >> err, '  encoding as hex'
            data = encoders.linebreak( binary.encode( 'hex' ), params.line_length )
            skiplen = len(data)+1
            data = operator + '\n' + data + '>\n'
            filters.append( 'hex' )
        else:
            if params.verbose >= 20:
                print >> err, '  encoding as ascii85'
            data = encoders.linebreak( encoders.ascii85_encode( binary ), params.line_length )
            skiplen = len(data)+2
            data = operator + '\n' + data + '~>\n'
            filters.append( 'ascii85' )
            
    filters.reverse()
    return pal, color, data, filters, maxlevel, skiplen

def compute_fit( (iw,ih), params ):
    if params.strict_eps:
        return 0, 0, iw, ih
    
    sw, sh    = params.paper_size
    landscape = params.landscape
    margin    = params.margin
    tw        = params.width
    th        = params.height

    if landscape:
        sw, sh = sh, sw

    pw = float(sw - margin * 2)
    ph = float(sh - margin * 2)

    if tw and not th:
        th = ih * float(tw) / iw
    elif th and not tw:
        tw = iw * float(th) / ih
    elif not tw and not th:
        if pw / iw < ph / ih:
            tw = pw
            th = ih * tw / iw
        else:
            th = ph
            tw = iw * th / ih
        
    scale = 1
    if tw > pw:
        scale = pw / tw
    if th > ph and ph / th < scale:
        scale = ph / th
    ow = tw * scale
    oh = th * scale

    ox = (sw-ow)/2
    oy = (sh-oh)/2

    return ox, oy, ow, oh

def write_postscript_header( fit, params, f, headers, level ):
    ox, oy, ow, oh = fit
    sw, sh         = params.paper_size
    landscape      = params.landscape

    f.write( '%!PS-Adobe-3.0 EPSF-3.0\n' )

    for kv in headers.iteritems():
        f.write( '%%%%%s: %s\n' % kv )
    
    f.write( '%%%%LanguageLevel: %d\n' % (level,) )
    
    if landscape:
        if params.strict_eps:
            f.write( '%%%%BoundingBox: -%d 0 0 %d\n' % (oh,ow) )
        else:
            f.write( '%%%%BoundingBox: %d %d %d %d\n' % \
                     (math.floor(sw-oy-oh), math.floor(ox),
                      math.ceil(sw-oy), math.ceil(ox+ow)) )
    else:
        f.write( '%%%%BoundingBox: %d %d %d %d\n' % \
                 (math.floor(ox), math.floor(oy),
                  math.ceil(ox+ow), math.ceil(oy+oh)) )

    if params.binary_output:
        f.write( '%%DocumentData: Binary\n' )
    else:
        f.write( '%%DocumentData: Clean7Bit\n' )

    f.write( '%%EndComments\n' )

    f.write( 'gsave\n' )
    if landscape:
        if params.strict_eps:
            f.write( '90 rotate %d %d scale\n' % fit[2:] )
        else:
            f.write( '90 rotate 0 %f translate\n' % (-sw,) )
            f.write( '%f %f translate %f %f scale\n' % fit )
    else:
        if params.strict_eps:
            f.write( '%d %d scale\n' % fit[2:] )
        else:
            f.write( '%f %f translate %f %f scale\n' % fit )
        
            

def write_postscript_footer( fit, params, f ):
    f.write( 'grestore\n' )
    f.write( 'showpage\n' )
    f.write( '%%EOF\n' )
    
