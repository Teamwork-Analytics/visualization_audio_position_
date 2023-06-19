"""

"""
print("webrtc start ")
import json
import math
import os
import threading
import time

import pydub
import speech_recognition as sr
import webrtcvad

from tqdm.auto import tqdm

import vad.webRTC as wt

##########################################
temp_file_path = "path"


########################################

def do_vad_with_speech_to_text(path: str, strictness_level: int, word_threshold: int = 1, number_of_thread: int = 0):
    """
    generate time segment (start time, end time), of voice segments, with the help of CMU Sphinx
    :param path: the path to the audio file for VAD
    :param strictness_level:
    :param word_threshold:
    :param number_of_thread: 0 or 1 for not using multi-threading

    :return: str or list, depending on return_str
    """
    audio, sample_rate = wt.read_wave(path)

    # Here is using the webRTC VAD to detect the voice segments
    # It is the first step
    vad = webrtcvad.Vad(strictness_level)
    segment_window = 30  #

    frames = wt.frame_generator(segment_window, audio, sample_rate)
    frames = list(frames)
    segments = wt.vad_collector(sample_rate, segment_window, 300, vad, frames)

    for content in segments:
        for i in range(len(content)):
            content[i] = content[i] * segment_window / 1000
    # print(segments)

    # Start from here, adding the correction function with t2s toolkit
    # It will remove the segments that do not have transcription, which means it just a false positive of webRTC VAD
    segments = do_speech_to_text_on_segments(segments, path, word_threshold=word_threshold,
                                             number_of_thread=number_of_thread)

    # this one is to left a temporary json file to prevent error in later code
    with open("temporary_data/temp.json", "w") as fp:
        json.dump(segments, fp)

    # if not return_str:
    #     return segments

    str_segments = []
    for segment in segments:
        str_segments.append(str(segment[0]) + "," + str(segment[1]))
    return "|".join(str_segments)
    # todo: 把这个segment的time frame算出来
    # for i, segment in enumerate(segments):
    #     path = 'chunk-%002d.wav' % (i,)
    #     print(' Writing %s' % (path,))
    #     write_wave(path, segment, sample_rate)


class Speech_to_text_thread(threading.Thread):
    def __init__(self, threadID, name, audio_dub: pydub.AudioSegment, segment_list: list, output_list: list,
                 word_threshold: int):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.audio_dub = audio_dub
        self.segment_list = segment_list
        self.word_threshold = word_threshold
        self.output_list = output_list

    def run(self):
        print("thread_started: " + self.name)
        self.speech_to_text_threaded(self.segment_list, self.audio_dub, self.output_list, self.word_threshold)
        print("thread_finished: " + self.name)

    def speech_to_text_threaded(self, segments: list, audio_dub: pydub.AudioSegment, output_list: list, word_threshold: int):
        with tqdm(total=len(segments)) as pbar:
            for line in segments:
                start = int(float(line[0]) * 1000)
                end = int(float(line[1]) * 1000)

                # if end - start < 0.5:
                #     pbar.update(1)
                #     continue

                clip = audio_dub[start: end]
                clip.export(os.path.join(temp_file_path, "{}_{}.wav".format(start, end)), "wav")
                clip_path = os.path.join(temp_file_path, "{}_{}.wav".format(start, end))
                result = speech2text_CMU(clip_path)
                try:
                    os.remove(clip_path)
                except:
                    print("====================\n" + "error on removing temporary files" + "========\n")
                # 这个实际是有str就行，应该用split来确定有几个单词
                # if len(result) > 2:
                #     cleaned_segments.append(line)

                # this one
                if len(result.split(" ")) > word_threshold:
                    output_list.append(line)
                else:
                    output_list.append("")
                pbar.update(1)


def speech_to_text(segments: list, audio_dub: pydub.AudioSegment, output_list: list, word_threshold: int):
    with tqdm(total=len(segments)) as pbar:
        for line in segments:
            start = int(float(line[0]) * 1000)
            end = int(float(line[1]) * 1000)

            # if end - start < 0.5:
            #     pbar.update(1)
            #     continue

            clip = audio_dub[start: end]
            clip.export(os.path.join(temp_file_path, "{}_{}.wav".format(start, end)), "wav")
            clip_path = os.path.join(temp_file_path, "{}_{}.wav".format(start, end))
            result = speech2text_CMU(clip_path)
            try:
                os.remove(clip_path)
            except:
                print("====================\n" + "error on removing temporary files" + "========\n")
            # 这个实际是有str就行，应该用split来确定有几个单词
            # if len(result) > 2:
            #     cleaned_segments.append(line)

            # this one
            if len(result.split(" ")) > word_threshold:
                output_list.append(line)
            pbar.update(1)


