from pathlib import Path


def get_wav_rttm_pairs(wav_dir: str, rttm_dir: str) -> list[tuple[str, str]]:
    """
    Given two directories, return pairs

    They should have the same directory structure, e.g.,
        `{wav_dir}/A/B.wav` and `{rttm_dir}/A/B.rttm` match but not `{wav_dir}/B.wav` and `{rttm_dir}/A/B.rttm`
    """
    wav_path = Path(wav_dir)
    rttm_path = Path(rttm_dir)

    if not wav_path.exists() or not rttm_path.exists():
        raise ValueError("wav_dir or rttm_dir doesn't exist")

    out = []
    for wav_filepath in wav_path.rglob("*.wav"):
        for rttm_filepath in rttm_path.rglob("*.rttm"):
            # for comparison
            temp = str(rttm_filepath).replace(".rttm", ".wav")
            temp = temp.replace(rttm_dir, wav_dir)

            if str(wav_filepath) != temp:
                continue
            out.append((str(wav_filepath), str(rttm_filepath)))
    return out
