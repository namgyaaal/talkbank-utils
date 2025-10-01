from pyannote.core import Annotation, Segment
import regex as re
from pathlib import Path
from typing import Self
import json

from .formatter import Formatter

TIMESTAMP_BRACE = "\x15"

re_has_speaker = re.compile(r"\*[A-Z]+:")
re_timestamp = re.compile(rf"{TIMESTAMP_BRACE}([0-9]+_[0-9]+){TIMESTAMP_BRACE}")


class Transcription:
    """Container for .cha with helper functions and data for ASR tasks"""

    def __init__(
        self, name: str, raw_transcription: str, formatter: Formatter = Formatter()
    ):
        self.formatter = formatter
        self.speakers = set()
        self.annotation = Annotation(uri=name)
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

        # Get basename since rttm needs it
        base = Path(filepath).parts[-1].removesuffix(".cha")

        return cls(base, raw_text)

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

    def to_manifest_entry(
        self, audio_filepath: str, rttm_filepath: str, should_exist: bool = False
    ) -> dict:
        """
        Return dictionary corresponding to a line of a manifest files used in
        NeMo-asr tasks to be written to a .jsonl file.

        :param audio_filepath: Path to the audio file for this transcription
        :param rttm_filepath: Path to the rttm file for this transcription
        :param should_exist: Throws an error if true and neither the audio or the rttm file exists.
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
            Format used for diarization: 
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
    def from_dir(cls, cha_dir: str):
        """
        Load a Reader from a recursive directory of .cha files.
        """
        transcriptions = {}
        for path in Path(cha_dir).rglob("*.cha"):
            base_dir = Path(*path.parts[1:]).with_suffix("")
            transcription = Transcription.from_path(path)
            transcriptions[base_dir] = transcription
        return cls(transcriptions)

    def save_rttms(self, rttm_dir: str):
        """
        Save .rttm files into the given directory.
        """
        for base_dir, transcription in self.transcriptions.items():
            rttm_filepath = rttm_dir / base_dir.with_suffix(".rttm")
            rttm_filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(rttm_filepath, "w") as f_out:
                f_out.write(transcription.to_rttm())

    def to_manifest(self, rttm_dir: str, wav_dir: str, skip=True) -> list[dict]:
        """
        Return a list of dictionaries representing the manifest file as used by NeMo

        :param rttm_dir: Directory of .rttm files, should exist
        :param wav_dir: Diectory of .wav files, should exist
        :param skip: Whether or not to skip a line of a .rttm of .wav file doesn't exist for it
        """
        out = []
        for base_dir, transcription in self.transcriptions.items():
            audio_filepath = wav_dir / base_dir.with_suffix(".wav")
            rttm_filepath = rttm_dir / base_dir.with_suffix(".rttm")

            try:
                manifest = transcription.to_manifest_entry(
                    audio_filepath, rttm_filepath, should_exist=True
                )
                out.append(manifest)
            except ValueError as e:
                if skip:
                    continue
                raise e

        return out

    def save_manifest(
        self, manifest_filepath: str, rttm_dir: str, wav_dir: str, skip: bool = True
    ):
        """
        Save manifest file into the given filepath. Should be called after save_rttms() and should point to its directory for `rttm_dir`

        :param manifest_filepath: Output directory for manifest file
        :param rttm_dir: Directory of .rttm files, should exist
        :param wav_dir: Directory of .wav files, should exist
        :param skip: Whether or not to skip a line if a .rttm or .wav file doesn't exist for it
        """
        if not manifest_filepath.endswith(".jsonl"):
            raise ValueError("Manifest file should end with .jsonl")

        manifest = self.to_manifest(rttm_dir, wav_dir, skip)

        Path(manifest_filepath).parent.mkdir(parents=True, exist_ok=True)
        manifest_file = open(manifest_filepath, "w")
        for manifest_entry in manifest:
            json.dump(manifest_entry, manifest_file)
            manifest_file.write("\n")
        manifest_file.close()
