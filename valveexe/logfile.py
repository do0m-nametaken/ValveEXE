from re import search as regexsearch
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from os.path import dirname, abspath

class LogFile:
    def __init__(self, file_path):
        self.file_path = file_path
        self.logs = ""
        self._bookmark = 0
        self.watchers = []

    def ingest(self):
        '''
        Will resume reading the logs from where it last left off until the end
        and return all logs since

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
    def __init__(self, logfile):
        self.logfile = logfile
        self._event_handler = FileSystemEventHandler()

    def start(self):
        self.logfile.watchers.append(self)
        self._observer = Observer()
        self._observer.daemon = True
        self._observer.schedule(self._event_handler, dirname(self.logfile.file_path), recursive=False)
        self._observer.start()

    def stop(self):
        self.logfile.watchers.remove(self)
        self._observer.stop()
        del self._observer

class RegexLogWatch(LogWatch):
    def __init__(self, logfile, regex, function=None, *function_args):
        super().__init__(logfile)
        self.regex = regex
        self.function = function
        self.function_args = []
        for arg in function_args:
            self.function_args.append(arg)
        self._event_handler.on_modified = self._on_modified

    def _on_modified(self, event):
        if (
                not event.is_directory and
                abspath(event.src_path) == abspath(self.logfile.file_path) and
                regexsearch(self.regex, self.logfile.ingest()) and
                self.function is not None and callable(self.function)
            ):
            self.function(*self.function_args)
        else:
            pass
