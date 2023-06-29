# https://r-graph-gallery.com/257-input-formats-for-network-charts.html
# https://igraph.org/python/
# https://networkx.org/documentation/stable/auto_examples/external/plot_igraph.html#sphx-glr-auto-examples-external-plot-igraph-py
# arrow curve https://stackoverflow.com/questions/16875547/using-igraph-how-to-force-curvature-when-arrows-point-in-opposite-directions
import math
import os

# import igraph as ig
import matplotlib.pyplot as plt
import pandas as pd

from audio_code import COLORS
from audio_spatail_processing import extract_information_with_yaw

# from testing.nx_playground import generating_network

#################################################
# the maximum size of a node in the social network.
# This should be determined using the data from last year
MAX_NODE_SIZE_S1 = 80
MAX_NODE_TIME_S1 = 660  # todo: still need to be changed
MAX_EDGE_WIDTH_S1 = 25
MAX_EDGE_TIME_S1 = 300

MAX_NODE_SIZE_S2 = 80
MAX_NODE_TIME_S2 = 190  # todo: still need to be changed
MAX_EDGE_WIDTH_S2 = 25
MAX_EDGE_TIME_S2 = 80

AREA_ADJUSTION = 7
###########################################33

def load_to_igraph(file_path: str):
    """load adjacent table saved in execl"""
    adj_table: pd.Dataframe = pd.read_excel(file_path)
    adj_table = adj_table.to_numpy()[:, 1: 6]
    return ig.Graph.Weighted_Adjacency(matrix=adj_table, mode="directed")


def area_to_radius(area: float, adjustion: float):
    """reduction is to prevent the circle size from being too big"""
    return math.sqrt(area) * adjustion


def __normalization_length(audio_dict: dict, adjacent_df, session_type, size_method):
    vis_dict = {}
    if session_type == "A":
        max_node_size = MAX_NODE_SIZE_S1
        max_node_time = MAX_NODE_TIME_S1
        max_edge_width = MAX_EDGE_WIDTH_S1
        max_edge_time = MAX_EDGE_TIME_S1
    elif session_type == "B":
        # max_node_size = MAX_NODE_SIZE_S2
        # max_node_time = MAX_NODE_TIME_S2
        # max_edge_width = MAX_EDGE_WIDTH_S2
        # max_edge_time = MAX_EDGE_TIME_S2
        max_node_size = MAX_NODE_SIZE_S1
        max_node_time = MAX_NODE_TIME_S1
        max_edge_width = MAX_EDGE_WIDTH_S1
        max_edge_time = MAX_EDGE_TIME_S1
    else:
        raise ValueError

    for a_color in audio_dict:
        if size_method == "radius":
            audio_dict[a_color][0] = max_node_size * audio_dict[a_color][0] / max_node_time
        elif size_method == "area":
            audio_dict[a_color][0] = area_to_radius(max_node_size * audio_dict[a_color][0] / max_node_time, AREA_ADJUSTION)
        else:
            raise ValueError

        for a_target in audio_dict[a_color][1]:
            audio_dict[a_color][1][a_target] = max_edge_width * audio_dict[a_color][1][a_target] / max_edge_time
            adjacent_df.at[a_color, a_target] = max_edge_width * adjacent_df.at[a_color, a_target] / max_edge_time
    return audio_dict, adjacent_df


def __normalization_prop(audio_dict: dict, adjacent_df, session_type):
    total_spk_time = 0
    for a_color in audio_dict:
        total_spk_time += audio_dict[a_color][0]

    for a_color in audio_dict:
        if total_spk_time != 0:
            audio_dict[a_color][0] = audio_dict[a_color][0] / total_spk_time
        else:
            audio_dict[a_color][0] = 0

        for a_target in audio_dict[a_color][1]:
            if total_spk_time != 0:

                audio_dict[a_color][1][a_target] = audio_dict[a_color][1][a_target] / total_spk_time
                adjacent_df.at[a_color, a_target] = adjacent_df.at[a_color, a_target] / total_spk_time
            else:
                audio_dict[a_color][1][a_target] = 0
                adjacent_df.at[a_color, a_target] = 0

    return audio_dict, adjacent_df


