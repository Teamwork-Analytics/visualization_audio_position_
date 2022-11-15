import math
import os

import numpy as np
import pandas as pd

from pozyx_extraction import extract_interpolate_single_session
from pozyx_extraction import BLACK_ID, BLUE_ID, RED_ID, GREEN_ID, WHITE_ID, YELLOW_ID, COLOR_TO_ID, ID_TO_COLOR


# Coordinates of critical locations
# May need to modify while want to use

def export_df_in_dict(dict_holding_df: dict, output_folder_path: str):
    """
    export df within a dict to a folder
    :param output_folder_path:
    :param dict_holding_df:
    :return:
    """
    for a_key in dict_holding_df:
        dict_holding_df[a_key].to_excel(os.path.join(output_folder_path, a_key + ".xlsx"))


def _proximity(x, distance, a):
    # if within the circle, set as that location
    if distance >= x >= 0:
        x = a
    elif x > distance:
        x = 'in'  # in the ROOM
    else:
        x = 'out'  # out the ROOM
    return x


def proxemicsSpaces(df_pivoted, dfco):
    """
    processing the pozyx data to give location labels.

    :param df_pivoted:
    :param numberOfTrackers:
    :param dfco:
    :return:
    """

    arealist = dfco.area.unique()
    a_dict = {}
    for a_tracker_id in df_pivoted:

        a_dict[a_tracker_id] = pd.DataFrame(columns=['timestamp'])
        a_dict[a_tracker_id]['timestamp'] = df_pivoted[a_tracker_id]['audio_timestamp']

        for a in arealist:
            PLables_column_name = str(a)
            distance = float(dfco[dfco.area == a].distance)
            area_x = float(dfco[dfco.area == a].x)
            area_y = float(dfco[dfco.area == a].y)
            a_dict[a_tracker_id][PLables_column_name] = np.sqrt(
                (df_pivoted[a_tracker_id]['x'] - area_x) ** 2 + (df_pivoted[a_tracker_id]['y'] - area_y) ** 2).map(
                lambda x: _proximity(x, distance, a)
            )

    # export the dataframes for testing
    # for an_id in a_dict:
    #     a_dict[an_id].to_excel("testing/testing_output/{}.xlsx".format(ID_TO_COLOR[str(an_id)]))
    return a_dict


def _hms_to_seconds(hms: str):
    """ transform timestamp in HH:MM:SS to seconds"""
    h, m, s = hms.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)


def _processing_timestamps(critical_time_sr: pd.Series):
    a_time_list = []
    for a_timestamp in critical_time_sr:
        if type(a_timestamp) == str:
            if len(a_timestamp.split(':')) == 3:
                a_time_list.append(_hms_to_seconds(a_timestamp))
        else:
            a_time_list.append(a_timestamp)

    a_time_list.sort()
    # cluster the single continuous timestamp
    interval_list = []
    time_buffer = []
    for a_timestamp in a_time_list:
        # statment to handle the first iteration
        if len(time_buffer) == 0:
            time_buffer.append(a_timestamp)
            continue

        # adding timestamp when the last timestamp in buffer is continous with timestamp in current iteration
        if a_timestamp - time_buffer[-1] == 1:
            time_buffer.append(a_timestamp)
            continue

        # stop adding timestamp into buffer
        if a_timestamp - time_buffer[-1] > 1:
            interval_list.append((time_buffer[0], time_buffer[-1]))
            time_buffer = []
            time_buffer.append(a_timestamp)
            continue
    if len(time_buffer) != 0:
        interval_list.append((time_buffer[0], time_buffer[-1]))
    return interval_list


def _get_continuous_time(a_proximics_df: pd.DataFrame, coordinate_rules_df):
    beds = ("B1", "B2", "B3", "B4")
    area_list = list(coordinate_rules_df["area"])  # the detailed criticl locations, like B1_Patient
    location_interval_dict = {}

    # from the list of where a student currently staying on,
    # extract the interval of time a student staying on a critical location
    for an_area in area_list:
        critical_area_df = a_proximics_df[["timestamp", an_area]]
        critical_time_df = critical_area_df.loc[critical_area_df[an_area] == an_area]
        an_interval_list = _processing_timestamps(critical_time_df["timestamp"])
        location_interval_dict[an_area] = an_interval_list

    # merge the location that has B,
    bed_interval_dict = {}
    for a_bed in beds:
        bed_interval_dict[a_bed] = []
        for a_key in location_interval_dict:
            if a_bed in a_key:
                bed_interval_dict[a_bed] += location_interval_dict[a_key]

    # adding other location to dict
    bed_interval_dict["other"] = []
    for a_key in location_interval_dict:
        is_other = True
        for a_bed in beds:
            if a_bed in a_key:
                is_other = False
        if is_other:
            bed_interval_dict["other"] += location_interval_dict[a_key]

    return bed_interval_dict


def processing_proximics_dict(proxemics_dict: dict, coordinate_rules_df: pd.DataFrame):
    """process the dict contain the location information of each student
    in each second into intervals
    e.g. from [1,2,3,4,5,6,10,11,12] to [(1,6), (10,12)]"""

    processed_proxemics_dict = {}
    for a_student_id in proxemics_dict:
        a_proximics_df = proxemics_dict[a_student_id]
        processed_proxemics_dict[a_student_id] = _get_continuous_time(a_proximics_df, coordinate_rules_df)
    return processed_proxemics_dict


