import re

from google.appengine.api import images, mail

import webapp2


def batches(itr, batch_size):
    b = []
    for e in itr:
        b.append(e)
        if len(b) == batch_size:
            yield b
            b = []
    if b:
        yield b

_height = 16

with open('pix.png', 'rb') as f:
    pix = f.read()
bar = images.composite([(pix, 0, y, 1., images.TOP_LEFT) for y in xrange(_height)],
                       1, _height, 0xff000000, images.PNG)

def _char_img(bits):
    return images.composite([(bar, x, 0, 1., images.TOP_LEFT) for x, c in enumerate(bits) if c == '1'],
                            100, _height, 0x00000000, images.PNG)

class Code128Handler(webapp2.RequestHandler):
    _patterns = (
        '11011001100', '11001101100', '11001100110', '10010011000', '10010001100',
        '10001001100', '10011001000', '10011000100', '10001100100', '11001001000',
        '11001000100', '11000100100', '10110011100', '10011011100', '10011001110',
        '10111001100', '10011101100', '10011100110', '11001110010', '11001011100',
        '11001001110', '11011100100', '11001110100', '11101101110', '11101001100',
        '11100101100', '11100100110', '11101100100', '11100110100', '11100110010',
        '11011011000', '11011000110', '11000110110', '10100011000', '10001011000',
        '10001000110', '10110001000', '10001101000', '10001100010', '11010001000',
        '11000101000', '11000100010', '10110111000', '10110001110', '10001101110',
        '10111011000', '10111000110', '10001110110', '11101110110', '11010001110',
        '11000101110', '11011101000', '11011100010', '11011101110', '11101011000',
        '11101000110', '11100010110', '11101101000', '11101100010', '11100011010',
        '11101111010', '11001000010', '11110001010', '10100110000', '10100001100',
        '10010110000', '10010000110', '10000101100', '10000100110', '10110010000',
        '10110000100', '10011010000', '10011000010', '10000110100', '10000110010',
        '11000010010', '11001010000', '11110111010', '11000010100', '10001111010',
        '10100111100', '10010111100', '10010011110', '10111100100', '10011110100',
        '10011110010', '11110100100', '11110010100', '11110010010', '11011011110',
        '11011110110', '11110110110', '10101111000', '10100011110', '10001011110',
        '10111101000', '10111100010', '11110101000', '11110100010', '10111011110',
        '10111101110', '11101011110', '11110101110', '11010000100', '11010010000',
        '11010011100', '1100011101011')

    @classmethod
    def varB(cls, s):
        def _val(c):
            val = ord(c) - 32
            if not 0 <= val < len(cls._patterns):
                raise ValueError, "Character '%s' out of encoding range" % c
            return val
        return [104] + map(_val, s)

    @classmethod
    def varC(cls, s):
        values = []
        while s:
            pair = s[:2]
            values.append(int(pair))
            s = s[2:]
        return [105] + values

    @classmethod
    def check(cls, values):
        return (sum(v * (w or 1) for w, v in enumerate(values))) % 103

    @classmethod
    def patterns(cls, s):
        if len(s) % 2 == 0 and re.match(r'^[0-9]+$', s):
            values = cls.varC(s)
        else:
            values = cls.varB(s)
        return [cls._patterns[v] for v in (values + [cls.check(values), -1])]

    def get(self, value):
        patterns = self.patterns(value)
        imgs = [(len(p), _char_img(p)) for p in patterns]
        (width, final), imgs = imgs[0], imgs[1:]
        for w, img in imgs:
            final = images.composite([(final, 0, 0, 1., images.TOP_LEFT),
                                      (img, width, 0, 1., images.TOP_LEFT)],
                                     width + w, _height, 0x00000000, images.PNG)
            width += w
        self.response.headers['Content-Type'] = mail.EXTENSION_MIME_MAP['png']
        self.response.headers['Cache-Control'] = "public, max-age=%d" % (24 * 60 * 60)
        self.response.out.write(final)

app = webapp2.WSGIApplication([
   (r'/code128/(.+)\.png', Code128Handler),
])