def __mapping_prop_to_plotting_values(audio_dict, adjacent_df, size_method):

    """change the value here to adjust the size of circle or arrow"""
    MAX_NODE_PROP = 0.6
    MAX_EDGE_PROP = 0.4
    MAX_NODE_SIZE = MAX_NODE_SIZE_S1
    MAX_EDGE_SIZE = MAX_EDGE_WIDTH_S1
    total_spk_time = 0

    for a_color in audio_dict:
        if size_method == "radius":
            audio_dict[a_color][0] = MAX_NODE_SIZE * audio_dict[a_color][0] / MAX_NODE_PROP
        elif size_method == "area":
            audio_dict[a_color][0] = area_to_radius(MAX_NODE_SIZE * audio_dict[a_color][0] / MAX_NODE_PROP, AREA_ADJUSTION)
        else:
            raise ValueError

        for a_target in audio_dict[a_color][1]:
            audio_dict[a_color][1][a_target] = MAX_EDGE_SIZE * audio_dict[a_color][1][a_target] / MAX_EDGE_PROP
            adjacent_df.at[a_color, a_target] = MAX_EDGE_SIZE * adjacent_df.at[a_color, a_target] / MAX_EDGE_PROP

    return audio_dict, adjacent_df


def precessing_audio_dict(audio_dict: dict):
    """ calculate raw audio dict and adjacent df, RAW means no normalization has been done on them"""
    raw_dict = {}
    adjacent_df = pd.DataFrame({
        "red": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "green": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "blue": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "yellow": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "white": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "black": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "outsider": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    }, index=["red", "green", "blue", "yellow", "white", "black", "outsider"])
    ##########################
    for a_key in audio_dict:

        a_audio_df = audio_dict[a_key]

        tar_dict = {}
        total_spk = 0
        a_list_in_vis = [total_spk, tar_dict]
        # the first position should be the speaking time
        # the second postion should be the time communicate to a stuent

        a_to_other_dict = {}  # this one is just for testing
        for a_color in COLORS:
            tar_dict[a_color] = 0

        tar_dict["outsider"] = 0
        #########################################
        # this if statement is for removing the arrows pointing from doctors and relatives
        if a_key == "black" or a_key == "white":
            raw_dict[a_key] = a_list_in_vis
            continue
        ########################################

        for i, row in a_audio_df.iterrows():
            targets = row['target'].split(",")
            spk_time = row["end"] - row["start"]
            a_list_in_vis[0] += spk_time
            for a_target in targets:
                tar_dict[a_target] += spk_time
                adjacent_df.at[a_key, a_target] += spk_time

        raw_dict[a_key] = a_list_in_vis



    return raw_dict, adjacent_df


# def __assign_vertex_size(audio_dict: dict):
#     """assign the vertex size with given audio_dict,
#        following the ["R", "G", "B", "Y", "out"]
#     """
#     a_list = [0.0, 0.0, 0.0, 0.0, 0.0]

def social_network_plotting_length(vis_dict: dict, adjacent_df, adjacent_df_temp_path: str, save_path: str):
    adjacent_df.to_excel(adjacent_df_temp_path)
    g = load_to_igraph(adjacent_df_temp_path)
    # get node size

    g["title"] = "communication network"
    g.vs["name"] = ["Red", "Green", "Blue", "Yellow", "patients/relative/doctor"]
    # g.vs["name"] = ["A", "B", "C", "D", "patients/relative/doctor"]
    layout = g.layout('circular')
    # assigning values to features need to use
    vertex_size = [vis_dict["red"][0],
                   vis_dict["green"][0],
                   vis_dict["blue"][0],
                   vis_dict["yellow"][0],
                   1]
    vertex_size = [i * 0.01 for i in vertex_size]
    vertex_frame_width = [(i * 0) + 0.5 for i in vertex_size]
    edge_width = [i * 0.2 for i in g.es["weight"]]

    edge_curved = [(i * 0 + 1) * 0.08 for i in g.es["weight"]]
    label_dist = [(i * 0 + 1) * 100 for i in g.es["weight"]]

    # using those parameters to generate a graph
    fig, ax = plt.subplots(figsize=(8, 6))
    visual_style = {}
    visual_style["vertex_size"] = vertex_size
    visual_style["vertex_color"] = "lightblue"
    visual_style["vertex_label"] = g.vs["name"]
    visual_style["vertex_label_angle"] = 3
    # visual_style["vertex_label_dist"] = label_dist
    visual_style["edge_curved"] = edge_curved
    visual_style["edge_width"] = edge_width
    visual_style["vertex_frame_color"] = "black"
    visual_style["vertex_frame_width"] = vertex_frame_width
    visual_style["edge_arrow_size"] = 0.003
    visual_style["edge_arrow_width"] = 1
    visual_style["layout"] = layout
    # visual_style["bbox"] = (800, 800)
    visual_style["margin"] = 0.8
    visual_style["vertex_shape"] = "circle"

    ig.plot(
        g,
        target=ax,
        **visual_style
    )
    # plt.axis("off")
    # ax.set_xmargin(100)
    # ax.set_ymargin(100)
    plt.subplots_adjust(left=0.0, right=1, top=1, bottom=0.0)
    if save_path != "":
        plt.savefig(save_path, bbox_inches='tight')
    plt.show()


