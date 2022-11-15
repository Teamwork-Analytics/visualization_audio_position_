"""
this part is to extract the segments of audio that have human voice,
by using a voice activity detection(VAD) system
"""

import collections
import contextlib
import datetime
import sys
import time
import wave
import os
import webrtcvad
import pandas


def read_wave(path):
    """Reads a .wav file.
    Takes the path, and returns (PCM audio data, sample rate).
    """
    with contextlib.closing(wave.open(path, 'rb')) as wf:
        num_channels = wf.getnchannels()
        assert num_channels == 1
        sample_width = wf.getsampwidth()
        assert sample_width == 2
        sample_rate = wf.getframerate()
        assert sample_rate in (8000, 16000, 32000, 48000)
        pcm_data = wf.readframes(wf.getnframes())
        return pcm_data, sample_rate


def write_wave(path, audio, sample_rate):
    """Writes a .wav file.
    Takes path, PCM audio data, and sample rate.
    """
    with contextlib.closing(wave.open(path, 'wb')) as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio)


class Frame(object):
    """Represents a "frame" of audio data."""

    def __init__(self, bytes, timestamp, duration):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration


def frame_generator(frame_duration_ms, audio, sample_rate):
    """Generates audio frames from PCM audio data.
    Takes the desired frame duration in milliseconds, the PCM data, and
    the sample rate.
    Yields Frames of the requested duration.
    """
    n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
    offset = 0
    timestamp = 0.0
    duration = (float(n) / sample_rate) / 2.0
    while offset + n < len(audio):
        yield Frame(audio[offset:offset + n], timestamp, duration)
        timestamp += duration
        offset += n


def vad_collector_old(sample_rate, frame_duration_ms,
                      padding_duration_ms, vad, frames, voiced_region_list):
    """Filters out non-voiced audio frames.
    Given a webrtcvad.Vad and a source of audio frames, yields only
    the voiced audio.
    Uses a padded, sliding window algorithm over the audio frames.
    When more than 90% of the frames in the window are voiced (as
    reported by the VAD), the collector triggers and begins yielding
    audio frames. Then the collector waits until 90% of the frames in
    the window are unvoiced to detrigger.
    注意这里，audio文件在开头和结尾都多了padding
    并不是↑，这个padding可以看做是由于队列window大小导致的多出来的一部分空音频
    The window is padded at the front and back to provide a small
    amount of silence or the beginnings/endings of speech around the
    voiced frames.
    Arguments:
    sample_rate - The audio sample rate, in Hz.
    frame_duration_ms - The frame duration in milliseconds.
    padding_duration_ms - The amount to pad the window, in milliseconds.修改这个和voiced百分比可以让trigger更容易出现，或者更难断掉
    vad - An instance of webrtcvad.Vad.
    frames - a source of audio frames (sequence or generator).
    Returns: A generator that yields PCM audio data.
    """
    num_padding_frames = int(padding_duration_ms / frame_duration_ms)
    # We use a deque for our sliding window/ring buffer.
    # 这个ring_buffer的最大长度意思是最多包含些数量的content，多的content会直接被挤掉
    #
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    # We have two states: TRIGGERED and NOTTRIGGERED. We start in the
    # NOTTRIGGERED state.
    triggered = False
    i = 0
    voiced_frames_id = []
    voiced_frames = []
    for frame in frames:
        is_speech = vad.is_speech(frame.bytes, sample_rate)
        # i = 42时会true一次
        sys.stdout.write('1' if is_speech else '0')
        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            # If we're NOTTRIGGERED and more than 90% of the frames in
            # the ring buffer are voiced frames, then enter the
            # TRIGGERED state.

            # 这里maxlen就是10,0.9 * 10 只能在10的时候大于9，改成>= 试试
            # todo: 把这里改成>=看看断开声音的情况多吗
            if num_voiced > 0.9 * ring_buffer.maxlen:  # 这里在num voice足够多时被trigger
                triggered = True
                voiced_frames_id.append(i - num_padding_frames)
                sys.stdout.write('+(%s)' % (ring_buffer[0][0].timestamp,))
                # We want to yield all the audio we see from now until
                # we are NOTTRIGGERED, but we have to start with the
                # audio that's already in the ring buffer.
                for f, s in ring_buffer:  # 也就是说voice以300ms为单位组合成一个voiced frame，并不对！
                    voiced_frames.append(f)
                ring_buffer.clear()
        else:
            # We're in the TRIGGERED state, so collect the audio data
            # and add it to the ring buffer.            # 也就是说voice以300ms为单位组合成一个voiced frame，并不对！voiced frame在trigger后就会一直记录小的frame
            voiced_frames.append(frame)
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            # If more than 90% of the frames in the ring buffer are
            # unvoiced, then enter NOTTRIGGERED and yield whatever
            # audio we've collected.
            if num_unvoiced > 0.9 * ring_buffer.maxlen:  # 然后一直到unvoice的片段多到占满一整个padding才结束
                sys.stdout.write('-(%s)' % (frame.timestamp + frame.duration))
                voiced_frames_id.append(i)
                voiced_region_list.append(voiced_frames_id)
                triggered = False
                yield b''.join([f.bytes for f in voiced_frames])
                ring_buffer.clear()
                voiced_frames = []
                voiced_frames_id = []

        i += 1

    if triggered:
        sys.stdout.write('-(%s)' % (frame.timestamp + frame.duration))
    sys.stdout.write('\n')
    # If we have any leftover voiced audio when we run out of input,
    # yield it.
    if voiced_frames:
        yield b''.join([f.bytes for f in voiced_frames])


