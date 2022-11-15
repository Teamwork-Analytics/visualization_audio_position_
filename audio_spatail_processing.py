import operator
import os.path

import pandas as pd
import portion

from audio_code import COLORS
from audio_code import extract_vad
from decorators import timer
from location_code import ID_TO_COLOR
from location_code import extract_interpolated_pozyx_with_yaw
from location_code import extract_loction_dict

# a threshold value to determine how close another response should be to count as responded speech.
RESPONDED_THRESHOLD = 5


def extract_location_with_interval(spatial_dict: dict, audio_interval: tuple):
    """

    :param spatial_dict: the dict for each student recording their spatial information
    :param audio_interval: audio interval, (start, end), in a tuple
    :return:
    """


def formatting_spatial_data(big_spatial_dict: dict):
    new_spatial_data = {}
    for a_key in big_spatial_dict:
        new_inner_dict = {}
        for a_location in big_spatial_dict[a_key]:
            interval_list = portion.empty()
            for an_interval in big_spatial_dict[a_key][a_location]:
                interval_list |= portion.closed(*an_interval)
            new_inner_dict[a_location] = interval_list
        new_spatial_data[ID_TO_COLOR[str(a_key)]] = new_inner_dict
    return new_spatial_data


def _determine_responded(main_start, main_end, ano_start, ano_end):
    """
    given two intervals of voice activity, detect whether later one responded the first one
    :param main_start:
    :param main_end:
    :param ano_start:
    :param ano_end:
    :return:
    """
    ano_interval = portion.closed(ano_start, ano_end)
    main_interval = portion.closed(main_start, main_end)

    # 改成只要overlap就可以，因为用这种方法的话，回话几乎全是给outsider
    # first situation, two interval overlaps, and ano start later than main
    # if ano_interval.overlaps(main_interval) and ano_start > main_start:
    #     return True
    #
    # # second situation, two interval not overlap, ano start few seconds after the first end
    # elif 0 < ano_start - main_end < RESPONDED_THRESHOLD:
    #     return True

    if ano_interval.overlaps(main_interval):
        return True
    elif 0 < ano_start - main_end < RESPONDED_THRESHOLD or 0 < main_start - ano_end < RESPONDED_THRESHOLD:
        return True
    return False


@timer
def responded_detection(audio_spatial_dict: dict):
    """
    This one use the responded speech as foundation to determine who a student is talking to.
    WARNING: The efficiency of this algorithm can be improved. Current version just uses brutal iteration
        to find a respond from others
    :param audio_spatial_dict:
    :return:
    """

    for a_color in COLORS:
        # adding a column to hold the utterance target
        audio_spatial_dict[a_color]["target"] = ""
        main_df = audio_spatial_dict[a_color]

        for i, row in main_df.iterrows():
            # select the start and end time of an utterance
            main_start = row['start']
            main_end = row['end']
            main_location = row["location"]
            main_interval = portion.closed(main_start, main_end)

            respond_list = []  # hold colors that responded the main color
            for another_color in COLORS:
                if another_color != a_color:
                    ano_df = audio_spatial_dict[another_color]

                    responded = False
                    for j, ano_row in ano_df.iterrows():
                        # if the two students are not in the same place, skip this one
                        if main_location != ano_row["location"]:
                            continue
                        ano_start = ano_row['start']
                        ano_end = ano_row['end']
                        responded = _determine_responded(main_start=main_start, main_end=main_end, ano_start=ano_start,
                                                         ano_end=ano_end)
                        if responded:
                            break
                        # ano_start = ano_row['start']
                        # ano_end = ano_row['end']
                        # ano_interval = portion.closed(ano_start, ano_end)
                        #
                        # # first situation, two interval overlaps, and ano start later than main
                        # if ano_interval.overlaps(main_interval) and ano_start > main_start:
                        #     responded = True
                        #     break
                        # # second situation, two interval not overlap, ano start few seconds after the first end
                        # elif 0 < ano_start - main_end < RESPONDED_THRESHOLD:
                        #     responded = True
                        #     break
                        # else it is not responded, do nothing, keep responded as False
                    if responded:
                        respond_list.append(another_color)
            if len(respond_list) == 0:
                respond_list.append("outsider")
            main_df.at[i, "target"] = ",".join(respond_list)
    return audio_spatial_dict


def export_df_in_dict(dict_holding_df: dict, output_folder_path: str):
    """
    export df within a dict to a folder
    :param output_folder_path:
    :param dict_holding_df:
    :return:
    """
    for a_key in dict_holding_df:
        dict_holding_df[a_key].to_excel(os.path.join(output_folder_path, a_key + ".xlsx"))


