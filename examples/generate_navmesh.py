import psutil
from valveexe import ValveExe
from valveexe.logfile import RegexLogWatcher

tf2 = ValveExe(
	"C:\\Program Files (x86)\\Steam\\steamapps\\common\\Team Fortress 2\\tf_win64.exe", # exe path
	"C:\\Program Files (x86)\\Steam\\steamapps\\common\\Team Fortress 2\\tf") # mod dir
tf2.launch("-windowed", "-novid",
	# this will not work if you already have the
	# game configured to load into a map at launch
	# either by your custom mods or config files.
	# (background maps also apply)
	"+map", "ctf_2fort",
	# for some reason i'm not able to load into a map in TF2 without steam running
	# i assume this is because of the new 64-bit update but i could be wrong
	# sadly i can't check if this is also the case on other platforms and machines right now
	# - Do0m
	"-steam")

with RegexLogWatcher(tf2.logFile, f"Redownloading all lightmaps", lambda: True):
	print("Waiting for the game to load into the map...")

print("Game finished loading!")
tf2.run('nav_generate') # will run the command "nav_generate"
logwatcher = RegexLogWatcher(
	logfile=tf2.logFile, pattern="\.nav' saved\.",
	callback=lambda: (True, tf2.quit(), print("Done!"))[0], # automatically exit the game and stop watching the logs when the log matches the regex string
	daemon=False, # set to True if you want to let python exit without letting the logwatcher automatically stop first
	join=False, # set to True if you want to block/pause further execution once starting until the logwatcher has automatically stopped
	)
logwatcher.start()
print("Watching the logs...  (O  ) _ (O  )") # this will not execute immediately after logwatcher.start() if join was set to True
# if daemon was set to False, python will not exit until logwatcher has automatically stopped