#############################
# code above here is not meant to be used.
#
################################


def vad_collector(sample_rate, frame_duration_ms,
                  padding_duration_ms, vad, frames):
    """Filters out non-voiced audio frames.

    Arguments:
    sample_rate - The audio sample rate, in Hz.
    frame_duration_ms - The frame duration in milliseconds.
    padding_duration_ms - The amount to pad the window, in milliseconds.修改这个和voiced百分比可以让trigger更容易出现，或者更难断掉
    vad - An instance of webrtcvad.Vad.
    frames - a source of audio frames (sequence or generator).
    Returns: A generator that yields PCM audio data.
    """
    num_padding_frames = int(padding_duration_ms / frame_duration_ms)
    # We use a deque for our sliding window/ring buffer.
    #
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    # We have two states: TRIGGERED and NOTTRIGGERED. We start in the
    # NOTTRIGGERED state.
    triggered = False
    i = 0
    voiced_frames_id = []
    voiced_region_list = []
    voiced_frames = []
    for frame in frames:
        is_speech = vad.is_speech(frame.bytes, sample_rate)

        # sys.stdout.write('1' if is_speech else '0')
        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            # If we're NOTTRIGGERED and more than 90% of the frames in
            # the ring buffer are voiced frames, then enter the
            # TRIGGERED state.

            # here maxlen is 10,
            # changed from > to >=
            # when num voice is enough, go into trigger, start counting as voiced
            if num_voiced >= 0.9 * ring_buffer.maxlen:
                triggered = True
                voiced_frames_id.append(i - num_padding_frames)
                # sys.stdout.write('+(%s)' % (ring_buffer[0][0].timestamp,))
                # We want to yield all the audio we see from now until
                # we are NOTTRIGGERED, but we have to start with the
                # audio that's already in the ring buffer.
                for f, s in ring_buffer:
                    voiced_frames.append(f)
                ring_buffer.clear()
        else:
            # We're in the TRIGGERED state, so collect the audio data
            # and add it to the ring buffer.           voiced frame will record little frames after being triggered
            voiced_frames.append(frame)
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            # If more than 90% of the frames in the ring buffer are
            # unvoiced, then enter NOTTRIGGERED and yield whatever
            # audio we've collected.
            # changed to >=? No
            if num_unvoiced > 0.9 * ring_buffer.maxlen:  # 然后一直到unvoice的片段多到占满一整个padding才结束
                # sys.stdout.write('-(%s)' % (frame.timestamp + frame.duration))
                # this part is changed from i to i - num_padding_frames to remove the empty frames
                voiced_frames_id.append(i - num_padding_frames)
                voiced_region_list.append(voiced_frames_id)
                triggered = False
                ring_buffer.clear()
                voiced_frames = []
                voiced_frames_id = []

        i += 1

    # if triggered:
    # sys.stdout.write('-(%s)' % (frame.timestamp + frame.duration))
    # sys.stdout.write('\n')
    # If we have any leftover voiced audio when we run out of input,
    # yield it.
    if voiced_frames:
        voiced_frames_id.append(i)
        voiced_region_list.append(voiced_frames_id)
        voiced_frames_id = []
    return voiced_region_list


