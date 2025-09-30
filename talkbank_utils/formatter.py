import regex as re
from string import ascii_letters, digits, punctuation, whitespace

root = r"[A-Za-z0-9:]+"

re_phonological = re.compile(rf"&\+{root}")
re_fillers = re.compile(rf"&-{root}")
re_nonwords = re.compile(rf"&~{root}")
re_events = re.compile(rf"&={root}")
re_omitted = re.compile(rf"0{root}?")

re_terminators = re.compile(r"\+[^\s\\]+")

re_brackets = re.compile(r"\[.*?\]")
re_scopes = re.compile(r"<.*?>")
re_shortenings = re.compile(r"\(.*?\)")
re_special_form = re.compile(rf"({root})@[a-z:]+")


class Formatter:
    """
    Whether or not these annotations should be filtered out.
    For more info, see: https://talkbank.org/0info/manuals/CHAT.pdf

    phonological_fragment: bool, optional
        &+
        Default is True
    fillers: bool, optional
        &-
        Default is True
    nonwords: bool, optional
        &~
        Default is True
    simple_events: bool, optional
        &=
        Default is True
    omitted: bool, optional
        0
        Default is True
    terminators: bool, optional
        +
        Default is True
    brackets: bool, optional
        [ ]
        Default is True
    scopes: bool, optional
        <  >
        Default is True
    shortenings:
        ( )
        True deletes everything in it and false deletes just the parentheses
        Default is False
    special_form
        utterance@form
        True deletes entire text while false just deletes the marker '@form'
        Default is False
    unintelligible:
        xxx
        Default is True
    uninterpretable:
        yyy
        Default is True
    discard_empty:
        After removals, discard if only one character or empty
        Default is True
    final_filter:
        Keep only alphanumeric and punctuation.
        Default is True

    """

    def __init__(self, **kwargs):
        kwargs.setdefault("phonological_fragment", True)
        kwargs.setdefault("fillers", True)
        kwargs.setdefault("nonwords", True)
        kwargs.setdefault("simple_events", True)
        kwargs.setdefault("terminators", True)
        kwargs.setdefault("brackets", True)
        kwargs.setdefault("scopes", True)
        kwargs.setdefault("shortenings", False)
        kwargs.setdefault("special_form", False)

        kwargs.setdefault("unintelligible", True)
        kwargs.setdefault("uninterpretable", True)

        kwargs.setdefault("discard_empty", True)
        kwargs.setdefault("final_filter", True)
        self.__dict__.update(kwargs)

    def format_line(self, line: str) -> str | None:
        """
        Format an utterance according to arguments passed in initialization.

        Assumes that it is utterance only.

        Returns formatted string or None if discard_empty is True and conditions are matched.
        """

        if self.unintelligible:
            line = line.replace("xxx", "")
        if self.uninterpretable:
            line = line.replace("yyy", "")

        if self.phonological_fragment:
            line = re_phonological.sub("", line)
        if self.fillers:
            line = re_fillers.sub("", line)
        if self.nonwords:
            line = re_nonwords.sub("", line)
        if self.simple_events:
            line = re_events.sub("", line)
        if self.terminators:
            line = re_terminators.sub("", line)
        if self.brackets:
            line = re_brackets.sub("", line)
        if self.scopes:
            line = re_scopes.sub("", line)
        if self.shortenings:
            line = re_shortenings.sub("", line)
        else:
            line = line.replace("(", "")
            line = line.replace(")", "")
        if self.special_form:
            line = re_special_form.sub("", line)
        else:
            text = re_special_form.search(line)
            if text is not None:
                text = text.group(1)
                line = re_special_form.sub(text, line)

        if self.unintelligible:
            line = line.replace("xxx", "")
        if self.uninterpretable:
            line = line.replace("yyy", "")

        line = re.sub(r"\s+", " ", line)
        line = re.sub(r"\s+([.,!?;:])", r"\1", line).strip()

        # Remove _ since it's used in context of named entities.
        line = line.replace("_", " ")

        # Final filtering alphanumeric + ending punctuation.
        if self.final_filter:
            chs = []
            mask = ascii_letters + digits + whitespace
            for i, ch in enumerate(line):
                if ch in mask:
                    chs.append(ch)
                elif i == len(line) - 1 and ch in punctuation:
                    chs.append(ch)
            line = "".join(chs)

        # Format out empty string
        if (line == "" or len(line) <= 2 or "0" in line) and self.discard_empty:
            return None

        return line


if __name__ == "__main__":
    """
    Some test cases.
    """

    formatter = Formatter()

    assert formatter.format_line("&=yells hm .") == "hm."
    assert formatter.format_line("yeah [/] yeah [/] yeah .") == "yeah yeah yeah."
    assert formatter.format_line("oh nope +/.") == "oh nope"
    assert formatter.format_line("yyy .") is None
    assert (
        formatter.format_line("yeah we gotta [: have to] sit on the pee_pee pot .")
        == "yeah we gotta sit on the pee_pee pot."
    )
    assert formatter.format_line("yyy yyy yyy &=squeals !") is None
    assert formatter.format_line("&=yells &=vocalizes .") is None
    assert formatter.format_line("xxx do it .") == "do it."
    assert formatter.format_line("don('t)") == "don't"
    assert formatter.format_line("&+ba back") == "back"