def determine_where_speak(audio_dict: dict, spatial_dict: dict):
    """
    use audio and spatial information to detect where is a studnet when he/she speak anything
    results will be added to a new column inside data frame in audio_dict
    :param audio_dict: structure:{color: pd.Dataframe(columns=[color, start, end])}
    :param spatial_dict: structure:{locations: [intervals of where a student is,],)}
    :return:
    """
    for a_color in COLORS:
        # adding a empty column to df to hold the location information
        a_audio_df = audio_dict[a_color]
        a_audio_df["location"] = ""
        a_spatial_dict = spatial_dict[a_color]

        # iterate each line in audio df
        for i, row in a_audio_df.iterrows():
            # use python-interval package to structure the data
            audio_interval = portion.closed(float(row["start"]), float(row["end"]))
            # potential_locations = [a_location for a_location in a_spatial_dict if a_spatial_dict[a_location].overlaps(audio_interval)]
            potential_locations = []
            for a_location in a_spatial_dict:
                # the overlap method will determine whether the intervals have overlaps
                if a_spatial_dict[a_location].overlaps(audio_interval):
                    potential_locations.append(a_location)

            if len(potential_locations) == 0:
                potential_locations.append("undetected")
            a_audio_df.at[i, "location"] = ",".join(potential_locations)
    return audio_dict


def getOverlap(a, b):
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def load_ground_truth(ground_truth_path: str):
    """
    load ground truth information from a given folder,
    the ground truth is just the manually created excel for
    :param ground_truth_path:
    :return:
    """
    ground_truth_df = pd.read_excel(ground_truth_path)
    # extract ground truths into a dict
    gt_dict = {}
    for a_color in COLORS:
        gt_dict[a_color] = ground_truth_df[ground_truth_df["initiator"] == a_color]
    return gt_dict


def __extract_length_from_interval(interval_list):
    total_length = 0
    for an_interval in interval_list:
        total_length += an_interval[1] - an_interval[0]
    return total_length


@timer
def testing_accuracy(audio_dict: dict, gt_dict: dict, accuracy_mode: str = "all", doctor_enter_time: float = 0, use_length: bool = True):
    """

    :param audio_dict:
    :param gt_dict:
    :param accuracy_mode: for determining which methods for calculating accuracy
    :return:
    """

    for a_color in COLORS:
        a_audio_df = audio_dict[a_color]
        a_audio_df["ground_truth_target"] = ""
        if doctor_enter_time != 0:
            less_than_df = a_audio_df[a_audio_df["start"] > doctor_enter_time]
            for i, row in less_than_df.iterrows():
                a_audio_df.drop(i, inplace=True)

        a_gt_df = gt_dict[a_color]
        for i, row in a_audio_df.iterrows():
            main_interval = portion.closed(row["start"], row["end"])
            gt_loc_set = set()
            overlaps_dict = {}    # a dictionary to hold the length of overlaps, to hold only one target in list
            for j, ano_row in a_gt_df.iterrows():
                ano_interval = portion.closed(ano_row["start_time"], ano_row["end_time"])
                if main_interval.overlaps(ano_interval):
                    gt_loc_set.add(ano_row["receiver"])
                    # hold the overlaps value
                    overlaps_dict[ano_row["receiver"]] = getOverlap((row["start"], row["end"]),
                                                                    (ano_row["start_time"], ano_row["end_time"]))
            # handle the problem where multiple target were found
            if len(gt_loc_set) > 1:
                gt_loc_set = set()
                gt_loc_set.add(max(overlaps_dict.items(), key=operator.itemgetter(1))[0])
            # location should be only one, but sometime there might be two,
            # raise an error to have a look when it will happen
            assert len(gt_loc_set) == 1 or len(gt_loc_set) == 0
            # if only one target were found, just pop it as ground truth
            if len(gt_loc_set) == 1:
                a_audio_df.at[i, "ground_truth_target"] = gt_loc_set.pop()
            elif len(gt_loc_set) == 0:
                a_audio_df.at[i, "ground_truth_target"] = "no ground truth"
    export_df_in_dict(audio_dict, "testing/testing_session_211/automatical_generated_locationwith_gt")
    # calculating accuracy using different methods
    positive_dict = {}
    negative_dict = {}
    accuracy_dict = {}
    TO_REPLACE_LIST = ["doctor", "patient", "relative", "control", "phone"]
    for a_color in COLORS:
        a_audio_df = audio_dict[a_color]

        # replace the ones outside nursing team to outsider, to enable compare detected target with ground truth
        a_audio_df.replace(TO_REPLACE_LIST, "outsider")

        a_positive_list = []
        a_negative_list = []
        for i, row in a_audio_df.iterrows():
            gt_target_str = row["ground_truth_target"]
            if gt_target_str == "no ground truth":
                continue
            # do it second time, due to multiple target may be in one
            for a_to_be_replace in TO_REPLACE_LIST:
                gt_target_str = gt_target_str.replace(a_to_be_replace, "outsider")

            # using set to hold the ground truth list and original target list, to make comparison easier later
            gt_target_set = set(gt_target_str.split(","))
            target_set = set(row["target"].split(","))

            # using different methods to calculate accuracy
            if accuracy_mode == "all":
                if len(target_set.intersection(gt_target_set)) > 0:
                    a_positive_list.append((row["start"], row["end"]))
                else:
                    a_negative_list.append((row["start"], row["end"]))
            elif accuracy_mode == "team":
                # this mode only
                pass
            elif accuracy_mode == "bef_doc":
                pass

        positive_dict[a_color] = a_positive_list
        negative_dict[a_color] = a_negative_list
        if use_length:
            positive_length = __extract_length_from_interval(a_positive_list)
            negative_length = __extract_length_from_interval(a_negative_list)
            accuracy_dict[a_color] = positive_length / (positive_length + negative_length)
        else:
            accuracy_dict[a_color] = len(a_positive_list) / (len(a_positive_list) + len(a_negative_list))
    # todo: accuracy 过低，初步检查应该是responded detection那边有问题单独工作的blue一直被detect成跟red说话
    print()
    return accuracy_dict
    # if accuracy_mode == "no_undetected"