def split_list(original_list: list, split_to: int):
    return [original_list[i: i + math.ceil(len(original_list) / split_to)] for i in
            range(0, len(original_list), math.ceil(len(original_list) / split_to))]


def split_list_evenly(original_list: list, split_to: int):
    splitted_list = [[] for _ in range(split_to)]
    for index, item in enumerate(original_list):
        splitted_list[index % split_to].append(item)
    return splitted_list


def assemble_splitted(spliited_list):
    assmbled_list = []
    len_list = len(spliited_list)
    total_length = 0
    for a_list in spliited_list:
        total_length += len(a_list)
    for index in range(total_length):
        assmbled_list.append(spliited_list[index % len_list][int(index / len_list)])
    return assmbled_list


def do_speech_to_text_on_segments(segments: list, audio_path: str, word_threshold: int = 1, number_of_thread: int = 0):
    """
    code that actually used the
    :param segments:
    :param audio_path:
    :param word_threshold:
    :return:
    """
    cleaned_segments = []

    # create the temporary folder for saving the temporary files.
    # It can be improved after rewrite the code of speechrecognition interface
    if not os.path.exists(temp_file_path):
        os.mkdir(temp_file_path)

    # load the original audio file, for clipping
    audio_file = pydub.AudioSegment.from_file(audio_path, "wav")
    if number_of_thread == 1 or number_of_thread == 0:
        speech_to_text(segments, audio_file, cleaned_segments, word_threshold)
    else:
        output_list = []
        for _ in range(number_of_thread):
            output_list.append([])
        splitted_segments = split_list_evenly(original_list=segments, split_to=number_of_thread)

        threads_list = []
        for index, sub_list in enumerate(splitted_segments):
            a_thread = Speech_to_text_thread(index, "speech2text thread {}".format(index), audio_file, sub_list,
                                             output_list[index], word_threshold)
            a_thread.start()
            threads_list.append(a_thread)

        for thread in threads_list:
            thread.join()
        output_segments = assemble_splitted(output_list)

        # the function used in the threading class is different
        # it does not simply ignore the segments with short transcription
        # it would add an empty string "" as placeholder due to the assemble algorithm
        # here we do the clean up for the ""
        cleaned_segments = []
        for a_line in output_segments:
            if a_line != "":
                cleaned_segments.append(a_line)


    # try:
    #     for file in os.listdir(temp_file_path):
    #         os.remove(os.path.join(temp_file_path, file))
    # except:
    #     print("====================\n" + "error on removing temporary files")

    return cleaned_segments


def clipping_audio(audio_path: str, audio_format: str, output_path: str, segments: list):
    """
    creating clips of audio to check if the alignment is correct.
    :param output_path:
    :param segments:
    :param audio_path:
    :param audio_format:
    :param json_path:
    :return:
    """
    audio_file = pydub.AudioSegment.from_file(audio_path, audio_format)

    for line in segments:
        start = int(float(line[0]) * 1000)
        end = int(float(line[1]) * 1000)
        clip = audio_file[start: end]
        clip.export(os.path.join(output_path, "{}_{}.wav".format(start, end)), "wav")


def speech2text_CMU(an_audio_path: str):
    r = sr.Recognizer()
    with sr.AudioFile(an_audio_path) as source:
        audio = r.record(source)  # read the entire audio file
    # now it needs to use a temporary wav files to do the recognition. If necessary, it would be rewrite to use binary files using wave library

    try:
        recognition_result = r.recognize_sphinx(audio)
        # print("Sphinx thinks you said:   " + recognition_result)
        return recognition_result
    except sr.UnknownValueError:
        return ""


def test_tqdm():
    with tqdm(total=1140) as pbar:
        for i in range(10):
            time.sleep(0.1)
            pbar.update(10)
    print("finished")


def testing_detection():
    # audio-sim = do_vad_with_speech_to_text("Rio/voice at beginning.wav", 3)
    res = do_vad_with_speech_to_text("Rio/3413 3415.wav", 3)
    print()


if __name__ == '__main__':
    # speech2text_CMU("Rio/voiced.wav")
    # speech2text_CMU("Rio/no voice.wav")
    # speech2text_CMU("Rio/small background noise, 25,40-25,45.wav")
    # speech2text_CMU("Rio/small background noise, 25,17-25,24.wav")
    # speech2text_CMU("Rio/voice at beginning.wav")
    # speech2text_CMU("Rio/voice at beginning.wav")
    # test_tqdm()

    testing_detection()
    # print(str(datetime.timedelta(seconds=100)))
