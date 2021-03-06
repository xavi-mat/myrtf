#!/usr/bin/env python3

"""
Simple RTF creator.

Constants, classes and functions to create simple rtf documents.
Main 'RTF' class defines objects where add paragraphs, footnotes, and text with
different formatting options. Properties of paper size and margins are also
supported.
By Xavimat.
"""

# USEFUL:
# https://www.oreilly.com/library/view/rtf-pocket-guide/9781449302047/ch01.html

__version__ = "0.0.58"
__author__ = "Xavimat"
__date__ = "2020-04-04"

from time import strftime as _strftime
from os import path as _path

# CONSTANTS:
CM2TW = 566.929133858
TW2CM = 1.0 / CM2TW
IN2TW = 1440
TW2IN = 1.0 / IN2TW

_fonts = {}
_colors = {}


def rtf_encode(text):
    """
    Convert unicode text to rtf format with substitution of non-ascii
    characters. (Based on Martijn Pieters' code.)
    """
    return ''.join(['\\u%i?' % (ord(e) if e < u'\u8000' else ord(e) - 65536) if (e > '\x7f' or e < '\x20' or e in u'\\{}') else str(e) for e in text])


def totwip(m):
    """Convert 'mm', 'cm', 'in' to twips."""
    m = str(m)
    if m == "":
        return -1
    if m.isdigit():
        return int(m)
    if m.endswith('cm'):
        m2 = float(m[:-2])
        return round(m2 * CM2TW)
    if m.endswith('mm'):
        m2 = float(m[:-2])
        return round(m2 * CM2TW / 10)
    if m.endswith('in'):
        m2 = float(m[:-2])
        return round(m2 * IN2TW)
    raise ValueError('measure impossible to parse: "' + m + '".')


class Font(object):
    """Fonts for the font table."""

    def __init__(self, id, fontname, family='fnil', fprq='', fcharset='', falt=""):
        """
        Register a new font for the font table.

        kwargs:
        - id: 'fN', where N is an integer.
        - family: (str) 'fnil', 'froman', 'fswiss', 'fnil', 'fbidi'...
        - fpqr: (str)  # pitch
        - fcharset: (str)
        - fontname: (str)
        - falt: (str) alternate font name to use if the fontname is not available.

        """
        if id[0] != 'f' or not id[1:].isdigit():
            raise ValueError('"' + id + '" is not a correct "id" for a Font.')

        self.id = id
        self.fontname = fontname
        self.family = family
        self.fprq = fprq
        self.fcharset = fcharset
        self.falt = falt

        _fonts[id] = self

    @property
    def output(self):
        """Text to create the font table."""
        o ="{\\" + self.id
        o += "\\" + self.family
        if self.fprq: o += "\\fprq" + self.fprq
        if self.fcharset: o += "\\fcharset" + self.fcharset
        o += " " + self.fontname
        if self.falt: o += "{\\*\\falt " + self.falt + "}"
        o += ";}\n"
        return o


class Color:
    """Colors for the color table."""

    def __init__(self, id, red=0, green=0, blue=0):
        """
        Register a new color for the color table.

        Arguments:
        - id: (str) containing only digits.
        - red, green, blue: (int) Numbers in range 0-255.
        """

        if not id.isdigit():
            raise ValueError('"' + id + '" is not a correct "id" for a Color.')

        self.id = id
        self.red = red
        self.green = green
        self.blue = blue

        _colors[id] = self

    @property
    def output(self):
        """Output for the color table."""
        o = "\\red" + str(self.red)
        o += "\\green" + str(self.green)
        o += "\\blue" + str(self.blue)
        o += ";\n"
        return o


