from io import StringIO
from textwrap import dedent

import regex

from .segments import get_segments, Newline, Span, Section
from .chord import Chord, KrautException


class Song:
    def __init__(self, title, segments):
        self.title = title
        self.segments = segments

    @classmethod
    def from_file(cls, file, name=""):
        lines = list(file)
        try:
            return cls(name, list(get_segments(lines)))
        except KrautException:
            return cls(name, list(get_segments(lines, german=True)))

    def to_monospace(self, flags=""):
        io = StringIO()

        def flush_lines(cache):
            last_chord_full_width = False
            for span in cache:
                if last_chord_full_width:
                    io.write(" ")
                if span.chord:
                    the_str = ("{:%s}" % flags).format(span.chord)
                else:
                    the_str = ""
                io.write(the_str.ljust(len(span)))
                last_chord_full_width = span.chord and len(span) == len(span.chord)

            io.write("\n")
            for span in cache:
                io.write((span.text or "").ljust(len(span)))
            io.write("\n")
            cache.clear()

        line_cache = []
        for segment in self.segments:
            if isinstance(segment, Span):
                line_cache.append(segment)
                continue
            if line_cache:
                flush_lines(line_cache)
            if not isinstance(segment, Newline):
                io.write(repr(segment))
        if line_cache:
            flush_lines(line_cache)
        return io.getvalue()

    def to_tex(self, flags=""):
        io = StringIO()
        io.write(dedent(
            r"""
            \documentclass{article}
            \usepackage{leadsheets}
            \begin{document}
            %%SONG
            \begin{song}{title={%s}}
            """[1:] % self.title
        ))
        section = None
        for segment in self.segments:
            if isinstance(segment, Section):
                if section:
                    io.write("\\end{%s}\n" % section.envname)
                section = segment
            io.write(segment.to_tex(flags=flags))
        if section:
            io.write("\\end{%s}\n" % section.envname)
        io.write(dedent(
            r"""
            \end{song}
            %ENDSONG
            \end{document}
            """.lstrip()
        ))
        document = io.getvalue()
        # remove extra backslashes at beginning of sections (cosmetic)
        document = regex.sub(r"\\begin\{(.*?)\}(\s|\\\\)+", r"\\begin{\1}\n", document)
        # remove extra backslashes at end of sections (necessary)
        document = regex.sub(r"[\s\\]+\\end\{(.*?)\}", r"\n\\end{\1}", document)
        return document

    def to_html(self, flags=""):
        return "\n".join([
            "<html><head><style>",
            """
            .span {
                line-height: 2em;
                display: inline-flex;
                flex-direction: column;
                text-align: left;
            }

            .chord {
                top: -1.8em;
            }

            .span.empty {
                margin-right: 0.5em;
            }
            .bhack {
                position: relative;
                left: -4px;
                letter-spacing: -7px;
            }
            """,
            "</style></head><body>",
            "".join(segment.to_html(flags=flags) for segment in self.segments),
            "</body></html>",
        ])

    def __getattr__(self, attr):
        if attr in Chord.exheritables:

            def fn(*args):
                data = dict(self.__dict__)
                data["segments"] = [
                    getattr(segment, attr)(*args)
                    if isinstance(segment, Span)
                    else segment
                    for segment in data["segments"]
                ]
                return Song(**data)

            return fn
        raise AttributeError(
            f"'{self.__class__.__name__} object has no attribute '{attr}'"
        )
