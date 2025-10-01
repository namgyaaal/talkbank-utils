# Talkbank Utils 

Python utility library for handling text and audio of Talkbank `.cha` files made for personal use. 

Used on ASR tasks (voice recognition, diarization and speech-to-text) for libraries such as `pyannote-audio` and `nemo_toolkit[asr]`. Because of this, it ignores a lot of other data included in .cha files. 

If you want those features, consider using other libraries (such as `pylangacq`).

# Example Usage

```python
from talkbank_utils.reader import Reader
from talkbank_utils.util import get_wav_rttm_pairs

from pyannote.audio import Pipeline
from pyannote.database.util import load_rttm
from pyannote.metrics.diarization import DiarizationErrorRate

der = DiarizationErrorRate()
pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-community-1")

reader = Reader.from_dir("transcription_directory")
reader.save_rttms("rttm_directory")

pairs = get_wav_rttm_pairs("audio_directory", "rttm_directory")
for (wav_filepath, rttm_filepath) in pairs: 
    hypothesis = pipeline(wav_filepath).exclusive_speaker_diarization
    true = list(load_rttm(rttm_filepath).values())[0]
    err = der(true, hypothesis)
    print(f"DER for {wav_filepath}: {err:.2f}")
```