from pyannote.core import Annotation, Segment
import regex as re
from pathlib import Path
from typing import Self
import json

from formatter import Formatter

TIMESTAMP_BRACE = "\x15"

re_has_speaker = re.compile(r"\*[A-Z]+:")
re_timestamp = re.compile(rf"{TIMESTAMP_BRACE}([0-9]+_[0-9]+){TIMESTAMP_BRACE}")


class Transcription:
    """Container for .cha with helper functions and data for ASR tasks"""

    def __init__(self, raw_transcription: str, formatter: Formatter = Formatter()):
        self.formatter = formatter
        self.speakers = set()
        self.annotation = Annotation()
        self.utterances = []
        self.duration = 0

        lines = raw_transcription.split("\n")
        for line in lines:
            self._parse_line(line)

    @classmethod
    def from_path(cls, filepath: str) -> Self:
        """
        Load transcription from a .cha file
        """
        f_in = open(filepath, "r")
        raw_text = f_in.read()
        f_in.close()
        return cls(raw_text)

    def _parse_line(self, line: str):
        """
        Internal util function for parsing line
        Only goes through @Participants line and any line with speaker format

        - Adds segments to annotation
        - Modifies speakers
        """
        if line.startswith("@Participants:"):
            line = line.removeprefix("@Participants:").strip()
            # TODO: Handle optional speaker matching here
        elif re_has_speaker.match(line):
            lines = line.split("\t")

            speaker = lines[0][1:-1]
            timestamp = re_timestamp.search(lines[1])
            utterance = re_timestamp.sub("", lines[1])
            # Only care if it has timestamps.
            if timestamp is None:
                return
            timestamp = timestamp.group(1)

            self.speakers.add(speaker)

            timestamps = timestamp.split("_")
            start = float(timestamps[0]) / 1_000
            end = float(timestamps[1]) / 1_000

            segment = Segment(start, end)

            utterance = self.formatter.format_line(utterance)

            self.utterances.append((speaker, segment, utterance))
            self.annotation[segment] = speaker

            self.duration = max(self.duration, end)

    def to_rttm(self) -> str:
        """
        Return rttm-formatted text to be written to file
        """
        return self.annotation.to_rttm()

    def to_manifest(
        self, audio_filepath: str, rttm_filepath: str, should_exist: bool = False
    ) -> dict:
        """
        Return list of dictionaries corresponding to a line of a manifest files used in
        NeMo-asr tasks to be written to a .jsonl file.
        """
        if should_exist:
            if not Path(audio_filepath).exists():
                raise ValueError(
                    f".wav file {audio_filepath} for to_manifest() must exist."
                )
            if not Path(rttm_filepath).exists():
                raise ValueError(
                    f".rttm file {rttm_filepath} for to_manifest() must exist"
                )
        """
            Format: 
                {'audio_filepath', 'text', 'offset', 'duration', 'num_speakers', 'rttm_filepath'}
        """
        return {
            "audio_filepath": str(audio_filepath),
            "text": "-",
            "offset": 0,
            "duration": int(self.duration),
            "num_speakers": len(self.speakers),
            "rttm_filepath": str(rttm_filepath),
        }


class Reader:
    """Reader class is used for loading a directory of .cha files to access"""

    def __init__(self, transcriptions: dict[str, Transcription]):
        if len(transcriptions) == 0:
            raise ValueError("Can't pass empty transcriptions to Reader")

        self.transcriptions = transcriptions

    @classmethod
    def from_dir(cls, dir: str):
        """
        Load a Reader from a recursive directory of .cha files.
        """
        transcriptions = {}
        for path in Path(dir).rglob("*.cha"):
            base_dir = Path(*path.parts[1:]).with_suffix("")
            transcription = Transcription.from_path(path)
            transcriptions[base_dir] = transcription
        return cls(transcriptions)

    def dump(
        self, rttm_dir: str, wav_dir: str, manifest_filepath: str, skip: bool = True
    ):
        """
        Dump transcriptions as a folder of .rttms and a manifest .jsonl file

        Assumes that directory of .wav files exists in 'wav_dir' that mirrors original structure of .cha files.
        """
        if not manifest_filepath.endswith(".jsonl"):
            raise ValueError("Manifest file should end with .jsonl")

        Path(manifest_filepath).parent.mkdir(parents=True, exist_ok=True)
        manifest_file = open(manifest_filepath, "w")

        for base_dir, transcription in self.transcriptions.items():
            audio_filepath = wav_dir / base_dir.with_suffix(".wav")

            if not Path.exists(audio_filepath):
                if skip:
                    continue
                raise ValueError(
                    f"Can't find audio file {audio_filepath} when saving generating .rttm and manifest files"
                )

            rttm_filepath = rttm_dir / base_dir.with_suffix(".rttm")
            rttm_filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(rttm_filepath, "w") as f_out:
                f_out.write(transcription.to_rttm())

            manifest = transcription.to_manifest(
                audio_filepath, rttm_filepath, should_exist=True
            )
            json.dump(manifest, manifest_file)
            manifest_file.write("\n")
        manifest_file.close()