class Stylesheet(object):

    def __init__(self, name="", lang="1024"):
        self.name = name
        self._styles = {}
        _Style(self, "s0", "Default", lang=lang)

    def new_style(self, id, name, **kwargs):
        """Create a new style for the stylesheet."""
        _Style(self, id, name, **kwargs)

    def _add_style(self, style):
        """Add style to stylesheet."""
        if self._styles:

            maxkey = max(self._styles.keys())

            if style.key < maxkey:
                maxid = self.style(maxkey).id
                raise ValueError('Styles must be added in order. Can\'t add "' +
                    style.id + '" after "' + maxid + '".')

            if style.key in self._styles:
                raise ValueError('Can\'t overwrite style "' + style.id + '".')

        self._styles[style.key] = style

    def del_style(self, style):
        """
        Delete style from stylesheet.

        Not yet implemented.
        # TODO: inform of other styles being based on this one.
        # TODO: delete style only if no other styles are "based on" this one.
        """
        print("Not yet implemented.")

    def style(self, keyid):
        """Return style by 'key' or 'id'."""
        if keyid in self._styles:
            return self._styles[keyid]

        for i in self._styles.values():
            if keyid == i.id:
                return i

        raise ValueError('Style "' + str(keyid) + '" not in stylesheet.')

    @property
    def output(self):
        """Output of the Stylesheet for the rtf file."""
        o = "{\\stylesheet\n"

        for style in self._styles.values():
            o += style.output

        o += "}\n"

        return o


def _check_style_id(id):
    """Check if 'id' has the correct format for a Style ('sN', 'csN')."""
    if id[0] == 's':
        if not id[1:].isdigit():
            raise ValueError('"' + id + '" is not a correct "id" for a Style.')
        key = int(id[1:])
    elif id[0:2] == 'cs':
        if not id[2:].isdigit():
            raise ValueError('"' + id + '" is not a correct "id" for a Style.')
        key = int(id[2:])
    else:
        raise ValueError('"' + id + '" is not a correct "id" for a Style.')
    return key


class _Style(object):
    """Styles for the stylesheet."""

    def __init__(self, sheet, id, name, **kwargs):
        """Register a new style for the stylesheet."""

        key = _check_style_id(id)

        accepted = ['sbasedon', 'snext', 'align', 'f', 'fs', 'sl', 'sb', 'sa', 'keepn', 'b', 'i', 'scaps', 'caps', 'widctlpar', 'nowidctlpar', 'hyphpar', 'rtlpar', 'ltrpar', 'cf', 'fi', 'li', 'ri', 'lang']

        not_accepted = set(kwargs.keys()) - set(accepted)

        if not_accepted:
            raise ValueError('Arguments not accepted in Styles: ' + str(not_accepted))

        self.key = key
        self.id = id
        self.name = rtf_encode(name)
        self.sbasedon = id
        self.snext = id
        self.align = "qj"  # qc, qj, ql, qr (center, justified, left, right)
        self.f = ""  # font id (defined in font table)
        self.fs = ""  # font size
        self.sl = ""  # Line-spacing.
        self.sb = ""  # Space before in twips (default is 0).
        self.sa = ""  # Space after in twips (default is 0).
        self.keepn = ""  # Keep paragraph with the next paragraph.
        self.b = ""  # bold.
        self.i = ""  # italics.
        self.scaps = ""  # small caps.
        self.caps = ""  # all caps
        self.widctlpar = ""  # Widow/orphan control.
        self.nowidctlpar = ""  # No widow/orphan control.
        self.hyphpar = ""  # Automatic hyphenation

        self.rtlpar = ""
        self.ltrpar = ""
        self.cf = ""  # Color foreground
        self.fi = ""  # First-line indent in twips (default is 0).
        self.li = ""  # Left indent in twips (default is 0).
        self.ri = ""  # Right indent in twips (default is 0).
        self.lang = ""  # language code (see code tables)

        if "sbasedon" in kwargs:

            id2 = kwargs["sbasedon"]  # 'id' of base style.

            key2 = _check_style_id(id2)

            base_style = sheet.style(key2)

            for i in accepted:
                setattr(self, i, getattr(base_style, i))

            self.sbasedon = id2
            self.snext = id

        if 'snext' in kwargs:
            _check_style_id(kwargs['snext'])

        for k, v in kwargs.items():
            setattr(self, k, v)

        sheet._add_style(self)

    @property
    def apply(self):
        """Apply properties to text and paragraph when the style is used."""
        o = "\\" + self.id

        if self.align: o += "\\" + self.align
        if self.f: o += "\\" + self.f
        if self.fs: o += "\\fs" + self.fs
        if self.sl: o+= "\\sl" + self.sl + "\\slmult1"
        if self.sb: o += "\\sb" + self.sb
        if self.sa: o += "\\sa" + self.sa
        if self.keepn: o += "\\keepn"
        if self.b: o += "\\b"
        if self.i: o += "\\i"
        if self.scaps: o += "\\scaps"
        if self.caps: o += "\\caps"
        if self.widctlpar: o += "\\widctlpar"
        if self.nowidctlpar: o += "\\nowidctlpar"
        if self.hyphpar: o += "\\hyphpar"
        if self.rtlpar: o += "\\rtlpar"
        if self.ltrpar: o += "\\ltrpar"
        if self.cf: o += "\\cf" + self.cf
        if self.fi: o += "\\fi" + self.fi
        if self.li: o += "\\li" + self.li
        if self.ri: o += "\\ri" + self.ri
        if self.lang: o += "\\lang" + self.lang
        #if self.: o += "\\" + self.

        o += " "
        return o

    @property
    def output(self):
        """Text to create the stylesheet in the rtf file."""
        o = "{\\" + self.id
        o += "\\sbasedon" + self.sbasedon.replace('s', '')
        o += "\\snext" + self.snext.replace('s', '')

        o += self.apply

        o += self.name + ";"
        o += "}\n"
        return o