def social_network_plotting_prop(vis_dict: dict, adjacent_df, adjacent_df_temp_path: str, save_path: str):
    adjacent_df.to_excel(adjacent_df_temp_path)
    adj_table = adjacent_df.to_numpy()
    g = ig.Graph.Weighted_Adjacency(matrix=adj_table, mode="directed")
    # get node size

    g["title"] = "communication network"
    g.vs["name"] = ["Red", "Gre", "Blu", "Yel", "Doctor", "Relative", "Patient"]
    # g.vs["name"] = ["A", "B", "C", "D", "patients/relative/doctor"]
    layout = g.layout('circular')
    # assigning values to features need to use
    vertex_size = [vis_dict["red"][0],
                   vis_dict["green"][0],
                   vis_dict["blue"][0],
                   vis_dict["yellow"][0],
                   1,
                   1,
                   1]
    vertex_size = [i * 0.01 for i in vertex_size]
    vertex_frame_width = [(i * 0) + 0.5 for i in vertex_size]
    edge_width = [i * 0.2 for i in g.es["weight"]]

    edge_curved = [(i * 0 + 1) * 0.08 for i in g.es["weight"]]
    label_dist = [(i * 0 + 1) * 100 for i in g.es["weight"]]

    # using those parameters to generate a graph
    fig, ax = plt.subplots(figsize=(8, 6))
    visual_style = {}
    visual_style["vertex_size"] = vertex_size
    visual_style["vertex_color"] = "lightblue"
    visual_style["vertex_label"] = g.vs["name"]
    visual_style["vertex_label_angle"] = 3
    # visual_style["vertex_label_dist"] = label_dist
    visual_style["edge_curved"] = edge_curved
    visual_style["edge_width"] = edge_width
    visual_style["vertex_frame_color"] = "black"
    visual_style["vertex_frame_width"] = vertex_frame_width
    visual_style["edge_arrow_size"] = 0.003
    visual_style["edge_arrow_width"] = 1
    visual_style["layout"] = layout
    # visual_style["bbox"] = (800, 800)
    visual_style["margin"] = 0.8
    visual_style["vertex_shape"] = "circle"

    ig.plot(
        g,
        target=ax,
        **visual_style
    )
    # plt.axis("off")
    # ax.set_xmargin(100)
    # ax.set_ymargin(100)
    plt.subplots_adjust(left=0.0, right=1, top=1, bottom=0.0)
    if save_path != "":
        plt.savefig(save_path, bbox_inches='tight')
    plt.clf()
    pass


def __handing_for_exporting_raw_data(raw_vis_dict, raw_adjacent_df, output_dict, output_folder_path):
    """adding the total spking time data and exporting raw adjacent matrix"""
    output_dict["blue"].append(raw_vis_dict["blue"][0])
    output_dict["green"].append(raw_vis_dict["green"][0])
    output_dict["red"].append(raw_vis_dict["red"][0])
    output_dict["yellow"].append(raw_vis_dict["yellow"][0])

    raw_adjacent_df.to_excel(os.path.join(output_folder_path, "adj_" + str(output_dict["session_id"][-1]) + ".xlsx"))




def generating_social_network(audio_dict, adjacent_df_temp_path: str, session_type: str, norm_method: str,
                              output_dict: dict, raw_data_output_folder_path: str, size_method: str = "radius", save_path: str = ""):
    """

    :param audio_dict: contain the four students as keys representing by colors
    :return:
    """
    # {"color": [total_speaking_time, speaking_target_dict{"color": speaking_time, ...}], ...}

    raw_vis_dict, raw_adjacent_df = precessing_audio_dict(audio_dict)
    if raw_data_output_folder_path != "":
        __handing_for_exporting_raw_data(raw_vis_dict, raw_adjacent_df, output_dict, raw_data_output_folder_path)
    if norm_method == "length":
        audio_dict, adjacent_df = __normalization_length(raw_vis_dict, raw_adjacent_df, session_type, size_method)
        social_network_plotting_length(audio_dict, adjacent_df, adjacent_df_temp_path, save_path)
    elif norm_method == "prop":
        audio_dict, adjacent_df = __normalization_prop(raw_vis_dict, raw_adjacent_df, session_type)
        # Two different plotting controller needs to be used, the value scale of length and prop normalization is different.
        audio_dict, adjacent_df = __mapping_prop_to_plotting_values(audio_dict, adjacent_df, size_method)
        social_network_plotting_prop(audio_dict, adjacent_df, adjacent_df_temp_path, save_path)

    else:
        raise ValueError

    # todo! 1. 两种normalization的实现
    #   2. 半径变成面积


