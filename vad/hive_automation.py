"""
@author Linxuan Zhao <linxuan.zhao@monash.edu>
"""
import vad.webRTC_with_speech2text
import vad.webRTC
from sklearn.metrics import confusion_matrix
from sklearn.metrics import accuracy_score
import pydub
import pandas as pd
import numpy
import sys
import getopt
import datetime
print("start")


def locate_missed_time_with_labels(csv_path: str):
    """
    there are some missed timestamp in "audio time" column, this function is
    going through data file to find out the missed timestamp in "audio time" columns
    :param csv_path: the path to the data.csv
    :return:
    """
    a_df = pd.read_csv(csv_path)
    audio_time = a_df["audio time"]
    i = 901
    for time_string in a_df["audio time"]:
        date = datetime.datetime.strptime(time_string, "%H:%M:%S")

        seconds = datetime.timedelta(
            hours=date.hour, minutes=date.minute, seconds=date.second).total_seconds()
        if i != seconds:
            print(seconds)
            i = seconds
        i += 1

    print(a_df["audio time"].dtypes)

    return a_df


def time_string_to_seconds(time_string: str):
    """
    converting the time string in csv file to seconds
    :param time_string: the time string, in format "hours:minutes:seconds", like "0:24:22"
    :return:
    """
    date = datetime.datetime.strptime(time_string, "%H:%M:%S")
    seconds = datetime.timedelta(
        hours=date.hour, minutes=date.minute, seconds=date.second).total_seconds()
    return seconds


def get_voiced_time(start: float, end: float):
    """
    here I considered three types of methods mapping the time segment, like (1.22, 3.22),
    to specific time stamp in "audio time" column
    1. int(start), ceil(end)
    2. ceil(start), int(end) currently using this one
    3. round(start), round(end)
    :param start: start time of a segment, which is the first float in a segment
    :param end: end time of a segment
    :return: a list containing the time string that should be marked as 1, in the same format in the data.csv.
    """

    # a_range = range(int(start), ceil(end) + 1)
    # a_range = range(ceil(start), round(end) + 1)
    a_range = range(round(start), round(end) + 1)

    an_array = []
    for a_time in a_range:
        an_array.append(str(datetime.timedelta(seconds=a_time)))
    return an_array


def calculate_performance(result_df: pd.DataFrame):
    """
    calculate the performance of algorithm, using the output csv of "testing_with_labels()"
    it will show the accuracy, confusion matrix, recall and precision.
    :param result_df: the output csv of "testing_with_labels()"
    :return: None
    """
    result_df = result_df.dropna()
    truth = numpy.array(result_df["audio"])
    pred = numpy.array(result_df["vad_result"])
    accuracy = accuracy_score(truth, pred)
    tn, fp, fn, tp = confusion_matrix(truth, pred).ravel()
    confusion_matrix(truth, pred)
    print("==========================================")
    print("accuracy: {}".format(accuracy))
    print("         , t is 1, t is 0")
    print("pred as 1, tp: {}, fp: {}".format(tp, fp))
    print("pred as 0, fn: {}, tn: {}".format(fn, tn))
    print()
    print("recall: {}, precision: {}".format(tp / (tp + fp), tp / (tp + fn)))
    print("==========================================")


def testing_with_labels(audio_path: str, csv_path: str, output_path: str, strictness_level: int = 3, word_threshold: int = 1, number_of_thread: int = 0):
    """
    This function is testing the performance of vad using the manually coded data
    It will generate a new csv file containing the "session", "audio time", "audio" columns in data.csv file.
    and a new column "vad_result" containing the result labeled by the vad algorithm

    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    ! DO remember that the audio file should be wav file, with frequency of 8000, 16000, or 32000 Hz
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    :param audio_path: The path to audio file for VAD
    :param csv_path: the path to data.csv
    :param output_path: output path of the result csv
    :param strictness_level: the strictness level of WebRTC VAD, it should be 1, 2, or 3. Left it 3 is fine
    :param word_threshold: this threshold for setting how many words should a transcription of
     a voice segment contains to pass the check. It is set due to some background voice sometimes can be transcribed
      to one or two words. This threshold is to throw away this type of false positive.
      Increasing this value may lead to the increasing of recall and decreasing of precision.
    :return: the result DataFrame
    """
    # todo 加上一段代码，把比较短的部分去掉 audio部分去掉
    a_df = pd.read_csv(csv_path)
    # extracting the columns from coded data
    a_df: pd.DataFrame = a_df[["session", "audio time", "audio"]]
    a_df["vad_result"] = 0  # initialize the new column with 0
    first_audio_time = time_string_to_seconds(
        a_df["audio time"].iloc[0])  # record the second of the first line
    result_string = vad.webRTC_with_speech2text.do_vad_with_speech_to_text(
        audio_path, strictness_level=strictness_level, word_threshold=word_threshold, number_of_thread=number_of_thread)
    if not len(result_string) == 0:
        for a_segment in result_string.split("|"):
            splitted = a_segment.split(",")
            start = float(splitted[0])
            end = float(splitted[1])

            # remove the small segments
            if end - start < 0.5:
                continue

            # the audio data for testing starts from 15:01,
            # so it needs to the time in the first line of "audio time" column
            time_array = get_voiced_time(
                start + first_audio_time, end + first_audio_time)
            for a_time in time_array:
                the_line = a_df[a_df["audio time"] == a_time]

                # for detecting if there is two line in "audio time column" shares the same time string
                if len(the_line) > 1:
                    print("two line with the same value!")
                    print(a_df["audio time"])
                # find the line that should be set to 1
                if len(the_line) != 0:
                    row = the_line.index.values.astype(int)[0]
                    a_df.iloc[row, a_df.columns.get_loc("vad_result")] = 1
            # for
    #
    # for time_string in a_df["audio time"]:
    #     a_second = time_string_to_seconds(time_string)

    print(a_df["audio time"].dtypes)
    # generate a csv file of result
    a_df.to_csv(output_path)
    return a_df


