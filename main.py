import os
import pandas as pd
from datetime import datetime

from IPA import main_IPA
from config import Constant
from pozyx_json_to_csv_2022 import pozyx_json_to_csv
from vad.pozyx_extraction import main
from vad.hive_automation import hive_main
from pymongo import MongoClient
import matplotlib.pyplot as plt



from social_network_generation import audio_visual

from flask import Flask
import ffmpeg

app = Flask(__name__)

# audio_pos_visualization_path = "C:\\develop\\saved_data\\audio_pos_visualization_data\\"
# hive_out = "C:\\develop\\saved_data\\"
base_path = "C:\\develop\\saved_data\\"


# folder_path, simulationid, handover_finish_time, secondary_nurses_enter_time, doctor_enter_time

@app.route("/audio-pos/<simulationid>")
def call_visualization(simulationid):
    client = MongoClient("mongodb+srv://admin:" + Constant.MONGO_DB_PASSWD + "@cluster0.ravibmh.mongodb.net/app?retryWrites=true&w=majority")

    db = client["app"]
    # Issue the serverStatus command and print the results

    simulation_obj = db.get_collection("simulations").find_one({"simulationId": simulationid})

    observation_obj = db.get_collection("observations").find_one({"_id":simulation_obj["observation"]})

    # phase_dict = {"handover": , "bed_4":, "ward_nurse":, "met_doctor":}
    # dict.fromkeys(observation_obj["phases"], )
    # item["timestamp"]
    print("db finish")

    handover_finish_time, secondary_nurses_enter_time, doctor_enter_time = 0, 0, 0
    for item in observation_obj["phases"]:
        if item["phaseKey"] == "handover":
            handover_finish_time = item["timestamp"].timestamp() #datetime.strptime(item["timestamp"], 'yyyy-MM-dd HH:mm:ss.SSS000').timestamp()
        elif item["phaseKey"] == "ward_nurse":
            secondary_nurses_enter_time = item["timestamp"].timestamp()# datetime.strptime(item["timestamp"], 'yyyy-MM-dd HH:mm:ss.SSS000').timestamp()
        elif item["phaseKey"] == "met_doctor":
            doctor_enter_time = item["timestamp"].timestamp() # datetime.strptime(item["timestamp"], 'yyyy-MM-dd HH:mm:ss.SSS000').timestamp()
        elif item["phaseKey"] == "bed_4":
            pass




    """--------------generate images---------------"""
    """-------------------------------------"""
    session = simulationid
    # pos_ = base_path + session + "\\" + session + ".json"
    data_dir = base_path + session + "\\"



    data_in = base_path + session + "\\" + session + ".json"
    sync_path = "{}\\sync.txt".format(base_path + session)


    json_csv_output_path = "pozyx_json_csv/" + session + ".csv"


    print("pozyx_json_to_csv")
    pozyx_json_to_csv(session, data_in, json_csv_output_path)
    print("pozyx_json_to_csv finish")
    plt.show()
    plt.clf()

    main_IPA(json_csv_output_path, int(session), data_dir + "\\teamwork.png")
    print("IPA finish")

    plt.show()
    plt.clf()


    if not os.path.exists(data_dir + "out"):
        os.mkdir(data_dir + "out")
    if not os.path.exists(data_dir + "out\\audio-sim"):
        os.mkdir(data_dir + "out\\audio-sim")
    if not os.path.exists(data_dir + "out\\pos"):
        os.mkdir(data_dir + "out\\pos")
    if not os.path.exists(data_dir + "out\\result"):
        os.mkdir(data_dir + "out\\result")

    # print("-p " + data_in + " -o " + hive_out + " -s " + sync_path)
    main(data_in, base_path + session + "\\out\\pos", sync_path)

    print("main  finish")
    """----------generate audio-sim csv files---------"""


    hive_data("RED", session, data_dir)
    hive_data("YELLOW", session, data_dir)
    hive_data("BLUE", session, data_dir)
    hive_data("GREEN", session, data_dir)
    hive_data("BLACK", session, data_dir)
    hive_data("WHITE", session, data_dir)

    result_dir = data_dir + "out\\result"
    df = pd.concat(map(pd.read_csv, [
        '{}\\{}_RED.csv'.format(result_dir, session),
        '{}\\{}_YELLOW.csv'.format(result_dir, session),
        '{}\\{}_BLUE.csv'.format(result_dir, session),
        '{}\\{}_GREEN.csv'.format(result_dir, session)]), ignore_index=True)

    df = df.sort_values(by='audio time')

    # client_dir = "../client/src/projects/hive/data"
    df.to_csv("{}/{}_all.csv".format(data_dir, session), sep=',', encoding='utf-8', index=False)
    plt.show()
    plt.clf()

    audio_visual(data_dir, simulationid, handover_finish_time, secondary_nurses_enter_time, doctor_enter_time, sync_path)
    print("audio_visual finish")

    plt.show()
    plt.clf()

    return "success"


def hive_data(colour, session, data_dir):
    # colour = "YELLOW"
    # file_date = "18-Aug-2021_15-33-14-715"
    audio_in = None
    audio_out = None
    filename_list = os.listdir(data_dir)
    for filename in filename_list:
        if filename.startswith("simulation_" + colour):
            audio_in = data_dir + filename
            audio_out = data_dir + "sim_" + colour + ".wav"
            break
    # audio_in = "{}/simulation_{}_{}_audio.wav".format(data_dir, colour, file_date)
    # audio_out = "{}/sim_{}.wav".format(data_dir, colour)

    # print(audio_in)
    # print(audio_out)

    if not audio_in or not audio_out:
        print("please copy the audio files")


    # !ffmpeg - i {audio_in} - ar 48000 {audio_out}

    if os.path.exists(audio_out):
        os.remove(audio_out)

    stream = ffmpeg.input(audio_in)
    audio = stream.audio
    stream = ffmpeg.output(audio, audio_out, **{'ar': '32000'})  # , 'acodec': 'flac'})
    ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)

    audio_sim_dir = data_dir + 'out\\audio-sim'
    pos_dir = data_dir + 'out\\pos'
    audio_csv_out = "{}/{}_{}.csv".format(audio_sim_dir, session, colour)

    # % run hive_automation.py - a {audio_out} - o {audio_csv_out} - s "145" - w "1" - t "3"

    if colour in ("BLACK", "WHITE"):
        return
    """comment here to remove multithreding audio processing"""
    hive_main(audio_out, audio_csv_out, session, 1, 3)

    dfp = pd.read_csv('{}/{}_{}.csv'.format(pos_dir, session, colour))
    dfa = pd.read_csv('{}/{}_{}.csv'.format(audio_sim_dir, session, colour))

    dfp.head()

    res = pd.merge(dfp, dfa, on="audio time")
    final = res.drop(labels=["Unnamed: 0_x", "Unnamed: 0_y", "session"], axis=1)
    final['tagId'] = colour
    final.head()

    result_dir = data_dir + "out\\result"
    result_csv = "{}/{}_{}.csv".format(result_dir, session, colour)
    final.to_csv(result_csv, sep=',', encoding='utf-8', index=False)


"""
send get request to localhost:5000/audio-pos
"""
if __name__ == '__main__':
    app.run("0.0.0.0", port=5050)


    # call_visualization("181")



    # os.system("ffmpeg -i {audio_in} - ar 48000 {audio_out}")

    # stream = ffmpeg.input("test.wav")
    # audio = stream.audio
    # stream = ffmpeg.output(audio, "result.wav", **{'ar': '48000'})#, 'acodec': 'flac'})
    # ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)