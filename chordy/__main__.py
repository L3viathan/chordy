import click

from .song import Song


@click.command()
@click.argument("file", type=click.File("r"))
@click.option(
    "--type",
    "-T",
    "type_",
    type=click.Choice(["tex", "txt", "html"]),
    help="What file type chordy should produce.",
    default="txt",
)
@click.option(
    "--transpose", "-t", default=0, help="Amount of semitones to transpose up/down",
)
@click.option(
    "--simplify", "-s", is_flag=True, help="Whether to simplify the chords",
)
@click.option(
    "--flags", "-f", type=str, help="Sequence of 1-letter display codes", default=""
)
@click.option(
    "--prefer",
    "-p",
    help="Whether to prefer b/♭ or #/♯",
    type=click.Choice(["b", "#", "♯", "♭", "flat", "sharp"]),
)
def cli(file, type_, transpose, simplify, flags, prefer):
    """
    Convert a UG-style chord file into PDF/normalized chords.
    """
    song = Song.from_file(file)
    if prefer:
        flags += {"♯": "#", "♭": "b", "flat": "b", "sharp": "#"}.get(prefer, prefer)
    if transpose:
        song = song.transpose(transpose)
    if simplify:
        song = song.simplify()
    if type_ == "tex":
        print(song.to_tex(flags=flags))
    elif type_ == "html":
        print(song.to_html(flags=flags))
    else:
        print(song.to_monospace(flags=flags))


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
