import cStringIO
import struct

def linebreak( data, maxlen ):
    if maxlen <= 0:
        return data
    length = len(data)
    out = []
    for i in range(0,length,maxlen):
        out.append( data[i:i+maxlen] )
    return '\n'.join( out )

def ascii85_encode( data ):
    l = len(data)
    pack = struct.pack
    unpack = struct.unpack
    out = cStringIO.StringIO()

    for i in xrange(0,l/4*4,4):
        (a,) = unpack( '>I', data[i:i+4] )
        if a == 0:
            out.write( 'z' )
        else:
            a, c5 = divmod( a, 85 )
            a, c4 = divmod( a, 85 )
            a, c3 = divmod( a, 85 )
            c1, c2 = divmod( a, 85 )
            out.write( pack( 'BBBBB', c1+33, c2+33, c3+33, c4+33, c5+33 ) )

    extend = data[l-l%4:]
    if extend:
        count = len(extend)
        extend += '\0\0\0'
        (a,) = unpack( '>I', extend[:4] )
        a, c5 = divmod( a, 85 )
        a, c4 = divmod( a, 85 )
        a, c3 = divmod( a, 85 )
        c1, c2 = divmod( a, 85 )
        tmp = pack( 'BBBBB', c1+33, c2+33, c3+33, c4+33, c5+33 )
        out.write( tmp[:count+1] )

    return out.getvalue()

def runlength_encode( data ):
    if not data:
        return chr(128)
    
    runs = []
    current = ''
    lastk = None
    count = 0

    for k in data:
        if k == lastk:
            if count:
                count += 1
            else:
                if len(current) > 1:
                    runs.append( current[:-1] )
                current = lastk
                count = 2
        else:
            if count:
                if count == 2:
                    runs.append( current * 2 )
                else:
                    runs.append( (current, count) )
                count = 0
                current = lastk = k
            else:
                current += k
                lastk = k
    if count:
        runs.append( (current, count) )
    else:
        runs.append( current )

    runs2 = [ runs[0] ]
    flag = (type(runs[0]) is str)
    for i in runs[1:]:
        if flag and type(i) is str:
            runs2[-1] += i
        else:
            runs2.append( i )
            flag = (type(i) is str)

    del runs

    out = cStringIO.StringIO()
    for i in runs2:
        if type(i) is str:
            for j in xrange(0,len(i),128):
                data = i[j:j+128]
                out.write( chr(len(data)-1) )
                out.write( data )
        else:
            k, count = i
            while count > 128:
                out.write( '\x81' + k )
                count -= 128
            if count == 1:
                out.write( '\x00' + k )
            else:
                out.write( chr(257-count) + k )

    out.write( '\x80' )

    return out.getvalue()
                
            
        
if __name__ == '__main__':
    def runlength_decode( data ):
        l = len(data)
        i = 0

        out = ''

        while i < l:
            x = ord(data[i])
            if x == 128:
                if i != l-1:
                    raise ValueError, 'early exit'
                return out
            elif x < 128:
                out += data[i+1:i+x+2]
                i += x+2
            else:
                out += data[i+1] * (257-x)
                i += 2

        raise ValueError, 'missed EOD'

    x1 = 'byybyybyybyybyyb' + 'y'*130 + 'byybyybyybyybyybyybyyabracadabbbrarraaaaaaa'
    print x1
    e1 = runlength_encode( x1 )
    print repr(e1)
    print len(x1), len(e1)
    y1 = runlength_decode( e1 )
    print y1, y1 == x1

            
