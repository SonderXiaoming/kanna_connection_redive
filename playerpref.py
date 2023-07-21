from urllib.parse import unquote
from re import finditer
from base64 import b64decode
from struct import unpack
from random import choice
key = b'e806f6'

def _deckey(s) -> str:
    b = b64decode(unquote(s))
    return bytes([key[i % len(key)] ^ b[i] for i in range(len(b))])

def _decval(k, s):
    b = b64decode(unquote(s))
    key2 = k.encode('utf8') + key
    b = b[0:len(b) - (11 if b[-5] != 0 else 7)]
    return bytes([key2[i % len(key2)] ^ b[i] for i in range(len(b))])

def _ivstring() -> str:
    return ''.join([choice('0123456789') for _ in range(32)])

def _encode(dat: str) -> str:
    return f'{len(dat):0>4x}' + ''.join([(chr(ord(dat[int(i / 4)]) + 10) if i % 4 == 2 else choice('0123456789')) for i in range(0, len(dat) * 4)]) + _ivstring()

def decryptxml(content):
    result = {}
    for re in finditer(r'<string name="(.*)">(.*)</string>', content):
        g = re.groups()
        try:
            key = _deckey(g[0]).decode('utf8')
        except:
            continue
        val = _decval(key, g[1])
        if key == 'UDID':
            val = ''.join([chr(val[4 * i + 6] - 10) for i in range(36)])
        elif 'SHORT_UDID' in key:
            result["viewer_id"] = key.replace("SHORT_UDID", "")
            key = "SHORT_UDID"
            val = _encode(str(val))            
        elif len(val) == 4:
            val = str(unpack('i', val)[0])
        result[key] = val
    return result['UDID'].replace("-", ""), result["viewer_id"]