stylesheets =  {}
_sheet = Stylesheet("Hebrew-Catalan")
_Style(_sheet, "s21", "Normal", sbasedon="s0", f="f1", fs="24", lang="1024")
_Style(_sheet, "s22", "Normal hebreu", sbasedon="s21", f="f2", fs="24",
    align="qj", rtlpar=True, lang="1037")
_Style(_sheet, "s23", "Nota", sbasedon="s21", f="f1", fs="18", li="227",
    fi="-227")
_Style(_sheet, "s24", "Nota hebreu", sbasedon="s23", f="f2", fs="22",
    lang="1307")
_Style(_sheet, "s25", "Estil_Titols", sbasedon="s21", align="qc", keepn=True,
    b=True, f="f1", fs="28", sb="1132", sa="566", lang="1609")
_Style(_sheet, "s26", "Nota normal", sbasedon="s23", f="f1", fs="20", li="227",
    fi="-227", lang="1027")  # Catalan
_Style(_sheet, "s28", "Estil_Titols_Amagats", sbasedon="s0", align="ql",
    keepn=True, f="f1", fs="4", cf="3", lang="1609")
stylesheets["Hebrew-Catalan"] = _sheet

_sheet = Stylesheet("Greek-Italian", lang="1040")
_Style(_sheet, "s21", "Normal", sbasedon="s0", f="f1", fs="24", lang="1040"),
_Style(_sheet, "s23", "Nota", sbasedon="s21", f="f1", fs="18", li="227",
    fi="-227", lang="1040"),
_Style(_sheet, "s25", "Estil_Titols", sbasedon="s21", align="qc", keepn=True,
    b=True, f="f1", fs="28", sb="1132", sa="566", lang="1609"),
_Style(_sheet, "s27", "Normal grec", sbasedon="s21", f="f1", fs="24", sl="276",
    hyphpar=True, lang="1609"),  # Ancient Greek
_Style(_sheet, "s28", "Estil_Titols_Amagats", sbasedon="s0", align="ql",
    keepn=True, f="f1", fs="4", cf="3", lang="1609"),
_Style(_sheet, "s29", "Nota italia", sbasedon="s23", f="f1", fs="20", li="227",
    fi="-227", hyphpar=True, lang="1040"),  # Italian
stylesheets["Greek-Italian"] = _sheet

_sheet = Stylesheet("Greek-Spanish")
_Style(_sheet, "s21", "Normal", sbasedon="s0", f="f1", fs="24", lang="1024"),
_Style(_sheet, "s23", "Nota", sbasedon="s21", f="f1", fs="18", li="227",
    fi="-227"),
_Style(_sheet, "s25", "Estil_Titols", sbasedon="s21", align="qc", keepn=True,
    b=True, f="f1", fs="28", sb="1132", sa="566", lang="1609"),
_Style(_sheet, "s26", "Nota Spanish", sbasedon="s23", f="f1", fs="20", li="227",
    fi="-227", lang="1034"),  # Spanish (Castilian)
_Style(_sheet, "s27", "Normal grec", sbasedon="s21", f="f1", fs="24", sl="276",
    hyphpar=True, lang="1609"),  # Ancient Greek
_Style(_sheet, "s28", "Estil_Titols_Amagats", sbasedon="s0", align="ql",
    keepn=True, f="f1", fs="4", cf="3", lang="1609"),
stylesheets["Greek-Spanish"] = _sheet


