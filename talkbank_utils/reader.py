from pyannote.core import Annotation, Segment
import regex as re 
from pathlib import Path
from typing import Self

TIMESTAMP_BRACE = '\x15'

re_has_speaker = re.compile(r'\*[A-Z]+:')
re_timestamp = re.compile(rf'{TIMESTAMP_BRACE}([0-9]+_[0-9]+){TIMESTAMP_BRACE}')
re_nonalphanumpunc = re.compile("^[A-Za-z0-9 _.,!\"'/$]*")
re_nonverbal = re.compile(r"&=[a-zA-Z]+")
re_fillers = re.compile(r"&-[a-zA-Z]+")
re_nonwords = re.compile(r"&~[a-zA-Z]+")
re_incomplete = re.compile(r"\w*\(\w+\)\w*")
re_replacement = re.compile(r"\[: .*\]")

class Transcription:
    """Container for .cha with helper functions""" 


    """
        remove_unknown: bool, optional 
            Remove 'xxx' 
            Default is False 
        remove_unintelligible: bool, optional
            Remove 'yyy' 
            Default is False 
        remove_nonverbal: bool, optional 
            Remove '&=action'
            Default is True
        remove_fillers: bool, optional
            Remove '&-filler'
            Default is True
        remove_nonwords: bool, optional 
            Remove '&~nonword'
            Default is True
        remove_incomplete: bool, optional
            Remove '(wo)rds'
            Default is True 
        remove_replacement: bool, optional 
            Remove '[: replacement]'
            Default is True 


        discard_empty: bool, optional 
            After removals, discard if utterance is "."
            Default is False

        unknown_replacement: str, optional 
            What to replace 'xxx' with if remove_unknown is false 
            Default is '<UNKNOWN>'
        unintelligible_replacement: str, optional 
            What to replace 'y' with if remove_unintelligible is false 
            Default is '<UNINTELLIGIBLE>'
    """
    def __init__(self, raw_transcription: str, **kwargs):
        kwargs.setdefault('remove_unknown', False)
        kwargs.setdefault('remove_unintelligible', False)
        kwargs.setdefault('remove_nonverbal', True)
        kwargs.setdefault('remove_fillers', True)
        kwargs.setdefault('remove_nonwords', True)
        kwargs.setdefault('remove_incomplete', True)
        kwargs.setdefault('remove_replacement', True)

        kwargs.setdefault('discard_empty', False)

        kwargs.setdefault('unknown_replacement', '<UNKNOWN>')
        kwargs.setdefault('unintelligible_replacement', '<UNINTELLIGIBLE>')
        self.__dict__.update(kwargs)

        self.speakers = set() 
        self.annotation = Annotation() 

        lines = raw_transcription.split('\n')

        for line in lines: 
            self._parse_line(line)

    @classmethod
    def from_path(cls, path: str) -> Self: 
        f_in = open(path, 'r')
        raw_text = f_in.read() 
        f_in.close()
        return Transcription(raw_text)


    """ 
        Internal util function for parsing line 
        Only goes through @Participants line and any line with speaker format  

        - Adds segments to annotation 
        - Modifies speakers 
    """
    def _parse_line(self, line: str):
        if line.startswith("@Participants:"): 
            line = line.removeprefix("@Participants:").strip()
            # TODO: Handle optional speaker matching here 
        elif re_has_speaker.match(line):
            lines = line.split('\t')

            speaker = lines[0][1 : -1]
            timestamp = re_timestamp.search(lines[1])
            utterance = re_timestamp.sub("", lines[1])
            # Only care if it has timestamps. 
            if timestamp is None: 
                return 
            timestamp = timestamp.group(1)

            self.speakers.add(speaker)

            timestamps = timestamp.split('_')
            start = float(timestamps[0]) / 1_000
            end = float(timestamps[1]) / 1_000

            self.annotation[Segment(start, end)] = speaker

            # TODO: Properly handle dialogue 
            utterance = self._clean_utterance(utterance)

    def _clean_utterance(self, line: str) -> str|None: 
        line = line.replace('xxx', '' if self.remove_unknown\
                     else self.unknown_replacement) 
        line = line.replace('yyy', '' if self.remove_unintelligible\
                     else self.unintelligible_replacement)

        if self.remove_nonverbal: 
            line = re_nonverbal.sub('', line)

        if self.remove_fillers: 
            line = re_fillers.sub('', line)

        if self.remove_nonwords:
            line = re_nonwords.sub('', line)

        if self.remove_incomplete: 
            line = re_incomplete.sub('', line)

        if self.remove_replacement:
            line = re_replacement.sub('', line)
        
        line = line.strip() 
        if line == "." and self.discard_empty:
            return None 

        return line 

    def to_rttm(self): 
        return self.annotation.to_rttm()

class Reader: 
    """Reader class is used for loading a directory of .cha files to access"""

    def __init__(self, transcriptions: dict[str, Transcription]): 
        if len(transcriptions) == 0: 
            raise ValueError("Can't pass empty transcriptions to Reader")

        self.transcriptions = transcriptions

    @classmethod
    def from_dir(cls, dir: str): 
        transcriptions = {}
        for path in Path(dir).rglob('*.cha'):
            base_dir = Path(*path.parts[1 :]).with_suffix('')
            transcription = Transcription.from_path(path)
            transcriptions[base_dir] = transcription
        return Reader(transcriptions)
    """ 
        Dump transcriptions as rttms into the specified folder.
    """
    def dump(self, path: str):
        for base_dir, transcription in self.transcriptions.items(): 
            out_path = path / base_dir.with_suffix('.rttm')
            out_path.parent.mkdir(parents = True, exist_ok = True)

            with open(out_path, 'w') as f_out:
                f_out.write(transcription.to_rttm())

if __name__ == "__main__":

    # Testing 
    """
    with open("VanDam5min_transcript/BE05/Be05_021023a.cha") as f_in:
        transcript = f_in.read()
    Transcription(transcript)

    reader = Reader.from_dir('VanDam5min_transcript')
    reader.dump('out')
    """