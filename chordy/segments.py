from collections import Counter
from itertools import groupby

import regex as re

from .chord import Chord


class Segment:
    pass


class Span(Segment):
    def __init__(self, text, chord):
        self.text = text
        self.chord = chord

    def __format__(self, code):
        return ("<{:%s}: {}>" % code).format(self.chord, self.text)

    def __len__(self):
        return max(
            len(self.text) if self.text is not None else 0,
            len(self.chord) if self.chord is not None else 0,
        )

    def __getattr__(self, attr):
        if attr in Chord.exheritables:

            def fn(*args):
                if self.chord is None:
                    return self
                data = dict(self.__dict__)
                data["chord"] = getattr(self.chord, attr)(*args)
                return Span(**data)

            return fn
        raise AttributeError(
            f"'{self.__class__.__name__} object has no attribute '{attr}'"
        )

    def to_tex(self, flags=""):
        if self.chord:
            if self.text:
                return r"^{%s}%s" % (self.chord.to_monospace(flags=flags), self.text)
            return r"^{%s}\empty " % self.chord.to_monospace(flags=flags)
        return self.text

    def to_html(self, flags=""):
        return "".join(
            [
                "<span class='span{}'><span class='chord'>".format(
                    " empty" if not self.text else ""
                ),
                self.chord.to_html(flags=flags) if self.chord else "&nbsp;",
                "</span>",
                (self.text or "").replace(" ", "&nbsp;"),
                "</span>",
            ]
        )


class Newline(Segment):
    def __repr__(self):
        return "\n"

    def to_tex(self, **kwargs):
        return "\\\\\n"

    def to_html(self, **kwargs):
        return "<br>"


class Section(Segment):
    def __init__(self, title):
        self.title = title

    def __repr__(self):
        return f"[{self.title}]\n"
        # return "SECTION\n"

    def to_tex(self, **kwargs):
        return "\\begin{%s}\n" % self.title.lower()

    def to_html(self, **kwargs):
        return f"<h3>{self.title}</h3>"


def line_replacements(line):
    tokens = line.split(" ")
    out = []
    for token in tokens:
        if out and (match := re.match(r"\(?(?:x(\d+)|(\d+)x)\)?", token)):
            number = int(next(filter(bool, match.groups())))
            out.extend([out[-1]] * (number - 1))
            continue
        out.append(token)
    return " ".join(out)


def token_type(token):
    if token.startswith("["):
        return "meta"
    if token in "Aa":
        return "ambiguous"
    if Chord.is_chord(token):
        return "chord"
    if token.isupper() and token.endswith(":"):
        return "meta"
    if token.lower().strip(":") in ["bridge", "verse", "chorus", "chords"]:
        return "meta"
    if re.match(r"^\(x\d\)$", token):
        return "instruct"
    return "word"


def line_type(line):
    tokens = [token for token in line.split(" ") if token]
    if not tokens:
        return "empty"
    types = Counter(token_type(token) for token in tokens)
    if len(types) == 2 and set(types) & {"ambiguous"}:
        types.pop("ambiguous")
    if len(types) == 2 and set(types) == {"meta", "word"}:
        types.pop("word")
    if len(types) == 1:
        type_, _ = types.popitem()
        if type_ == "ambiguous":
            type_ = "chord"
        return type_
    return "/".join(types)


def spans_from_single(line, ltype):
    if ltype == "word":
        # FIXME keep previous chord?
        # but not fixing this probably doesn't hurt
        yield Span(text=line, chord=None)
    elif ltype == "chord":
        for chord in line.split(" "):
            if not chord:
                continue
            yield Span(text=None, chord=Chord.from_string(chord))
    elif ltype == "empty":
        pass
    elif ltype == "meta":
        yield Section(line.strip().strip("[]"))
    else:
        raise NotImplementedError(line, ltype)


def spans_from_pair(cline, tline):
    spans = []
    cur_chord = None
    text = []
    for ws, group in groupby(cline, lambda x: x == " "):
        cstr = "".join(group)
        clen = len(cstr)
        if ws:
            text.extend(tline[:clen])
            tline = tline[clen:]
            spans.append(Span(text="".join(text), chord=cur_chord))
            cur_chord = None
            text = []
            continue
        cur_chord = Chord.from_string(cstr)
        text.extend(tline[:clen])
        tline = tline[clen:]
    if text or cur_chord:
        spans.append(Span(text="".join(text), chord=cur_chord))
    if tline:
        spans[-1].text += tline
    yield from spans


def get_segments(lines):
    prev = None
    for line in lines:
        line = line.rstrip("\n") + " "
        line = line_replacements(line)
        ltype = line_type(line)
        if not prev:
            prev = line, ltype
            continue
        pline, ptype = prev
        if ptype == "chord" and ltype == "word":
            yield from spans_from_pair(pline, line)
            yield Newline()
            prev = None
            continue
        yield from spans_from_single(pline, ptype)
        yield Newline()
        prev = line, ltype
    if prev is not None:
        yield from spans_from_single(*prev)
        yield Newline()
