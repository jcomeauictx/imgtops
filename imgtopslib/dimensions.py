import re

dimensions = {
    'in' : 72,
    'mm' : 72 / 25.4,
    'cm' : 72 / 2.54,
    'pt' : 1,
    'ft' : 72 * 12,
    'm' : 39.370079 * 72,
    }

dimension_re = re.compile( r'^(.*)(' + '|'.join(dimensions.keys()) + r')\s*$' )

def interpret_dimension( d ):
    m = dimension_re.match( d )
    if m is None:
        try:
            return float(d)
        except ValueError:
            return None
    num, dim = m.groups()
    try:
        num = float(num)
    except ValueError:
        return None
    return num * dimensions[dim]

if __name__ == '__main__':
    for i in ( '0.5in', '4in', '2.5in', '30cm', '300mm',
               '75pt', '75 pt', '75pt ', '75pm', '75pm8in',
               '7.5.5ft', '0', '00.0', '0.', '.0', '0.0.0', '56.5',
               ):
        print '%20s : %r' % (i, interpret_dimension(i) )
        
    
    
    
    
    
