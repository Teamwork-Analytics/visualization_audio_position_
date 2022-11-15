import os

import pydub
from audio_code import COLORS


def __mute_a_segment(a_segment, mute_before: float):
    muted_handover_segments = a_segment[0: mute_before * 1000] - 100
    processed_segment = muted_handover_segments + a_segment[mute_before * 1000:]
    return processed_segment


def preprocessing_audio_files(audio_files_folder: str, processed_output_folder, handover_finished_time: float,
                              secondary_enter_time: float,
                              doctor_enter_time: float):

    if not os.path.exists(processed_output_folder):
        os.mkdir(processed_output_folder)

    processed_audio = set()

    for a_audio_file in os.listdir(audio_files_folder):
        if not a_audio_file.startswith("sim_"):
            continue
        # preventing errors
        color = ""
        is_a_wanted_file = False

        for a_color in COLORS:
            if a_color.lower() in a_audio_file.lower():
                is_a_wanted_file = True
                color = a_color
                break

        if not is_a_wanted_file:
            continue
        if color in processed_audio:
            raise ValueError("audio file already processed")

        processed_audio.add(color)

        # load audio file
        an_audio = pydub.AudioSegment.from_wav(os.path.join(audio_files_folder, a_audio_file))

        # do processing
        if color == "blue" or color == "red" or color == "black":
            processed_segments = __mute_a_segment(an_audio, handover_finished_time)
        elif color == "green" or color == "yellow":
            processed_segments = __mute_a_segment(an_audio, secondary_enter_time)
        elif color == "white":
            processed_segments = __mute_a_segment(an_audio, doctor_enter_time)
        else:
            raise ValueError("unexpected color appeared, SHOULD NOT happened")
        processed_segments.export(os.path.join(processed_output_folder, color + ".wav"), format="wav")

if __name__ == '__main__':
    testing_dub = pydub.AudioSegment.from_wav("audio for testing.wav")
    processed = __mute_a_segment(testing_dub, 700)
    processed.export("output.wav", format="wav")
