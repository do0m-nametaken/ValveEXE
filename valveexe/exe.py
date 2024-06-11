import os
import uuid
import time
import subprocess
import psutil
import glob

from rcon import Client

from valveexe.utils import find_process, terminate_process
from valveexe.logfile import LogFile, RegexLogWatcher
from valveexe.console import RconConsole, ExecConsole

PATTERNS = {
    "name_command": r'\"name\" = \"(?P<client_name>[^"]*)\"',
    "player_kill": r"(?P<subject>.+) killed (?P<victim>.+) with (?P<weapon>\w+)"
}

class ValveExe(object):
    def __init__(self, gameExe, gameDir, steamExe=None, appid=None):
        """Defines a launchable source engine game to be interacted with.

        .. note:: Some games cannot be launched by their .exe alone \
        (ex:csgo, probably for anti-cheat related reasons). \
        Those games need to include the optional parameters :any:`steamExe` \
        and :any:`appid`. Those parameters are only to be used if \
        absolutely needed, they are a fallback and will downgrade ValveEXE \
        functionnality if present.

        :param gameExe: the path for the game executable.
        :type gameExe: path, str
        :param gameDir: The mod directory.
        :type gameDir: path, str
        :param steamExe: The path for the Steam executable.
        :type steamExe: optional, path, str
        :param appid: The `Steam AppID
            <https://developer.valvesoftware.com/wiki/Steam_Application_IDs>`_.
        :type appid: optional, int
        """

        self.gameExe = gameExe
        self.gameDir = gameDir
        self.exeName = self.gameExe.split('\\')[-1]  #: :type: (str) - only the filename of `gameExe`

        self.appid = appid
        self.steamExe = steamExe

        self.uuid = str(uuid.uuid4()).split('-')[-1]

        self.logName = f'valve-exe-{self.uuid}.log'
        self.logPath = os.path.join(gameDir, self.logName)
        self.logFile = LogFile(self.logPath, True) #: :type: (LogFile) - the logfile that the game is writing to

        self.console = None

        self.rcon_enabled = None
        self.hijacked = None

        # returns a process if game is already running, None if else
        self.process = find_process(self.exeName)

        self._full_cleanup()

    def launch(self, *params):
        """Launches the game as specified in :any:`__init__` with the
        launch parameters supplied as arguments.

        :param \*params: The launch parameters to be supplied to the executable.
        :type \*params: str
        """

        # if the game is already running,
        # just makes it sure that it writes to the logfile
        if self.process:
            self.run("con_logfile", self.logName)
            return

        if self.steamExe and self.appid:
            # Steam launches cannot be hijacked
            terminate_process(self.exeName)
            launch_params = [self.steamExe, '-applaunch', str(self.appid)]
        else:
            self.hijacked = bool(self.process)
            launch_params = [self.gameExe, '-hijack']

        launch_params.extend(['-game', self.gameDir])
        launch_params.extend(['+log', '0', '+sv_logflush', '1',
                              '+con_logfile', self.logName])

        if self._check_rcon_eligible():
            launch_params.extend(['-usercon', '+ip', '0.0.0.0',
                                  '+rcon_password', self.uuid])

        launch_params.extend([*params])
        self.process = subprocess.Popen(
            launch_params,
            creationflags=subprocess.DETACHED_PROCESS |
            subprocess.CREATE_NEW_PROCESS_GROUP)

        while not os.path.exists(self.logPath):
            time.sleep(3)

    def run(self, command, *params):
        """Forwards a command with its parameters to the active :any:`VConsole`

        :param command: A Source Engine `console command \
        <https://developer.valvesoftware.com/wiki/Console_Command_List>`_.
        :type command: str
        :param \*params: The values to be included with the command.
        :type \*params: str
        """
        if not self.process:
            return
        if self.console:
            self.console.run(command, *params)
        else:
            with self as console:
                console.run(command, *params)

    def quit(self):
        """Closes the game client"""
        self.run(
            # stop writing to the logfile in order for the
            # LogFile object to delete it upon its destruction.
            "con_logfile", '""')
        process = self.process or find_process(self.exeName)
        if process:
            process.terminate()
        self.process = None

    def _check_rcon_eligible(self):
        """
        None: Unknown
        True: Eligible
        False: Not eligible
        """
        if self.process is not None:
            process = psutil.Process(self.process.pid)
            if '-usercon' not in process.cmdline():
                # doesn't have rcon enabled
                return False
            else:
                # 'connections' confirms game is listening for rcon
                return bool(process.connections())
        else:
            # no process running
            return None

    def __enter__(self):
        while self._check_rcon_eligible() is None:
            time.sleep(3)

        if self._check_rcon_eligible():
            self.console = RconConsole("127.0.0.1", 27015, self.uuid)
        else:
            self.console = ExecConsole(self.gameExe, self.gameDir, self.uuid)

        self.console.__enter__()
        return self.console

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.console.__exit__(exc_type, exc_val, exc_tb)
        self.console = None

    def __del__(self):
        try:
            self.run('con_logfile', '""')
        except:
            pass

    def _full_cleanup(self):
        for f in glob.glob(self.gameDir + 'valve-exe-*.log'):
            try:
                os.remove(f)
            except:
                pass

# COMING SOON!

#class Server:
#    """Represents a server the that a ValveExe client is connected to."""
#    def __init(self, exe, poll_info_on='client connection'):
#        self.exe = exe
#        self.poll_info_on = poll_info_on
#        if self.poll_info_on == 'client connection':
#            self.info_poller = RegexLogWatcher