def unpackaging_comma_separation(package_in_list: list):
    result_set = set()
    for a_str in package_in_list:
        for a_color in a_str.split(','):
            if a_color != "":
                result_set.add(a_color)
    return list(result_set)


def responded_detection_using_yaw(audio_dict, coord_yaw_dict, extended_boundary=0):
    for a_color in audio_dict:
        main_audio_df = audio_dict[a_color]
        main_coord_yaw_df = coord_yaw_dict[a_color]
        main_audio_df["target"] = ""
        main_audio_df["in_sight"] = ""

        for i, row in main_audio_df.iterrows():
            boundary_start = row["start"] - extended_boundary
            boundary_end = row["end"] + extended_boundary
            rows = main_coord_yaw_df.loc[(main_coord_yaw_df["audio_timestamp"] >= boundary_start) &
                                         (main_coord_yaw_df["audio_timestamp"] <= boundary_end)]
            potential_targets = pd.unique(rows["in_sight"])
            in_sight_list = []
            # split the comma separation into a list
            unpackaged_targets = unpackaging_comma_separation(potential_targets)
            for a_target_color in unpackaged_targets:
                tar_coord_yaw_df = coord_yaw_dict[a_target_color]
                tar_rows = tar_coord_yaw_df[(tar_coord_yaw_df["audio_timestamp"] >= boundary_start) &
                                            (tar_coord_yaw_df["audio_timestamp"] <= boundary_end)]
                tar_potential_targets = pd.unique(tar_rows["in_sight"])
                tar_potential_targets = unpackaging_comma_separation(tar_potential_targets)
                # !!!!!!!!!!! important, here is the logic to determine whether two students are in sight of each other
                if a_color in tar_potential_targets:
                    in_sight_list.append(a_target_color)

                # then it is time to use the actual responded detection to detect whether it is responded
            main_audio_df.at[i, "in_sight"] = ",".join(in_sight_list)
            target_list = []
            for a_target in in_sight_list:
                tar_audio_df = audio_dict[a_target]
                responded = False
                for j, tar_row in tar_audio_df.iterrows():
                    responded = _determine_responded(main_start=row["start"], main_end=row["end"],
                                                     ano_start=tar_row["start"], ano_end=tar_row["end"])
                    if responded:
                        break
                if responded:
                    target_list.append(a_target)
            if len(target_list) == 0:
                target_list.append("outsider")
            # if
            main_audio_df.at[i, "target"] = ",".join(target_list)
    return audio_dict
    # df.loc[(df['column_name'] >= A) & (df['column_name'] <= B)]


######################################3
# helper above ↑, main func below ↓
#######################################

