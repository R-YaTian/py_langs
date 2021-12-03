# py_langs module BY R-YaTian
# Version: 1.1

import gettext
from struct import unpack
from platform import system
from os import path
from locale import getlocale, getdefaultlocale, setlocale, LC_ALL, getpreferredencoding
try:
    from py_langs.po2buf import make
except:
    from po2buf import make

LANG_CODES = {
    'en_us': 'en',
    'en_gb': 'en',
    'en_au': 'en',
    'en_in': 'en',
    'en_ca': 'en',
    'en_ie': 'en',
    'en_nz': 'en',
    'en_za': 'en',
    'en_sg': 'en',
    'zh_sg': 'zh_hans',
    'zh_my': 'zh_hans',
    'zh_cn': 'zh_hans',
    'zh_hk': 'zh_hant',
    'zh_mo': 'zh_hant',
    'zh_tw': 'zh_hant'
}

def lang_init(default_lang = 'en', lang_dir = 'languages'):
    region = None
    if system() == 'Darwin':
        from subprocess import Popen, PIPE
        get_loc = Popen(['defaults', 'read', '.GlobalPreferences', 'AppleLanguages'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        outs, errs = get_loc.communicate()
        tmp_code = outs.decode('utf-8').split('\n')[1]
        loc = tmp_code[tmp_code.find("\"")+1:tmp_code.rfind("\"")].replace('-', '_').lower()
        if loc.count('_') is 2:
            region = loc[loc.rfind("_")+1:]
            loc = loc[:loc.rfind("_")]
    else:
        loc = getdefaultlocale()[0]

    try:
        loca = LANG_CODES[loc.lower()]
    except:
        loca = loc.lower()

    langsys = path.join(lang_dir, loca + '.po')
    lange = path.join(lang_dir, 'en.po')

    if loca != default_lang:
        if path.exists(langsys):
            buff = make(langsys)
            lang = GNUTranslations_Mod(buff)
            lang.install()
        else:
            if path.exists(lange):
                buff = make(lange)
                lang = GNUTranslations_Mod(buff)
                lang.install()
            else:
                gettext.install('')
    else:
        gettext.install('')

    info = [loc.lower(), loca, region]
    return info

#-----------------------------------------------------------------------------
# gettext.GNUTranslations
# Modify by R-YaTian

class GNUTranslations_Mod(gettext.NullTranslations):
    # Magic number of .mo files
    LE_MAGIC = 0x950412de
    BE_MAGIC = 0xde120495

    # Acceptable .mo versions
    VERSIONS = (0, 1)

    def _get_versions(self, version):
        """Returns a tuple of major version, minor version"""
        return (version >> 16, version & 0xffff)

    def _parse(self, buf):
        # Parse the .mo file header, which consists of 5 little endian 32
        # bit words.
        self._catalog = catalog = {}
        self.plural = lambda n: int(n != 1) # germanic plural by default
        buflen = len(buf)
        # Are we big endian or little endian?
        magic = unpack('<I', buf[:4])[0]
        if magic == self.LE_MAGIC:
            version, msgcount, masteridx, transidx = unpack('<4I', buf[4:20])
            ii = '<II'
        elif magic == self.BE_MAGIC:
            version, msgcount, masteridx, transidx = unpack('>4I', buf[4:20])
            ii = '>II'
        else:
            raise OSError(0, 'Bad magic number')

        major_version, minor_version = self._get_versions(version)

        if major_version not in self.VERSIONS:
            raise OSError(0, 'Bad version number ' + str(major_version))

        # Now put all messages from the .mo file buffer into the catalog
        # dictionary.
        for i in range(0, msgcount):
            mlen, moff = unpack(ii, buf[masteridx:masteridx+8])
            mend = moff + mlen
            tlen, toff = unpack(ii, buf[transidx:transidx+8])
            tend = toff + tlen
            if mend < buflen and tend < buflen:
                msg = buf[moff:mend]
                tmsg = buf[toff:tend]
            else:
                raise OSError(0, 'File is corrupt')
            # See if we're looking at GNU .mo conventions for metadata
            if mlen == 0:
                # Catalog description
                lastk = None
                for b_item in tmsg.split(b'\n'):
                    item = b_item.decode().strip()
                    if not item:
                        continue
                    k = v = None
                    if ':' in item:
                        k, v = item.split(':', 1)
                        k = k.strip().lower()
                        v = v.strip()
                        self._info[k] = v
                        lastk = k
                    elif lastk:
                        self._info[lastk] += '\n' + item
                    if k == 'content-type':
                        self._charset = v.split('charset=')[1]
                    elif k == 'plural-forms':
                        v = v.split(';')
                        plural = v[1].split('plural=')[1]
                        self.plural = gettext.c2py(plural)
            # Note: we unconditionally convert both msgids and msgstrs to
            # Unicode using the character encoding specified in the charset
            # parameter of the Content-Type header.  The gettext documentation
            # strongly encourages msgids to be us-ascii, but some applications
            # require alternative encodings (e.g. Zope's ZCML and ZPT).  For
            # traditional gettext applications, the msgid conversion will
            # cause no problems since us-ascii should always be a subset of
            # the charset encoding.  We may want to fall back to 8-bit msgids
            # if the Unicode conversion fails.
            charset = self._charset or 'ascii'
            if b'\x00' in msg:
                # Plural forms
                msgid1, msgid2 = msg.split(b'\x00')
                tmsg = tmsg.split(b'\x00')
                msgid1 = str(msgid1, charset)
                for i, x in enumerate(tmsg):
                    catalog[(msgid1, i)] = str(x, charset)
            else:
                catalog[str(msg, charset)] = str(tmsg, charset)
            # advance to next entry in the seek tables
            masteridx += 8
            transidx += 8

    def lgettext(self, message):
        missing = object()
        tmsg = self._catalog.get(message, missing)
        if tmsg is missing:
            if self._fallback:
                return self._fallback.lgettext(message)
            tmsg = message
        if self._output_charset:
            return tmsg.encode(self._output_charset)
        return tmsg.encode(getpreferredencoding())

    def lngettext(self, msgid1, msgid2, n):
        try:
            tmsg = self._catalog[(msgid1, self.plural(n))]
        except KeyError:
            if self._fallback:
                return self._fallback.lngettext(msgid1, msgid2, n)
            if n == 1:
                tmsg = msgid1
            else:
                tmsg = msgid2
        if self._output_charset:
            return tmsg.encode(self._output_charset)
        return tmsg.encode(getpreferredencoding())

    def gettext(self, message):
        missing = object()
        tmsg = self._catalog.get(message, missing)
        if tmsg is missing:
            if self._fallback:
                return self._fallback.gettext(message)
            return message
        return tmsg

    def ngettext(self, msgid1, msgid2, n):
        try:
            tmsg = self._catalog[(msgid1, self.plural(n))]
        except KeyError:
            if self._fallback:
                return self._fallback.ngettext(msgid1, msgid2, n)
            if n == 1:
                tmsg = msgid1
            else:
                tmsg = msgid2
        return tmsg