class RTF:
    """
    Main class. Contains all text, formatting options, information of fonttable
    and stylsheet.
    """

    deflang = 1027  # Catalan
    adeflang = 1037 # Asian default language (Hebrew)
    _fonttable = [
        Font("f0", "Times New Roman", family="fnil"),
        Font("f1", "Linux Libertine", family="fnil"),
        Font("f2", "SBL BibLit", family="fnil"),
        Font("f3", "Linux Biolinum", family="fswiss"),
        ]
    _colortable = [
        Color("1", red=128, green=128, blue=128),      # Grey
        Color("2", red=128, green=64, blue=0),         # Orange
        Color("3", red=255, green=255, blue=255),      # White
        ]
    _stylesheet = Stylesheet()

    author = "author"
    _ftn_options = {
        "position": "ftnbj",
        "ftnrstpg": False,
        "ftnrestart": False,
        "numbering": "ftnnar"
        }
        # position:
        # ftntj: Footnotes beneath text (top justified).
        # ftnbj: Footnotes at the bottom of the page (bottom justified).
        # restart:
        # ftnrstpg: Restart footnote numbering each page.
        # ftnrestart: Footnote numbers restart at each section.
        # numbering:
        # ftnnar: Footnote numbering—Arabic numbering (1, 2, 3, …).
        # ftnnalc: Footnote numbering—Alphabetical lowercase (a, b, c, …).
        # ftnnauc: Footnote numbering—Alphabetical uppercase (A, B, C, …).
        # ftnnrlc: Footnote numbering—Roman lowercase (i, ii, iii, …).
        # ftnnruc: Footnote numbering—Roman uppercase (I, II, III, …).

    paperh = 16838 # paper height
    paperw = 11906 # paper width
    margl = 1134   # margin left
    margr = 1134   # margin right
    margt = 1134   # margin top
    margb = 1134   # margon bottom
    verbose = False


    def __init__(self, title="Document Title", **kwargs):
        """
        Register an RTF object to keep all info and create everything at the end.
        """
        self.title = title
        self.filename = title
        self._all_text = []
        self._all_lines = []
        self._paropen = False
        self._noteopen = False
        self._par_style = self._stylesheet.style(0)
        self._note_style = self._stylesheet.style(0)

        for key in kwargs:
            setattr(self, key, kwargs[key])

        self._log('RTF Object created with title "' + title + '".')

    def _log(self, txt, end='\n'):
        if self.verbose: print(txt, end=end)

    def _a(self, txt):  # Add text to all_lines.
        self._all_lines.append(txt)

    def _a2(self, txt):  # Add encoded text to all_lines.
        self._all_lines.append(rtf_encode(txt))

    def _t(self, txt):  # Add text.
        self._all_text.append(txt)

    def _t2(self, txt):  # Add encoded text.
        self._all_text.append(rtf_encode(txt))


    def create(self, filename="", folder=""):
        """
        At the end, create the entire rtf file.
        1- Put all_lines info in 'all_lines' list.
        2- Write the 'all_lines' list to a file.
        """

        if filename: self.filename = filename
        if folder: self.filename = _path.join(folder, self.filename)

        self.close_par()

        self._log('CREATING file...')

        self._all_lines = []

        # HEADER:

        # RTF prolog
        self._a("{\\rtf1\\ansi\\deff0")
        self._a("\\deflang" + str(self.deflang) + "\\adeflang" + str(self.adeflang) + "\n")

        # Font table
        self._a("{\\fonttbl\n")
        for font in self._fonttable:
            self._a(font.output)
        self._a("}\n")

        # Color table
        self._a("{\\colortbl\n")
        self._a(";\n")
        for color in self._colortable:
            self._a(color.output)
        self._a("}\n")

        # Style sheet
        #self._a("{\\stylesheet\n")
        #for style in self._stylesheet.values():
        #    self._a(style.output)
        #self._a("}\n")
        self._a(self._stylesheet.output)

        # Generator
        self._a("{\\*\\generator myrtf_by_xavimat_" + __version__ + "}\n")

        # DOCUMENT AREA:

        # Info
        self._a("{\\info\n")
        self._a("{\\title ")
        self._a2(self.title)
        self._a("}\n")
        self._a("{\\author ")
        self._a2(self.author)
        self._a("}\n")
        self._a(_strftime("{\\creatim\\yr%Y\\mo%m\\dy%d\\hr%H\\min%M}\n"))
        self._a("}\n")

        # Document Formatting Properties

        # - Page information
        # Example: "\\paperh16838\\paperw11906\\margl1134\\margr1134\\margt1134\\margb1134"
        self._a("\\paperh" + str(self.paperh))
        self._a("\\paperw" + str(self.paperw))
        self._a("\\margl" + str(self.margl))
        self._a("\\margr" + str(self.margr))
        self._a("\\margt" + str(self.margt))
        self._a("\\margb" + str(self.margb))
        self._a("\n")

        # - Footnotes and endnotes
        self._a("\\" + self._ftn_options["position"])
        if self._ftn_options["ftnrstpg"]:
            self._a("\\ftnrstpg")
        if self._ftn_options["ftnrestart"]:
            self._a("\\ftnrestart")
        self._a("\\" + self._ftn_options["numbering"])
        self._a("\n")

        # TEXT
        for i in self._all_text:
            self._a(i)

        # CLOSING
        self._a("\\par }")

        self._log('EXPORTING "' + self.title + '" as "' + self.filename + '.rtf"...')
        
        with open(self.filename+".rtf", "w+") as t:

            for i in self._all_lines:
                t.write(i)

        self._log('DONE!')


    def par(self, txt="", style=""):
        """
        Open a new paragraph with style.
        Close former paragraph and/or note if needed.
        """

        self.close_par()

        style = self._search_style(style)

        self._paropen = True

        self._t("{\\pard " + style.apply)
        self._t2(txt)

        self._log('(Open paragraph:)', end=' ')
        if txt: self._log(txt, end='')


    def close_par(self):
        """If par is open, close it. Close also note if needed."""

        self.close_note()

        if self._paropen:
            self._t("\\par}\n")
            self._paropen = False
            self._log(' (Close paragraph.)')


    def text(self, txt, format=""):
        """
        Add text, with format if needed:
        i: italics; b: bold; sub: subscript; super: superscript;
        scaps: small caps.
        """
        if format in ["bi", "ib"]: self._t("{\\i\\b ")
        #elif format == "i":            self._t("{\\i ")
        #elif format == "b":          self._t("{\\b ")
        #elif format == "sub":        self._t("{\\sub ")
        #elif format == "super":      self._t("{\\super ")
        #elif format == "scaps":      self._t("{\\scaps ")
        elif format:                 self._t("{\\" + format + " ")

        self._t2(txt)

        if format: self._t("}")

        self._log(txt, end='')


    # Text-like function. Add italic text.
    def i(self, txt): self.text(txt, format="i")
    # Text-like function. Add bold text.
    def b(self, txt): self.text(txt, format="b")
    # Text-like function. Add subscript text.
    def sub(self, txt): self.text(txt, format="sub")
    # Text-like function. Add superscript text.
    def super(self, txt): self.text(txt, format="super")
    # Text-like function. Add small caps text.
    def scaps(self, txt): self.text(txt, format="scaps")


    def note(self, txt, style="", anchor="\\chftn"):
        """Open a new note with style. Close former note if needed."""

        self.close_note()

        style = self._search_style(style, typ="note")

        self._noteopen = True

        self._t('{\\super '+ anchor + "{\\footnote " + anchor + "\\pard\\plain ")
        self._t(style.apply)
        self._t2(txt)

        self._log('(Open footnote:) ', end='[')
        if txt: self._log(txt, end='')


    def close_note(self):
        """If note is open, close it."""
        if self._noteopen:
            self._t("}}\n")
            self._noteopen = False
            self._log('] (Close footnote.)', end='')


    def set_layout(self, default="", ph="", pw="", mt="", mb="", ml="", mr=""):
        """
        Define the layout (paper width/height and margins).
        - default: 'A4', 'B5', 'A5', 'royal', 'digest', 'LAS'.
        - pw: paper width
        - ph: paper height
        - mt: margin top
        - mb: margin bottom
        - ml: margin left
        - mr: margin right
        Values in twips, inches or centimeters.
        """
        ph = totwip(ph)
        pw = totwip(pw)
        mt = totwip(mt)
        mb = totwip(mb)
        ml = totwip(ml)
        mr = totwip(mr)

        if default == "A4":  # size: A4, margins 2cm
            ph, pw, mt, mb, ml, mr = 16838, 11906, 1134, 1134, 1134, 1134
        elif default == "B5":  # size: B5, margins 3cm, 2.5cm, 2cm, 2cm
            ph, pw, mt, mb, ml, mr = 14173, 9978, 1701, 1417, 1134, 1134
        elif default == "A5":  # size: A5
            ph, pw, mt, mb, ml, mr = 11906, 8391, 1151, 720, 567, 862
        elif default == "royal":  # size: royal (15.57cm, 23.39cm)
            ph, pw, mt, mb, ml, mr = 13262, 8827, 1152, 720, 864, 864
        elif default == "digest":  # size: digest (5.5in, 8.5in)
            ph, pw, mt, mb, ml, mr = 12240, 7920, 1151, 720, 567, 862
        elif default == "LAS":  # size: LAS (17cm, 24cm)
            ph = totwip("24cm")
            pw = totwip("17cm")
            mt = totwip("1.9cm")
            mb = totwip("2.5cm")
            ml = totwip("2.2cm")
            mr = totwip("2.3cm")
        elif default:
            raise ValueError("Default layout '" + default + "' does not exist.")

        if ph < 0: ph = self.paperh
        if pw < 0: pw = self.paperw
        if mt < 0: mt = self.margt
        if mb < 0: mb = self.margb
        if ml < 0: ml = self.margl
        if mr < 0: mr = self.margr

        self.paperh = ph
        self.paperw = pw
        self.margt = mt
        self.margb = mb
        self.margl = ml
        self.margr = mr

        if default:
            self._log('Layout set to "' + default + '".')
        else:
            self._log('Layout set.')


    @property
    def layout(self):
        """Page layout (paper width/height and margins)."""
        txt = "Layout in twips:\n"
        txt += " Paper height: " + str(self.paperh) + "\n"
        txt += " Paper width: " + str(self.paperw) + "\n"
        txt += " Top margin: " + str(self.margb) + "\n"
        txt += " Bottom margin: " + str(self.margb) + "\n"
        txt += " Left margin: " + str(self.margl) + "\n"
        txt += " Rigth margin: " + str(self.margr)
        return txt
    @layout.setter
    def layout(self, layout):
        self.set_layout(layout)


    @property
    def stylesheet(self):
        return self._stylesheet.output
    @stylesheet.setter
    def stylesheet(self, default):
        if type(default) == Stylesheet:
            self._stylesheet = default
            self._log('Stylesheet set to "' + default.name + '".')
        elif default not in stylesheets:
            raise ValueError('Default stylesheet "' + default + '" not found.')
        else:
            self._stylesheet = stylesheets[default]
            self._log('Stylesheet set to "' + default + '".')


    def style(self, keyid):
        """
        Return style from stylesheet by 'key' or 'id'. Can change style attributes.
        """
        return self._stylesheet.style(keyid)


    def new_style(self, id, name, **kwargs):
        """Create a style-object and add it to the stylesheet."""
        _Style(self._stylesheet, id, name, **kwargs)
        self._log('New style "' + id + '" added to the stylesheet.')


    def set_style(self, style, typ="par"):
        """Set default style for 'typ' (par:paragraph, note:footnote)."""
        style = self._search_style(style, typ=typ)

        if typ == "note":
            self._note_style = style
        else:
            self._par_style = style

        self._log('Style for "' + typ + '" set to "'+style.id+'".')


    @property
    def par_style(self):
        """Default style for paragrahps."""
        return self._par_style.id
    @par_style.setter
    def par_style(self, style):
        self.set_style(style, typ="par")


    @property
    def note_style(self):
        """Default style for footnotes."""
        return self._note_style.id
    @note_style.setter
    def note_style(self, style):
        self.set_style(style, typ="note")


    def _search_style(self, keyid, typ="par"):
        """
        Return a Style object by 'key' or 'id'.
        Or the default, according to 'typ'.
        """
        if typ == "note":
            default = self._note_style
        else:
            default = self._par_style

        #for i in self._stylesheet.values():
        #    if i.id == keyid:
        #        return i

        if keyid:
            return self._stylesheet.style(keyid)
            #self._log('Style "' + keyid + '" not found. Defaulting to "' +
            #    default.id + '".')

        return default


    def fonttable(self):
        """
        Add fonts to the font table.
        Not yet implemented.
        """
        print("Not yet implemented.")


    def footnote_options(self):
        """
        General options for footnotes.
        Not yet implemented.
        """
        print("Not yet implemented.")
