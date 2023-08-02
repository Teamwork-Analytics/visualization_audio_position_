import os

import pandas as pd

from vad.webRTC import do_vad

# colors should be added if more participants are expected
COLORS = ("blue", "green", "red", "yellow", "white", "black")


def __testing():
    return


def get_color(a_filename: str, COLORS_list: list or tuple):
    for a_color in COLORS_list:
        if a_color in a_filename.lower():
            return a_color


def extract_vad(audio_folder_path: str):
    res_dict = {}
    for a_filename in os.listdir(audio_folder_path):
        if ".wav" not in a_filename:
            print("{} is not a audio file, skipped".format(os.path.join(audio_folder_path, a_filename)))
            continue

        path = os.path.join(audio_folder_path, a_filename)
        result = do_vad(path, 3)
        color = get_color(a_filename, COLORS)
        res_dict[color] = unpackaging_vad_res(result, color)
    return res_dict


def unpackaging_vad_res(vad_res: str, color: str) -> pd.DataFrame:
    if len(vad_res) == 0:
        return pd.DataFrame({"color": [], "start": [], "end": []})
    res_list = [interval_str.split(",") for interval_str in vad_res.split("|")]
    res_dict = {"color": [], "start": [], "end": []}
    for an_interval in res_list:
        res_dict["color"].append(color)
        res_dict["start"].append(float(an_interval[0]))
        res_dict["end"].append(float(an_interval[1]))
    return pd.DataFrame(res_dict)


if __name__ == '__main__':
    extract_vad("testing/testing_session_207/audio")
    print("")