def create_result_dataframe(audio_path: str, session_name: str):
    time_list = []
    audio = pydub.AudioSegment.from_wav(audio_path)
    print(audio.duration_seconds)
    for i in range(int(audio.duration_seconds) + 1):
        time_list.append(str(datetime.timedelta(seconds=i)))
    a_df = pd.DataFrame({"audio time": time_list})
    a_df["session"] = session_name
    a_df["audio"] = 0
    a_df = a_df[["session", "audio time", "audio"]]

    return a_df


def vad_on_unlabelled_data_without_speech2text(audio_path: str, output_path: str, session_name: str, strictness_level: int = 3):
    """
    This function is doing the VAD on unlabelled audio data.
    It will generate a new csv file containing the "session", "audio time", "audio" columns
    in data.csv file.

    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    ! DO remember that the audio file should be wav file, with frequency of 8000, 16000, or 32000 Hz
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    :param audio_path: The path to audio file for VAD
    :param csv_path: the path to csv files containing the data awaiting VAD
    :param output_path: output path of the result csv
    :param strictness_level: the strictness level of WebRTC VAD, it should be 1, 2, or 3. Left it 3 is fine
    :param word_threshold: this threshold for setting how many words should a transcription of
     a voice segment contains to pass the check. It is set due to some background voice sometimes can be transcribed
      to one or two words. This threshold is to throw away this type of false positive.
      Increasing this value may lead to the increasing of recall and decreasing of precision.
    :param number_of_thread: number of thread for accelerate the computing time. 0 or 1 for not using multi-threading
    :return: the result DataFrame
    """
    # the result dataframe contains three columns called
    # "session", "audio time", "audio", containing the session name,
    # timestamp in the audio(in %H:%M:%S format),
    # and the if the teacher spoke something(1 for teacher spoke something, 0 for not)
    a_df = create_result_dataframe(audio_path, session_name)
    result_string = vad.webRTC.do_vad(
        audio_path, strictness_level=strictness_level)

    if not len(result_string) == 0:
        # decode the return of the result
        for a_segment in result_string.split("|"):
            splitted = a_segment.split(",")
            start = float(splitted[0])
            end = float(splitted[1])

            # remove the small segments
            if end - start < 0.5:
                continue

            # the audio data for testing starts from 15:01,
            # so it needs to the time in the first line of "audio time" column
            time_array = get_voiced_time(start, end)
            for a_time in time_array:
                the_line = a_df[a_df["audio time"] == a_time]

                # find the line that should be set to 1
                if len(the_line) != 0:
                    row = the_line.index.values.astype(int)[0]
                    a_df.iloc[row, a_df.columns.get_loc("audio")] = 1

    print(a_df["audio time"].dtypes)
    # generate a csv file of result
    a_df.to_csv(output_path)
    return a_df