def main(args):
    if len(args) != 2:
        sys.stderr.write(
            'Usage: example.py <aggressiveness> <path to wav file>\n')
        sys.exit(1)
    audio, sample_rate = read_wave(args[1])
    vad = webrtcvad.Vad(int(args[0]))
    frames = frame_generator(30, audio, sample_rate)
    frames = list(frames)
    segments = vad_collector(sample_rate, 30, 300, vad, frames)
    # for i, segment in enumerate(segments):
    #     path = 'chunk-%002d.wav' % (i,)
    #     print(' Writing %s' % (path,))
    #     write_wave(path, segment, sample_rate)


def do_vad(path: str, strictness_level: int):
    """
    generate time segment, of voice segments
    :param path:
    :param strictness_level:
    :return:
    """
    audio, sample_rate = read_wave(path)
    vad = webrtcvad.Vad(strictness_level)
    segment_window = 30  #

    frames = frame_generator(segment_window, audio, sample_rate)
    frames = list(frames)
    regions = vad_collector(sample_rate, segment_window, 300, vad, frames)
    for content in regions:
        for i in range(len(content)):
            content[i] = content[i] * segment_window / 1000
    # print(regions)
    str_regions = []
    for region in regions:
        str_regions.append(str(region[0]) + "," + str(region[1]))
    return "|".join(str_regions)
    # todo: 把这个segment的time frame算出来
    # for i, segment in enumerate(segments):
    #     path = 'chunk-%002d.wav' % (i,)
    #     print(' Writing %s' % (path,))
    #     write_wave(path, segment, sample_rate)


def do_vad_with_speech_to(path: str, strictness_level: int):
    """
    generate time segment, of voice segments
    :param path:
    :param strictness_level:
    :return:
    """
    audio, sample_rate = read_wave(path)
    vad = webrtcvad.Vad(strictness_level)
    segment_window = 30  #

    frames = frame_generator(segment_window, audio, sample_rate)
    frames = list(frames)
    regions = vad_collector(sample_rate, segment_window, 300, vad, frames)
    for content in regions:
        for i in range(len(content)):
            content[i] = content[i] * segment_window / 1000
    # print(regions)
    str_regions = []
    for region in regions:
        str_regions.append(str(region[0]) + "," + str(region[1]))
    return "|".join(str_regions)
    # todo: 把这个segment的time frame算出来
    # for i, segment in enumerate(segments):
    #     path = 'chunk-%002d.wav' % (i,)
    #     print(' Writing %s' % (path,))
    #     write_wave(path, segment, sample_rate)


def generating_region_files(path: str):
    """
    generate wav files, but not in use
    :param path:
    :return:
    """
    a_dict = {}
    a_dict["id"] = path.split("/")[-2]
    for file_path in os.listdir(path):
        if "GREEN" in file_path:
            a_dict["green"] = do_vad(path + file_path, 3)
        elif "RED" in file_path:
            a_dict["red"] = do_vad(path + file_path, 3)
        elif "BLUE" in file_path:
            a_dict["blue"] = do_vad(path + file_path, 3)
        elif "YELLOW" in file_path:
            a_dict["yellow"] = do_vad(path + file_path, 3)
    return a_dict


def experiment_VAD_on_bad_case():
    """
    merely for testing
    holding several lines of testing code
    :return:
    """
    # print("180 up")
    # do_vad("data/180 blue power up.wav", 3)
    # print("180 no power up")
    # do_vad("data/180 blue no empowered .wav", 3)
    # print("195 power up")
    # do_vad("data/195 blue power up.wav", 3)
    # print("195 no power up")
    # do_vad("data/195 blue no power up.wav", 3)
    # print(do_vad("data/216/simulation_GREEN_01-Sep-2021_13-19-37-929_audio.wav", 3))
    # print(do_vad("data/216 full for test2.wav", 3))
    print(do_vad("data/173 t.wav", 3))


