# ( ͡° ͜ʖ ͡°)

import time
from webbrowser import open as open_url
from valveexe import ValveExe
from valveexe.logfile import RegexLogWatcher

# you can easily change these for another source game
game = ValveExe(
    gameExe="C:\\Program Files (x86)\\Steam\\steamapps\\common\\Team Fortress 2\\tf_win64.exe",
    gameDir="C:\\Program Files (x86)\\Steam\\steamapps\\common\\Team Fortress 2\\tf")
open_url("steam://run/440") # run TF2 through steam
game.run("con_logfile", game.logName) # makes sure that the game writes to the logfile

yourname = "auto lenny on kill using CODE!" # replace with your name ingame

killwatcher = RegexLogWatcher(
    game.logFile,
    yourname + r" killed .+ with (\w+)\.\n",
    lambda: (False, game.run("lenny"))[0], # assuming that you already have a console alias named lenny
    join=False, daemon=False)
killwatcher.start()
try:
    print(
        "Now watching for kills!\n"+
        "Press the interrupt key to stop (e.g., Ctrl+C or equivalent).")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    killwatcher.stop()
