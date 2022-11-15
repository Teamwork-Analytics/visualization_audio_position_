Here is how the script being called in the nodeJS script:

    const python = spawn('python', ['hive_automation.py', "-a", "small background noise, 25,17-25,24.wav", "-o", "console_output.csv", "-s", "test1", "-w", "1", "-t", "3"]);

There are five parameters to run the VAD script. Audio path(-a), csv output path(-o), session name that would be shown in the csv file(-s), word threshold(-w) controlling the strictness of VAD algorithm(it is described in the previous email, I think. 1 or 2 should be the best.), and the number of thread(-t) for accelerating the processing speed.

There is also some package used in the python interpreter. They are numpy, pydub, SpeechRecognition, webrtcvad, tqdm, pandas, and sklearn

## Steps

Please follow the steps below to clean, extract, and save the file

    1. Ensure that the audio file has sample rate 48KHz (the best)
    2. Run the converter
    3. `clean` folder is
    4.