def vad_on_unlabelled_data(audio_path: str, output_path: str, session_name: str, strictness_level: int = 3, word_threshold: int = 1, number_of_thread: int = 0):
    """
    This function is doing the VAD on unlabelled audio data.
    It will generate a new csv file containing the "session", "audio time", "audio" columns
    in data.csv file.

    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    ! DO remember that the audio file should be wav file, with frequency of 8000, 16000, or 32000 Hz
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    :param audio_path: The path to audio file for VAD
    :param csv_path: the path to csv files containing the data awaiting VAD
    :param output_path: output path of the result csv
    :param strictness_level: the strictness level of WebRTC VAD, it should be 1, 2, or 3. Left it 3 is fine
    :param word_threshold: this threshold for setting how many words should a transcription of
     a voice segment contains to pass the check. It is set due to some background voice sometimes can be transcribed
      to one or two words. This threshold is to throw away this type of false positive.
      Increasing this value may lead to the increasing of recall and decreasing of precision.
    :param number_of_thread: number of thread for accelerate the computing time. 0 or 1 for not using multi-threading
    :return: the result DataFrame
    """
    # the result dataframe contains three columns called
    # "session", "audio time", "audio", containing the session name,
    # timestamp in the audio(in %H:%M:%S format),
    # and the if the teacher spoke something(1 for teacher spoke something, 0 for not)
    a_df = create_result_dataframe(audio_path, session_name)
    result_string = vad.webRTC_with_speech2text.do_vad_with_speech_to_text(
        audio_path, strictness_level=strictness_level, word_threshold=word_threshold, number_of_thread=number_of_thread)

    if not len(result_string) == 0:
        # decode the return of the result
        for a_segment in result_string.split("|"):
            splitted = a_segment.split(",")
            start = float(splitted[0])
            end = float(splitted[1])

            # remove the small segments
            if end - start < 0.5:
                continue

            # the audio data for testing starts from 15:01,
            # so it needs to the time in the first line of "audio time" column
            time_array = get_voiced_time(start, end)
            for a_time in time_array:
                the_line = a_df[a_df["audio time"] == a_time]

                # find the line that should be set to 1
                if len(the_line) != 0:
                    row = the_line.index.values.astype(int)[0]
                    a_df.iloc[row, a_df.columns.get_loc("audio")] = 1

    print(a_df["audio time"].dtypes)
    # generate a csv file of result
    a_df.to_csv(output_path)
    return a_df


def evaluation(csv_path: str, sub_csvs=None):
    """
    load the result csv, and also merge the vad_result column of other result csvs
    for easy comparison
    :param csv_path: result csv file generated by testing_with_labels()
    :param sub_csvs: result csv file generated by testing_with_labels() that you would like to show the vad_result column together
    :return: merged DataFrame
    """
    if sub_csvs is None:
        sub_csvs = []
    df = pd.read_csv(csv_path)
    calculate_performance(df)
    for i, path in enumerate(sub_csvs):
        df["vad result of " + str(i)] = pd.read_csv(path)["vad_result"]

    return df


def evaluation_label_result(label_result_csv_path: str, manual_label_path: str, output_path: str):
    """
    load the result csv, and also merge the vad_result column of other result csvs
    for easy comparison
    :param csv_path: result csv file generated by testing_with_labels()
    :param sub_csvs: result csv file generated by testing_with_labels() that you would like to show the vad_result column together
    :return: merged DataFrame
    """
    label_df = pd.read_csv(label_result_csv_path)
    manual_df = pd.read_csv(manual_label_path)
    result_df = manual_df[["session", "audio time", "audio"]]
    result_df["vad_result"] = 0
    label_as_1_df = label_df.loc[label_df['audio'] == 1]
    for index, line in label_as_1_df.iterrows():
        time = line["audio time"]
        the_line = result_df[result_df["audio time"] == time]

        # find the line that should be set to 1
        if len(the_line) != 0:
            row = the_line.index.values.astype(int)[0]
            result_df.iloc[row, result_df.columns.get_loc("vad_result")] = 1

    calculate_performance(result_df)
    return result_df


def labeling_with_manual_data(label_result_csv_path: str, manual_label_path: str, output_path: str):
    """
    load the result csv, and also merge the vad_result column of other result csvs
    for easy comparison
    :param csv_path: result csv file generated by testing_with_labels()
    :param sub_csvs: result csv file generated by testing_with_labels() that you would like to show the vad_result column together
    :return: merged DataFrame
    """
    label_df = pd.read_csv(label_result_csv_path)
    manual_df = pd.read_csv(manual_label_path)
    result_df = manual_df.copy()
    label_as_1_df = label_df.loc[label_df['audio'] == 1]
    for index, line in label_as_1_df.iterrows():
        time = line["audio time"]
        the_line = result_df[result_df["audio time"] == time]

        # find the line that should be set to 1
        if len(the_line) != 0:
            row = the_line.index.values.astype(int)[0]
            result_df.iloc[row, result_df.columns.get_loc("audio")] = 1
    result_df.to_csv(output_path)
    return result_df


def testing_small_audios():
    # just a testing, ignore it
    output_path = "Rio/results/3413"
    result = testing_with_labels(
        "Rio/3413 3415- larger.wav", "Rio/cleaned-data/data.csv", output_path)
    return

