from re import search as regexsearch
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from os.path import dirname, abspath, isfile

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
        if isfile(abspath(self.file_path)):
            self.ingest()

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

class LogWatch(FileSystemEventHandler):
    '''
    An abstract class that you can override methods from that can
    automatically detect changes in a :any:`LogFile()` and can then call
    aforementioned methods.

    When :any:`started<start()>` on its own with the default arguments, it
    watches the LogFile and executes the respective method according to the
    type of event (e.g. created, moved, etc.) And because those methods are,
    *by default*, set to be "successful events" (i.e. return a value of True),
    it then :any:`stops<stop()>`.
    '''

    def __init__(self, logfile, iters=1, daemonic=True, join=False):
        '''
        :param logfile: The LogFile to watch
        :type logfile: LogFile

        :param iters: Specifies how many consecutive "successful events" until
            stopping. This means that those methods need to return True to get
            a "successful event" in order to automatically stop the LogWatch
        :type iters: positive, int

        :param daemonic: Determines whether to use a `daemonic thread
            <https://docs.python.org/3/library/threading.html#:~:text=a%20threa
            d%20can%20be%20flagged%20as%20a%20%E2%80%9Cdaemon%20thread%E2%80%9D
            .%20the%20significance%20of%20this%20flag%20is%20that%20the%20entir
            e%20python%20program%20exits%20when%20only%20daemon%20threads%20are
            %20left.>`_
            . Set to False if you don't want to let the main program exit
            without letting the LogWatch stop first.
        :type daemonic: bool

        :param join: Determines whether to call :meth:`~threading.Thread.join`
            when starting. Set to True if you want block further execution
            until the LogWatch has stopped.
        :type join: bool
        '''
        self.logfile = logfile
        self.iters = iters
        self.daemonic = daemonic
        self.join = join
        self._started = False

    def on_any_event(self, event):
        if (
                not event.is_directory and
                abspath(event.src_path) == abspath(self.logfile.file_path)
            ):
            match event.event_type:
                case 'modified':
                    if self.on_modified(event.src_path): self._iters -= 1
                case 'created':
                    if self.on_created(event.src_path): self._iters -= 1
                case 'deleted':
                    if self.on_deleted(event.src_path): self._iters -= 1
                case 'closed':
                    if self.on_closed(event.src_path): self._iters -= 1
                case 'moved':
                    if self.on_moved(event.src_path): self._iters -= 1
            if self._iters == 0: self.stop()
            else: pass

    def on_modified(self, event):
        return True

    def on_created(self, event):
        return True

    def on_deleted(self, event):
        return True

    def on_closed(self, event):
        return True

    def on_moved(self, event):
        return True

    def start(self):
        '''
        Start watching the LogFile.
        '''
        self._iters = self.iters
        self._observer = Observer()
        self._observer.daemon = self.daemonic
        self._observer.schedule(
            self,
            dirname(self.logfile.file_path),
            recursive=False)
        self._observer.start()
        self._started = True

    def stop(self):
        '''
        Stop watching the LogFile.
        '''
        if self._started:
            self._observer.stop()
            del self._observer
            del self._iters
            self._started = False
        else:
            # already stopped
            pass


class RegexLogWatch(LogWatch):
    '''
    Log Watcher that will :any:`ingest()` whenever the LogFile is modified and
    will execute the specified callback if a specified regex is found within
    the logfile.

    This class inherits the parameters, methods, and, default arguments from
    :any:`LogWatch`.
    '''

    def __init__(
            self, logfile, regex, callback,
            iters=1, daemonic=True, join=False,
            *callback_args, **callback_kwargs
        ):
        '''
        :param regex: A regex string to match against the logs
        :type regex: str

        :param callback: The function to run on a successful regex match
        :type callback: function

        :param \*callback_args: The arguments to pass to the callback function

        :param \*\*callback_kwargs: The keyword arguments to pass to the
            callback function
        '''
        super().__init__(logfile, iters, daemonic, join)
        self.regex = regex
        self.callback = callback
        self.callback_args = callback_args
        self.callback_kwargs = callback_kwargs

    def on_modified(self, event):
        if (
                regexsearch(self.regex, self.logfile.ingest()) and
                self.callback is not None and callable(self.callback)
            ):
            return self.callback(*self.callback_args, **self.callback_kwargs)
        else:
            pass