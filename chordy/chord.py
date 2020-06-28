import regex as re


class KrautException(Exception):
    pass

class AmbiguousChord(Exception):
    pass


def note_to_number(note, shift, german=False):
    if note is None:
        return None
    if german:
        if note == "H":
            note = "B"
        elif note == "B":
            if shift == "b":
                raise AmbiguousChord
            shift = "b"
    number = ["C", 0, "D", 0, "E", "F", 0, "G", 0, "A", 0, "B"].index(note.upper())
    if shift:
        number += "b #".index(shift) - 1
    return number % 12


def normalize_modifiers(modifiers):
    return [{"+": "aug"}.get(mod, mod) for mod in modifiers]


CHORD = re.compile(
    r"""^
    (?P<optional>\()?                       # opening paren, to indicate optionality
    (?P<main>[ABCDEFGHabcdefgh])            # bass chord. can already indicate minor!
    (?P<shift>[#b])?                        # shift semitone up or down
    (?P<minor>[m-])?                        # indicator for minor chord
    (?:
      \(?
      (?P<modifiers>
        sus[24]?                            # suspended chord
      | dim                                 # diminished chord
      | (?:aug|\+)                          # augmented chord
      | (?:\#|b|no|-|[mM]aj|M|add)?(?:\d+)  # regular/b'd added tone
      | M                                   # major 7, I guess...
      )
      \)?
    )*
    (?:/
    (?P<bass>[ABCDEFGHabcdefgh])            # bass tone
    (?P<bassshift>[#b])?                    # bass shift
    )?
    \)?
    $""",
    re.VERBOSE,
)


class Chord:
    exheritables = ["transpose", "simplify"]

    @classmethod
    def is_chord(cls, token):
        return CHORD.match(token) or token == "N.C."

    def __init__(self, tone, minor=False, bass=None, modifiers=None, optional=False):
        self.tone = tone
        self.minor = minor
        self.bass = bass
        self.modifiers = modifiers or []
        self.optional = optional

    @classmethod
    def from_string(cls, string, german=False):
        if string == "N.C.":
            return cls(tone=None)
        data = CHORD.match(string).capturesdict()
        main = data["main"][0]
        shift = data["shift"][0] if data["shift"] else None
        bass = data["bass"][0] if data["bass"] else None
        bassshift = data["bassshift"][0] if data["bassshift"] else None
        if "H" in (main, bass) and not german:
            raise KrautException

        tone = note_to_number(main, shift, german=german)
        bass = note_to_number(bass, bassshift, german=german)
        minor = bool(data["minor"]) or main.islower()
        modifiers = normalize_modifiers(data["modifiers"])
        optional = bool(data["optional"])
        return cls(
            tone=tone, minor=minor, bass=bass, modifiers=modifiers, optional=optional
        )

    @staticmethod
    def note(number, flags=""):
        if "b" in flags:
            the_note = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"][
                number
            ]
        else:
            the_note = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][number]
        if "f" in flags:
            the_note = the_note.replace("#", "♯").replace("b", "♭")
        return the_note

    def __format__(self, code):
        return self.to_monospace(flags=code)

    def to_monospace(self, flags=""):
        if self.tone is None:
            return "N.C."
        return "".join(
            [
                self.note(self.tone, flags=flags),
                "m" if self.minor else "",
                "".join(self.modifiers),
                f"/{self.note(self.bass, flags=flags)}" if self.bass is not None else "",
            ]
        )

    def __repr__(self):
        return self.to_monospace()

    def __len__(self):
        # approximate: flags can change length
        return len(self.to_monospace())

    def length(self, flags=""):
        return len(self.to_monospace(flags=flags))

    def transpose(self, semitones):
        if self.tone is None:
            return self
        data = dict(self.__dict__)
        data["tone"] = (data["tone"] + semitones) % 12
        if data["bass"] is not None:
            data["bass"] = (data["bass"] + semitones) % 12
        return Chord(**data)

    def simplify(self):
        # TODO: several levels of simplification possible. We'll start with the
        # most extreme:
        if self.tone is None:
            return self
        return Chord(self.tone, minor=self.minor)

    def to_html(self, flags=""):
        if self.tone is None:
            return "N.C."
        if "F" not in flags:
            flags += "f"
        parts = [self.note(self.tone, flags=flags)]
        if self.minor:
            parts.append("m")
        if self.modifiers:
            parts.append("<sup>")
            parts.append("".join(self.modifiers))
            parts.append("</sup>")
        if self.bass is not None:
            parts.append(f"/{self.note(self.bass, flags=flags)}")
        return "".join(parts)