"""
def main(argv):
    audio_path = ""
    output_path = ""
    session_name = ""
    strictness_level = 3
    word_threshold = 1
    number_of_thread: int = 0

    opts, args = getopt.getopt(argv, "a:o:s:w:t:",
                               ["audio_path=", "output_path=", "session_name=", "word_thres=", "thread_number="])
    for opt, arg in opts:
        if opt in ("-a", "--audio_path"):
            audio_path = str(arg)
        elif opt in ("-o", "--output_path"):
            output_path = str(arg)
        elif opt in ("-s", "--session_name"):
            session_name = str(arg)
        elif opt in ("-w", "--word_thres"):
            word_threshold = int(arg)
        elif opt in ("-t", "--thread_number"):
            number_of_thread = int(arg)

    if audio_path == "" or output_path == "" or session_name == "":
        print("audio_path and output_path and session_name must have input value")
        return
    print(" before vad")
    vad_on_unlabelled_data(audio_path=audio_path, output_path=output_path, session_name=session_name,
                           word_threshold=word_threshold, number_of_thread=number_of_thread)
    # hive_automation.py -a "Rio/small background noise, 25,17-25,24.wav" -o console_output.csv -s test1 -w 1 -t 3
    return
"""

def hive_main(audio_path, output_path, session_name, word_threshold, number_of_thread):
    # audio_path = ""
    # output_path = ""
    # session_name = ""
    # strictness_level = 3
    # word_threshold = 1
    # number_of_thread: int = 0
    #
    # opts, args = getopt.getopt(argv, "a:o:s:w:t:",
    #                            ["audio_path=", "output_path=", "session_name=", "word_thres=", "thread_number="])
    # for opt, arg in opts:
    #     if opt in ("-a", "--audio_path"):
    #         audio_path = str(arg)
    #     elif opt in ("-o", "--output_path"):
    #         output_path = str(arg)
    #     elif opt in ("-s", "--session_name"):
    #         session_name = str(arg)
    #     elif opt in ("-w", "--word_thres"):
    #         word_threshold = int(arg)
    #     elif opt in ("-t", "--thread_number"):
    #         number_of_thread = int(arg)

    if audio_path == "" or output_path == "" or session_name == "":
        print("audio_path and output_path and session_name must have input value")
        return
    print(" before vad")

    # # removed speech to text improvement
    # vad_on_unlabelled_data(audio_path=audio_path, output_path=output_path, session_name=session_name,
    #                        word_threshold=word_threshold, number_of_thread=number_of_thread)
    # new function
    vad_on_unlabelled_data_without_speech2text(audio_path=audio_path, output_path=output_path, session_name=session_name)

    # hive_automation.py -a "Rio/small background noise, 25,17-25,24.wav" -o console_output.csv -s test1 -w 1 -t 3
    return


if __name__ == '__main__':
    # testing_small_audios()

    ################# code for testing with labelled data ############################
    # output_path = "Rio/result_original_with_speech2text.csv"

    # output_csv_path = "Rio/demo_result.csv"

    # # output_path = "Rio/result_df_remove_small_highpass 400 48.csv"
    #

    # df = testing_with_labels("Rio/voice at beginning.wav", "Rio/cleaned-data/data.csv",
    #                          output_csv_path)

    # print(get_voiced_time(23.4, 27.1))

    ############## testing with labeled data with manual data ###############
    # out_path = "Rio/cleaned-data/vad/{}-vad.csv"
    # vad_path = "Rio/results/{} - focus recall.csv"
    # manual_path = "Rio/cleaned-data/{}.csv"
    # filenames = ["session6", "session7", "session8", "session10", "session11", "session12"]
    # # df = evaluation_label_result("Rio/results/session6.csv", "Rio/manual/manual_session6.csv",
    # #                              "Rio/results/session6-eva.csv")
    # for name in filenames:
    #     labeling_with_manual_data(vad_path.format(name), manual_path.format(name), out_path.format(name))
    ############## using VAD label to replace manual labeled data ###########

    ############## testing multi-threading: #################
    # session_path = "Rio/Session10 - multithread testing.wav"
    # output_csv_path = "Rio/mt_result3-new.csv"
    #
    # word_threshold = 2
    # testing_with_labels(session_path, "Rio/cleaned-data/data.csv", output_csv_path,
    #                     word_threshold=word_threshold, number_of_thread=4)
    #
    # eva_df = evaluation(output_csv_path, ["Rio/a_df.csv"])

    ################  code for labelling data ##################################
    # session_name = "session6"
    # session_path = "Rio/Session6 - full.wav"
    # word_threshold = 2
    # if word_threshold == 2:
    #     vad_on_unlabelled_data(session_path, "Rio/results/{} - focus recall.csv".format(session_name), session_name,
    #                            word_threshold=word_threshold, number_of_thread=3)
    # elif word_threshold == 1:
    #     vad_on_unlabelled_data(session_path, "Rio/results/{}.csv".format(session_name), session_name,
    #                            word_threshold=word_threshold, number_of_thread=3)

    ############ handle parameters ###########
    print("here")
    # main(sys.argv[1:])