def extract(session_id: int):
    """not in use"""
    frame = generating_region_files("data/{}/".format(session_id))
    df = pandas.DataFrame(frame, index=[1])
    used_df = df[["blue", "green", "red", "yellow"]]
    used_df.to_csv("buffer.csv")
    print(frame)
    print()


def bulk_extract(path: str, level: int = 3) -> object:
    """
    extract voice segments into separated files, and save into a single dict variable.
    :param path:
    :param level: level of strictness, value from 0 to 3, 3 is the most strict level.
    :return:
    """
    folders = os.listdir(path)
    a_dict = {}
    a_dict["id"] = []
    a_dict["region_blue"] = []
    a_dict["region_green"] = []
    a_dict["region_red"] = []
    a_dict["region_yellow"] = []
    a_dict["start_timestamp"] = []

    for folder in folders:
        folder_path = os.path.join(path, folder)
        a_dict["id"].append(folder)
        for file in os.listdir(folder_path):

            if "BLUE" in file:
                elements = file.split("_")
                time_string = elements[2] + "-" + elements[3]
                date = datetime.datetime.strptime(
                    time_string, "%d-%b-%Y-%H-%M-%S-%f")
                timestamp = datetime.datetime.timestamp(date)
                a_dict["start_timestamp"].append(timestamp)

            file_path = os.path.join(folder_path, file)
            if "GREEN" in file_path:
                a_dict["region_green"].append(do_vad(file_path, level))
            elif "RED" in file_path:
                a_dict["region_red"].append(do_vad(file_path, level))
            elif "BLUE" in file_path:
                a_dict["region_blue"].append(do_vad(file_path, level))
            elif "YELLOW" in file_path:
                a_dict["region_yellow"].append(do_vad(file_path, level))

    return a_dict


def extract_audio_segment_csv(data_folder_path: str, output_path: str):
    another_dict = bulk_extract(data_folder_path, level=3)
    df = pandas.DataFrame(another_dict)
    df.to_csv(output_path)


def loading_segment_results_to_array(csv_path: str):
    """
    loading the csv to array object
    the structure is [{id: int, blue: array, green: array, red: array, yellow: array},{},...]
    the array inside a dict, named by color, like blue, contains time segments like (start, end)
    :param csv_path:
    :return:
    """
    color = ["region_blue", "region_green", "region_red", "region_yellow"]
    df = pandas.read_csv(csv_path)

    the_array = []
    for i, line in df.iterrows():
        a_dict = {}
        a_dict["id"] = line["id"]
        a_dict["start_timestamp"] = line["start_timestamp"]
        for a_color in color:
            a_dict[a_color.split("_")[1]] = []
            for a_segment in line[a_color].split("|"):
                str_segment = a_segment.split(",")
                a_dict[a_color.split("_")[1]].append(
                    (float(str_segment[0]), float(str_segment[1])))
        the_array.append(a_dict)

    return the_array


def get_timestamp(path: str):
    """把文件名上的时间信息转化成timestamp"""
    a_dict = {}
    a_dict["start_time_stamp"] = []
    folders = os.listdir(path)
    a_dict["id"] = []

    for folder in folders:
        folder_path = os.path.join(path, folder)

        a_dict["id"].append(folder)
        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            if "BLUE" in file_path:
                elements = file_path.split("_")
                time_string = elements[2] + "-" + elements[3]
                date = datetime.datetime.strptime(
                    time_string, "%d-%b-%Y-%H-%M-%S-%f")
                timestamp = datetime.datetime.timestamp(date)
                a_dict["start_time_stamp"].append(timestamp)
    return a_dict


if __name__ == '__main__':
    start = time.time()

    # print(do_vad("Rio/Session6  - Tracker 26656 T1 - 180418_1359.wav", 3))

    # code for extraction
    # extract_audio_segment_csv("data", "results_for_all_2021_10_22.csv")

    # code for loading csv as array
    # result = loading_segment_results_to_array()
    print(time.time() - start)