def __extract_single_session(input_path: str, coordinate_rules_df: pd.DataFrame, sync_path):
    """
    using an external input files to
    :param input_path: pozyx json path
    :param coordinates_path: coordinates path, in csv
    :return:
    """
    """DO CHECK FOLLOWING SECTION, Critical constant settings, it may be different for each simulation"""
    # coordinates_path = "Coordinates.csv"
    # input_path = "testing/182.json"
    RED_ID = 27226
    BLUE_ID = 27261
    GREEN_ID = 27160
    YELLOW_ID = 27263
    """'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''"""
    # coordinate_rules_df = pd.read_csv(coordinates_path, delimiter=",")

    interpolated_dict = extract_interpolate_single_session(input_path, sync_path)
    proxemics_dict = proxemicsSpaces(interpolated_dict, coordinate_rules_df)
    # proxemics_df = pd.DataFrame(proxemics_dict)
    return proxemics_dict


def correction(radian: float):
    return 2 * math.pi - radian


def get_within_view(p1: np.ndarray, p1_yaw: float, p2: np.ndarray, p2_yaw: float, fov: int, distance_thres: int,
                    absolute_thres: int):
    distance = np.linalg.norm(p1 - p2)
    if distance > distance_thres:
        return False
    if distance < absolute_thres:
        return True
    p1_yaw_vec = np.array([math.cos(p1_yaw), math.sin(p1_yaw)])
    p2_yaw_vec = np.array([math.cos(p2_yaw), math.sin(p2_yaw)])

    p1_to_p2_vec = p2 - p1
    p2_to_p1_vec = p1 - p2
    dot_product_p1_p2 = np.dot(p1_to_p2_vec / np.linalg.norm(p1_to_p2_vec), p1_yaw_vec / np.linalg.norm(p1_yaw_vec))
    dot_product_p2_p1 = np.dot(p2_to_p1_vec / np.linalg.norm(p2_to_p1_vec), p2_yaw_vec / np.linalg.norm(p2_yaw_vec))
    # math.degree can be used to change radius to angle
    angle_p1_to_p2 = math.degrees(np.arccos(dot_product_p1_p2))
    angle_p2_to_p1 = math.degrees(np.arccos(dot_product_p2_p1))
    # print()

    if angle_p1_to_p2 < fov / 2 and angle_p2_to_p1 < fov / 2:
        return True
    else:
        return False


def extract_interpolated_pozyx_with_yaw(pozyx_json_path: str, sync_path: str, fov_thres: int, dist_thres: int,
                                        absolute_thres: int, output_folder_path: str = ""):
    interpolated_dict_use_id = extract_interpolate_single_session(pozyx_json_path, sync_path)
    use_color_dict = {}
    for an_id in interpolated_dict_use_id:
        interpolated_dict_use_id[an_id]["yaw"] = interpolated_dict_use_id[an_id]["yaw"].apply(
            lambda radian: 2 * math.pi - radian)
        use_color_dict[ID_TO_COLOR[str(an_id)]] = interpolated_dict_use_id[an_id]

    # this two lines of codes are for testing
    # todo comment those two lines when actually using them
    # use_color_dict["black"] = use_color_dict["red"].copy(deep=True)
    # use_color_dict["white"] = use_color_dict["red"].copy(deep=True)

    # two layer for-statement, to detect for each line, whether there are someone within this one's sight
    for a_color in use_color_dict:
        main_df = use_color_dict[a_color]
        main_df["in_sight"] = ""
        for i, row in main_df.iterrows():
            main_p = np.array([row["x"], row["y"]])
            main_yaw = row["yaw"]
            timestamp = row["audio_timestamp"]

            insight_list = []
            for ano_color in use_color_dict:
                if a_color != ano_color:
                    ano_df = use_color_dict[ano_color]
                    ano_rows = ano_df.loc[ano_df['audio_timestamp'] == timestamp]
                    assert len(ano_rows.index) <= 1
                    if len(ano_rows.index) == 1:
                        ano_row = ano_rows.iloc[0]
                        ano_p = np.array([ano_row["x"], ano_row["y"]])
                        ano_yaw = ano_row["yaw"]
                        if get_within_view(main_p, main_yaw, ano_p, ano_yaw, fov=fov_thres, distance_thres=dist_thres,
                                           absolute_thres=absolute_thres):
                            insight_list.append(ano_color)
                    elif len(ano_rows.index) < 1:
                        pass
                    else:
                        # it should not happen
                        assert True
            main_df.at[i, "in_sight"] = ",".join(insight_list)
    if output_folder_path != "":
        export_df_in_dict(use_color_dict, output_folder_path)
    return use_color_dict


def extract_loction_dict(pozyx_json_path: str, coordinates_path: str, sync_path):
    coordinate_rules_df = pd.read_csv(coordinates_path, delimiter=",")
    prox_dict = __extract_single_session(pozyx_json_path, coordinate_rules_df, sync_path)
    prox_interval_dict = processing_proximics_dict(prox_dict, coordinate_rules_df)
    # todo: extraction of spatial data interval is done, next step is
    #   extract audio data, simply use the VAD and then use the responded speech to detect who is talking to whom.

    return prox_interval_dict


if __name__ == '__main__':
    path = "testing/testing_session_207/spatial/207.json"
    coordinates = "Coordinates.csv"
    sync_path = "testing/testing_session_207/sync.txt"
    # extract location information with Jimmy's code
    # extract_loction_dict(path, coordinates, sync_path)
    path_211_pozyx = "testing/testing_session_211/211.json"
    path_211_sync = "testing/testing_session_211/sync.txt"
    # extract interpolated pozyx yaw
    extract_interpolated_pozyx_with_yaw(path, sync_path, fov_thres=200, dist_thres=2000,
                                        output_folder_path="testing/testing_session_207/interpolated_yaw_coord")
    # extract_interpolated_pozyx_with_yaw(path_211_pozyx, "testing/testing_session_207/interpolated_yaw_coord", path_211_sync)
