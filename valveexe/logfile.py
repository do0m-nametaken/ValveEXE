from collections.abc import Iterable
from inspect import getdoc
from re import search as regexsearch
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from os.path import dirname, abspath, isfile

class LogFile:
    '''
    Initialize a console logfile to track by leveraging the con_logfile
    command. Supported in most source games (except L4D2).
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

class LogWatcher():
    '''
    An abstract class that can automatically detect changes in a
    :any:`LogFile<LogFile()>` and can then call the appropriate event methods
    that you can override from.
    '''

    def __init__(self, logfile, iters=1, daemon=True, join=False):
        '''
        :param logfile: The :any:`LogFile<LogFile()>` to watch
        :type logfile: LogFile

        :param iters: Specifies how many consecutive "successful events" until
            stopping. This means that those methods need to return True to get
            a successful event in order to automatically :any:`stop()`.
        :type iters: positive, int

        :param daemon: Determines whether to use a `daemonic thread
            <https://docs.python.org/3/librar   y/threading.html#:~:text=a%20th
            read%20can%20be%20flagged%20as%20a%20%E2%80%9Cdaemon%20thread%E2%80
            %9D.%20the%20significance%20of%20this%20flag%20is%20that%20the%20en
            tire%20python%20program%20exits%20when%20only%20daemon%20threads%20
            are%20left.>`_.
            Set to False if you don't want to let the main program exit
            without letting the :any:`LogWatcher` stop first.
        :type daemon: bool

        :param join: Determines whether to call :meth:`~threading.Thread.join`
            when starting. Set to True if you want to block/pause further
            execution once starting until the :any:`LogWatcher` has stopped.
        :type join: bool
        '''
        self.logfile = logfile
        self.iters = iters
        self.daemon = daemon
        self.join = join
        self._started = False
        self._event_handler = FileSystemEventHandler()
        self._event_handler.on_any_event = self.on_any_event

    def start(self):
        '''
        Start watching the :any:`LogFile<LogFile()>`.
        '''
        self._successful_events = 0
        self._observer = Observer()
        self._observer.daemon = self.daemon
        self._observer.schedule(
            self._event_handler,
            dirname(self.logfile.file_path),
            recursive=False)
        self._observer.start()
        self._started = True
        if self.join: self._observer.join()

    def stop(self):
        '''
        Stop watching the :any:`LogFile<LogFile()>`.
        '''
        if self._started:
            self._observer.stop()
            del self._observer
            del self._successful_events
            self._started = False
        else:
            # already stopped
            pass

    def on_any_event(self, event):
        """Catch-all event handler. After calling the appropriate event method,
        it will call :any:`stop()` if the amount of successful events
        internally counted reaches the :attr:`iters` parameter.

        :param event:
            The event object representing the file system event.
        :type event:
            :class:`FileSystemEvent`
        """
        if (
                not event.is_directory and
                abspath(event.src_path) == abspath(self.logfile.file_path)
            ):
            match event.event_type:
                case 'modified':
                    if self.on_modified(event.src_path):
                        self._successful_events += 1
                case 'created':
                    if self.on_created(event.src_path):
                        self._successful_events += 1
                case 'deleted':
                    if self.on_deleted(event.src_path):
                        self._successful_events += 1
                case 'closed':
                    if self.on_closed(event.src_path):
                        self._successful_events += 1
                case 'moved':
                    if self.on_moved(event.src_path):
                        self._successful_events += 1
            if self._successful_events >= self.iters:
                self.stop()
            else:
                pass

    def on_moved(self, event):
        """
        Called by :any:`on_any_event()` when the logfile is moved or renamed.

        :param event:
            Event representing file/directory movement.
        :type event:
            :class:`DirMovedEvent` or :class:`FileMovedEvent`

        :return: Whether or not the call was a successful event.
            :any:`True` by default.
        :rtype: bool
        """
        return True

    def on_created(self, event):
        """
        Called by :any:`on_any_event()` when the logfile is created.

        :param event:
            Event representing file/directory creation.
        :type event:
            :class:`DirCreatedEvent` or :class:`FileCreatedEvent`
        
        :return: Whether or not the call was a successful event.
            :any:`True` by default.
        :rtype: bool
        """
        return True

    def on_deleted(self, event):
        """
        Called by :any:`on_any_event()` when the logfile is deleted.

        :param event:
            Event representing file/directory deletion.
        :type event:
            :class:`DirDeletedEvent` or :class:`FileDeletedEvent`
        
        :return: Whether or not the call was a successful event.
            :any:`True` by default.
        :rtype: bool
        """
        return True

    def on_modified(self, event):
        """
        Called by :any:`on_any_event()` when the logfile is modified.

        :param event:
            Event representing file/directory modification.
        :type event:
            :class:`DirModifiedEvent` or :class:`FileModifiedEvent`
        
        :return: Whether or not the call was a successful event.
            :any:`True` by default.
        :rtype: bool
        """
        return True

    def on_closed(self, event):
        """
        Called by :any:`on_any_event()` when the logfile opened for writing
        is closed.

        :param event:
            Event representing file closing.
        :type event:
            :class:`FileClosedEvent`
        
        :return: Whether or not the call was a successful event.
            :any:`True` by default.
        :rtype: bool
        """


class RegexLogWatcher(LogWatcher):
    '''
    Log Watcher that will :any:`ingest()` whenever the
    :any:`LogFile<LogFile()>` is modified and will execute the specified
    callback if a specified regex is found within the
    :any:`LogFile<LogFile()>`'s recent/:any:`ingested<ingest()>` output.

    This class inherits the parameters and default arguments from
    :any:`LogWatcher`.
    '''

    def __init__(
            self, logfile, regex, callback,
            args=[], kwargs=dict(), iters=1, daemon=True, join=False
        ):
        '''
        :param regex: A regex string to match against the logs
        :type regex: str

        :param callback: The function to call on a successful regex match
        :type callback: ~collections.abc.Callable

        :param args: The arguments to pass to the callback function in the form
            of an iterable
        :type args: ~collections.abc.Iterable

        :param kwargs: The keyword arguments to pass to the callback function
            in the form of a mapping/dictionary
        :type kwargs: dict
        '''
        super().__init__(logfile, iters, daemon, join)
        self.regex = regex
        self.callback = callback
        if not isinstance(args, Iterable):
            raise TypeError("args must be an iterable.")
        else: self.args = args
        if not isinstance(kwargs, dict):
            raise TypeError("kwargs must be a mapping.")
        else: self.kwargs = kwargs

    def on_modified(self, event):
        print("logmod")
        if (
                regexsearch(self.regex, self.logfile.ingest()) and
                self.callback is not None and callable(self.callback)
            ):
            print("callback")
            return self.callback(*self.args, **self.kwargs)
        else:
            return False