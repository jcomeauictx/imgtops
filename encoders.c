#include <Python.h>

static PyObject* ASCII85Encode( PyObject* self, PyObject* args );
static PyObject* RunLengthEncode( PyObject* self, PyObject* args );
static PyObject* LineBreak( PyObject* self, PyObject* args );

static PyMethodDef EncoderMethods[] = {
    { "ascii85_encode", (PyCFunction)ASCII85Encode, METH_VARARGS },
    { "runlength_encode", (PyCFunction)RunLengthEncode, METH_VARARGS },
    { "linebreak", (PyCFunction)LineBreak, METH_VARARGS },
    { NULL, NULL }
};

void
#ifdef WIN32
__declspec( dllexport )
#endif
initencoders( void )
{
    PyObject* m;

    m = Py_InitModule( "encoders", EncoderMethods );
}

static PyObject* LineBreak( PyObject* self, PyObject* args )
{
    int length;
    int lines;
    int maxlen;
    char* data;
    char* out;
    PyObject* input;
    PyObject* result;
    int i;
    
    if ( !PyArg_ParseTuple( args, "O!i", &PyString_Type, &input, &maxlen ) )
	return NULL;

    if ( maxlen <= 0 )
    {
	Py_INCREF( input );
	return input;
    }

    PyString_AsStringAndSize( input, &data, &length );
    
    lines = (length-1)/maxlen + 1;

    result = PyString_FromStringAndSize( NULL, length + lines-1 );
    out = PyString_AsString( result );

    for ( i = 0; i < lines-1; ++i )
    {
	memcpy( out, data, maxlen );
	out[maxlen] = '\n';
	out += maxlen + 1;
	data += maxlen;
    }
    memcpy( out, data, length - (lines-1)*maxlen );

    return result;
}

static PyObject* ASCII85Encode( PyObject* self, PyObject* args )
{
    int length;
    unsigned char* data;
    PyObject* result;
    unsigned char* dataout;
    int lengthout;
    int i;
    unsigned int a;
    int g;
    unsigned int c5, c4, c3, c2, c1;
    

    if ( !PyArg_ParseTuple( args, "s#", (char*)&data, &length ) )
	return NULL;

    result = PyString_FromStringAndSize( NULL, length * 5 / 4 + 6 );
    dataout = PyString_AsString( result );
    lengthout = 0;

    g = (length / 4) * 4;
    for ( i = 0; i < g; i += 4 )
    {
	a = (data[i] << 24) | (data[i+1] << 16) | (data[i+2] << 8) | data[i+3];
	if ( a == 0 )
	{
	    *(dataout++) = 0x7a;
	    lengthout++;
	}
	else
	{
	    c5 = a % 85;
	    a /= 85;
	    c4 = a % 85;
	    a /= 85;
	    c3 = a % 85;
	    a /= 85;
	    c2 = a % 85;
	    c1 = a / 85;

	    *(dataout++) = c1 + 0x21;
	    *(dataout++) = c2 + 0x21;
	    *(dataout++) = c3 + 0x21;
	    *(dataout++) = c4 + 0x21;
	    *(dataout++) = c5 + 0x21;
	    lengthout += 5;
	}
    }

    if ( g < length )
    {
	a = (data[g] << 24) |
	    (((g+1<length) ? data[g+1] : 0) << 16) |
	    (((g+2<length) ? data[g+2] : 0) << 8) |
	    ((g+3<length) ? data[g+3] : 0);
	
	c5 = a % 85;
	a /= 85;
	c4 = a % 85;
	a /= 85;
	c3 = a % 85;
	a /= 85;
	c2 = a % 85;
	c1 = a / 85;
	
	*(dataout++) = c1 + 0x21;
	*(dataout++) = c2 + 0x21;
	*(dataout++) = c3 + 0x21;
	*(dataout++) = c4 + 0x21;
	*(dataout++) = c5 + 0x21;
	lengthout += length - g + 1;
    }

    _PyString_Resize( &result, lengthout );
    return result;
}
    
static PyObject* RunLengthEncode( PyObject* self, PyObject* args )
{
    int length;
    unsigned char* data;
    PyObject* result;
    int i = 0;
    int j;
    unsigned char* out;
    int outpos;
    int outlen;

    if ( !PyArg_ParseTuple( args, "s#", (char*)&data, &length ) )
	return NULL;

    //printf( "input is %d bytes\n", length );
    
    outlen = length;
    out = malloc( outlen );
    outpos = 0;

    while( i < length )
    {
	if ( i <= length-3 && data[i] == data[i+1] && data[i] == data[i+2] )
	{
	    j = 3;
	    while( j+i < length && data[j+i] == data[i] )
	    {
		if ( j < 128 )
		    ++j;
		else
		    break;
	    }

	    //printf( "%c (%02x) times %d\n", data[i], data[i], j );
	    if ( outpos + 2 > outlen )
	    {
		outlen = length / 16 + 256;
		out = realloc( out, outlen );
	    }
	    out[outpos] = 257 - j;
	    out[outpos+1] = data[i];
	    outpos += 2;
	    i += j;
	}
	else
	{
	    j = 0;
	    if ( i > length-3 )
		goto tail;
	    
	    while( data[i+j] != data[i+j+1] || data[i+j] != data[i+j+2] )
	    {
		j += 1;
		
		if ( i+j+2 >= length )
		{
		tail:
		    if ( outpos + j + 2 > outlen )
		    {
			outlen = length / 16 + 256;
			out = realloc( out, outlen );
		    }
	    
		    j = length - i;
		    if ( j > 128 )
		    {
			//printf( "128 bytes from pos %d\n", i );
			out[outpos] = 127;
			memcpy( out+outpos+1, data+i, 128 );
			outpos += 129;
			i += 128;
			j -= 128;
		    }
		    //printf( "%d bytes from pos %d\n", j, i );
		    out[outpos] = j-1;
		    memcpy( out+outpos+1, data+i, j );
		    outpos += j+1;
		    goto done;
		}

		if ( j == 128 )
		    break;
	    }

	    //printf( "%d bytes from pos %d\n", j, i );
	    out[outpos] = j-1;
	    memcpy( out+outpos+1, data+i, j );
	    outpos += j+1;
	    i += j;
	}
    }
 done:

    if ( outpos + 1 > outlen )
    {
	outlen += 1;
	out = realloc( out, outlen );
    }
    out[outpos++] = 128;
    
    result = PyString_FromStringAndSize( out, outpos );
    free( out );
    
    return result;
}


