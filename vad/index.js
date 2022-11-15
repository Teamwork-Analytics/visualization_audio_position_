const express = require("express");
const { spawn } = require("child_process");
const app = express();
const port = 3000;
app.get("/", (req, res) => {
  var dataToSend;
  // spawn new child process to call the python script
  const python = spawn("python", [
    "hive_automation.py",
    "-a",
    "small background noise, 25,17-25,24.wav",
    "-o",
    "console_output.csv",
    "-s",
    "test1",
    "-w",
    "1",
    "-t",
    "3",
  ]);
  // collect data from script
  python.stdout.on("data", function (data) {
    console.log("Pipe data from python script ...");
    dataToSend = data.toString();
  });
  // in close event we are sure that stream from child process is closed
  python.on("close", (code) => {
    console.log(`child process close all stdio with code ${code}`);
    // send data to browser
    res.status(200).send(dataToSend);
  });
});
app.listen(port, () =>
  console.log(`Example app listening on port 
${port}!`)
);

// hive_automation.py -a "Rio/small background noise, 25,17-25,24.wav" -o console_output.csv -s test1 -w 1 -t 3