def extract_information(audio_folder_path: str, pozyx_json_path: str, coordinates_path: str,
                        sync_path, doctor_enter_time: float = 0,
                        testing: bool = False,
                        ground_truth_path: str = ""):
    """

    :param testing:
    :param ground_truth_path:
    :param coordinates_path:
    :param audio_folder_path: the folder of audio data for four colors of students
    :param pozyx_json_path: the json file generated by Pozyx
    :return:
    """
    # fetching spatial data
    spatial_dict = extract_loction_dict(pozyx_json_path, coordinates_path, sync_path)
    spatial_dict = formatting_spatial_data(spatial_dict)
    # fetching audio data
    audio_dict = extract_vad(audio_folder_path)
    # using audio and spatial data to determine where a student is, while they talking (having start and end)
    audio_dict = determine_where_speak(audio_dict, spatial_dict)
    # just run this function, then the audio_dict will be added with a target column to hold conversation target
    audio_dict = responded_detection(audio_dict)
    # if testing:
    #     export_df_in_dict(audio_dict, "testing/testing_session_207/automatical_generated_location")
    # load ground truth of speaking target for testing
    ################ following codes are used for testing. ####################
    if testing and ground_truth_path == "":
        print("If you want to test, the path of ground truth file should be given!")
    if testing and ground_truth_path != "":
        gt_dict = load_ground_truth(ground_truth_path)
        export_df_in_dict(gt_dict, "testing/testing_session_211/automatical_generated_locationwith_gt")
        testing_accuracy(audio_dict, gt_dict, doctor_enter_time=doctor_enter_time)
    print()
    # todo:
    #  1. 再检查一下生成的dataframe 的location是不是合适
    #  2. 利用这个location信息，把学生的start and end分到相应的bed上去，如果某个区域只有一个学生，那么可以认为他是在跟队外的人说话
    #  3. 找一下之前的responded speech的code，用在这里，detect是不是跟relative说话
    #  4. 问题，doctor来了的情况如何判断？先强行试一下，不行看
    #  5. 用这些信息获得social network，学生对学生之间的对话量
    #  6. B4和其他区域的social network，
    #  7. 连接到visualisation上

    return


def extract_information_with_yaw(audio_folder_path: str, pozyx_json_path: str, coordinates_path: str, sync_path, doctor_enter_time,
                                 fov_thres, dist_thres, absolute_thres,
                                 testing: bool = False,
                                 ground_truth_path: str = "",
                                 testing_result_output_folder: str = ""):
    """

    :param testing:
    :param ground_truth_path:
    :param coordinates_path:
    :param audio_folder_path: the folder of audio data for four colors of students
    :param pozyx_json_path: the json file generated by Pozyx
    :return:
    """
    # fetching spatial data

    coord_yaw_dict = extract_interpolated_pozyx_with_yaw(pozyx_json_path, sync_path, fov_thres, dist_thres, absolute_thres=absolute_thres)


    # fetching audio data
    audio_dict = extract_vad(audio_folder_path)

    # just run this function, then the audio_dict will be added with a target column to hold conversation target
    audio_dict = responded_detection_using_yaw(audio_dict, coord_yaw_dict, 1)

    # if testing:
    #     export_df_in_dict(audio_dict, "testing/testing_session_207/automatical_generated_location")
    # load ground truth of speaking target for testing
    ################ following codes are used for testing. ####################
    if testing and ground_truth_path == "":
        print("If you want to test, the path of ground truth file should be given!")
    if testing and ground_truth_path != "":
        gt_dict = load_ground_truth(ground_truth_path)
        export_df_in_dict(gt_dict, testing_result_output_folder)
        testing_accuracy(audio_dict, gt_dict, doctor_enter_time=doctor_enter_time)
    print()

    return audio_dict


# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    # path_audio_folder = "testing/testing_session_207/audio"
    # path_pozyx_json = "testing/testing_session_207/spatial/207.json"
    # sync_path = "testing/testing_session_207/sync.txt"
    # path_ground_truth = "testing/testing_session_207/ground_truth_location/detd_timetaged_207.xlsx"
    # path_coordinates = "Coordinates.csv"
    # doctor_enter_time = 0

    path_audio_folder = "testing/testing_session_211/audio"
    path_pozyx_json = "testing/testing_session_211/spatial/211.json"
    sync_path = "testing/testing_session_211/sync.txt"
    path_ground_truth = "testing/testing_session_211/ground_truth_location/detd_timetaged_211.xlsx"
    path_coordinates = "Coordinates.csv"
    testing_result_output_folder_path = "testing/testing_session_211/automatical_generated_locationwith_gt"
    doctor_enter_time = 0
    # extract_information(path_audio_folder, path_pozyx_json, path_coordinates, sync_path, doctor_enter_time=doctor_enter_time,
    #                     testing=True,
    #                     ground_truth_path=path_ground_truth)
    extract_information_with_yaw(path_audio_folder, path_pozyx_json, path_coordinates, sync_path,
                                 doctor_enter_time=doctor_enter_time, testing=True,
                                 fov_thres=200, dist_thres=2000, absolute_thres=500, ground_truth_path=path_ground_truth,
                                 testing_result_output_folder=testing_result_output_folder_path)
    # a_portion = portion.closed(1,5)
    # another_portion = portion.closed(1, 5) | portion.closed(7, 10)
    # print(a_portion.upper, a_portion.lower)
    # print(another_portion.upper, another_portion.)
