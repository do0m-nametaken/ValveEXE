from re import search as regexsearch
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from os.path import dirname, abspath

class LogFile:
    '''
    Initialize a console logfile to track.
    '''
    def __init__(self, file_path):
        '''
        :param file_path: The path to the log file
        :type file_path: path, str
         '''
        self.file_path = file_path
        self.logs = ""  #: :type: (str) - all the logs accumulated so far
        self._bookmark = 0

    def ingest(self):
        '''
        Will resume reading the logs from where it last left off until the end
        and return all logs since.

        :rtype: str
        '''
        logs_since_bookmark = ""
        with open(self.file_path, mode="r") as file:
            file.seek(self._bookmark, 0)
            for line in file.readlines():
                self.logs += line
                logs_since_bookmark += line
                self._bookmark = file.tell()
        return logs_since_bookmark

class LogWatch():
    '''
    An abstract class that can automatically detect changes in a LogFile.
    Does nothing on its own. 
    '''
    def __init__(self, logfile):
        '''
        :param logfile: The LogFile to watch
        :type logfile: LogFile
        '''
        self.logfile = logfile
        self._event_handler = FileSystemEventHandler()

    def start(self):
        '''
        Start watching the LogFile.
        '''
        self._observer = Observer()
        self._observer.daemon = True
        self._observer.schedule(
            self._event_handler,
            dirname(self.logfile.file_path),
            recursive=False)
        self._observer.start()

    def stop(self):
        '''
        Stop watching the LogFile.
        '''
        self._observer.stop()
        del self._observer

class RegexLogWatch(LogWatch):
    '''
    Log Watcher that will :any:`ingest()<ingest>` whenever the LogFile is
    modified and will execute the specified callback if a specified regex
    is found within the logfile.
    '''
    def __init__(self, logfile, regex, callback=None, *callback_args):
        '''
        :param logfile: The LogFile to watch
        :type logfile: LogFile
        :param regex: A regex string to match against the logs
        :type regex: str
        :param callback: The function to run on a successfui regex match
        :type callback: function
        :param *callback_args: The arguments to pass to the callback
        function
        '''
        super().__init__(logfile)
        self.regex = regex
        self.callback = callback
        self.callback_args = []
        for arg in callback_args:
            self.callback_args.append(arg)
        self._event_handler.on_modified = self._on_modified

    def _on_modified(self, event):
        if (
                not event.is_directory and
                abspath(event.src_path) == abspath(self.logfile.file_path) and
                regexsearch(self.regex, self.logfile.ingest()) and
                self.callback is not None and callable(self.callback)):
            self.callback(*self.callback_args)
        else:
            pass