########################################
# code below is testing or demo codes.

#############
# This is the most impressive service I have received in the last ten years.
# I was helping my friend to check if there is a parcel mistakenly send to there. The manager just

def generate_graphs(session_id, output_folder: str, norm_method, size_method, output_dict: dict, raw_data_output_folder_path: str):
    """
    The requried files need to follow a special structure to be correctly loaded
    sequence: 1. extract_information_with_yaw() to generate the initial audio_dict, this audio dict contains: start
                    and end of a utterance, color of speaker, target, and who is detected as insight.
              2. then use the generating generating_social_network()
              3. in generating_social_network(), it will generate a raw_visdict, structure is:
                    {color: [total_spk_time, {talk to color: spk_time, ...,}], ...,}
              4. use the raw ones to normalize, prop, or norm.
              5.
    :param session_id:
    :return:
    """
    session_id = str(session_id)
    base_folder = "testing/{}/".format(session_id)
    path_audio_folder = base_folder + "audio"
    path_pozyx_json = base_folder + "{}.json".format(session_id)
    sync_path = base_folder + "sync.txt"
    path_coordinates = "Coordinates.csv"
    doctor_enter_time = 0
    adjacent_temp_path = base_folder + "vis_temp.xlsx"
    session_type = "A" if int(session_id) % 2 == 1 else "B"
    fig_save_path = os.path.join(output_folder, "{}.png".format(session_id))
    if raw_data_output_folder_path != "":
        output_dict["session_id"].append(session_id)
    # extract_information(path_audio_folder, path_pozyx_json, path_coordinates, sync_path, doctor_enter_time=doctor_enter_time,
    #                     testing=True,
    #                     ground_truth_path=path_ground_truth)

    audio_dict = extract_information_with_yaw(path_audio_folder, path_pozyx_json, path_coordinates, sync_path,
                                              doctor_enter_time=doctor_enter_time, testing=True,
                                              fov_thres=200, dist_thres=2000, absolute_thres=600)
    generating_social_network(audio_dict, adjacent_temp_path, session_type, save_path=fig_save_path,
                              size_method=size_method, norm_method=norm_method, output_dict=output_dict,
                              raw_data_output_folder_path=raw_data_output_folder_path)


def hard_coded_bulk_generates(output_folder, norm_method, size_method, raw_data_output_folder_path):
    """nunmbers in the tuple is the session id for plotting, using the plotting structure given in generate_graphs(
    ) """
    SESSIONS = (149, 181, 161, 173, 165, 180, 190, 160, 208, 207, 177)
    # SESSIONS = (180, 190, 160, 208)
    # SESSIONS = (161,)
    # SESSIONS = (177,)
    dict_for_df = {"session_id": [], "blue": [], "red": [], "green": [], "yellow": []}


    for a_session in SESSIONS:
        generate_graphs(a_session, output_folder, norm_method, size_method, dict_for_df, raw_data_output_folder_path)
    pd.DataFrame(dict_for_df).to_excel(os.path.join(raw_data_output_folder_path, "spk_time_for_each.xlsx"))

if __name__ == '__main__':
    # demo_code()
    # __demo_directed_network_plotting()
    # __demo_quickstart()
    # __demo_quickstart_cairo_demo()
    #
    # path_audio_folder = "testing/testing_session_211/audio"
    # path_pozyx_json = "testing/testing_session_211/spatial/211.json"
    # sync_path = "testing/testing_session_211/sync.txt"
    # path_ground_truth = "testing/testing_session_211/ground_truth_location/detd_timetaged_211.xlsx"
    # path_coordinates = "Coordinates.csv"
    # doctor_enter_time = 823
    # adjacent_temp_path = "testing/testing_session_211/vis_temp.xlsx"
    # session_type = "A"
    # # extract_information(path_audio_folder, path_pozyx_json, path_coordinates, sync_path, doctor_enter_time=doctor_enter_time,
    # #                     testing=True,
    # #                     ground_truth_path=path_ground_truth)
    #
    #
    # audio_dict = extract_information_with_yaw(path_audio_folder, path_pozyx_json, path_coordinates, sync_path,
    #                                           doctor_enter_time=doctor_enter_time, testing=True,
    #                                           fov_thres=200, dist_thres=2000, absolute_thres=400)
    # generating_social_network(audio_dict, adjacent_temp_path, "A")

    output_path = "testing/new_normalization_test/square/radius"
    raw_data_output_folder_path = "testing/new_normalization_test/raw_data_record"
    hard_coded_bulk_generates(output_path, "prop", "radius", raw_data_output_folder_path)
    # output_path = "testing/new_normalization_test/area/length"
    # hard_coded_bulk_generates(output_path, "length", "area")
