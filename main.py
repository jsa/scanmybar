from io import BytesIO
import re

from PIL import Image
import webapp2


class Code128Handler(webapp2.RequestHandler):
    # pattern ref: http://en.wikipedia.org/wiki/Code_128#Bar_code_widths
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

    def __init__(self, *a, **kw):
        self.unescape = kw.pop('unescape', False)
        super(Code128Handler, self).__init__(*a, **kw)

    def varB(self, s):
        vals = [104]
        s = iter(s)
        for c in s:
            if self.unescape and c == '\\':
                e = s.next()
                # detect double backslash
                if e == '\\':
                    c = '\\'
                else:
                    vals.append(int(e + s.next() + s.next()))
                    continue
            val = ord(c) - 32
            if not 0 <= val < len(self._patterns):
                raise ValueError, "Character '%s' out of encoding range" % c
            vals.append(val)
        return vals

    def patterns(self, s):
        if len(s) % 2 == 0 and re.match(r"^[0-9]+$", s):
            values = self.varC(s)
        else:
            values = self.varB(s)
        return [self._patterns[v] for v in (values + [self.check(values), -1])]

    def get(self, value):
        patterns = self.patterns(value.decode('utf-8'))
        scale = max(1, min(10, int(self.request.get('s', "1"))))

        # generate the barcode pattern as a byte string
        row, width, pix, bit = "", 0, 0, 7
        for p in patterns:
            for c in p:
                width += 1
                # "1" signifies existence of the bar, ie. 0 is blank ie. white
                if c == "0":
                    pix |= 1 << bit
                if bit > 0:
                    bit -= 1
                else:
                    row += chr(pix)
                    pix, bit = 0, 7
        if bit < 7:
            # include the trailing bits, extra data gets ignored
            row += chr(pix)

        # logging.debug("row (%dpx): %s" % (width, "".join(format(ord(c), "08b") for c in row)))

        # raw args: raw mode, stride, orientation
        barcode = Image.fromstring("1", (width, 1), row, "raw", "1", 0, 1) \
                       .resize((width * scale, 30 * scale))
        with BytesIO() as pngb:
            barcode.save(pngb, "PNG")
            png = pngb.getvalue()

        self.response.headers['Content-Type'] = "image/png"
        self.response.headers['Cache-Control'] = "public, max-age=%d" % (60 * 60)
        self.response.out.write(png)


class EscapedCode128Handler(Code128Handler):
    def __init__(self, *a, **kw):
        super(EscapedCode128Handler, self).__init__(*a, unescape=True, **kw)


class DocHandler(webapp2.RequestHandler):
    def get(self):
        """This should be enough documentation."""
        self.redirect("/code128/Hello%20world!.png")


app = webapp2.WSGIApplication([
   (r"^/$", DocHandler),
   (r"^/\^code128/(.+)\.png$", EscapedCode128Handler),
   (r"^/code128/(.+)\.png$", Code128Handler),
])
