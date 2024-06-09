from collections.abc import Iterable
from re import search as regexsearch
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
from os.path import dirname, abspath, isfile

class LogFile:
    """
    Initialize a console logfile to track by leveraging the con_logfile
    command. Supported in most source games (except L4D2).
    """
    def __init__(self, file_path):
        """
        :param file_path: The path to the log file
        :type file_path: path, str
        """
        self.file_path = file_path
        self.logs = ""  #: :type: (str) - all the logs accumulated so far
        self._bookmark = 0
        if isfile(abspath(self.file_path)):
            self.ingest()

    def ingest(self):
        """
        Will resume reading the logs from where it last left off until the end
        and return all logs since.

        :rtype: str
        """
        logs_since_bookmark = ""
        with open(self.file_path, mode="r") as file:
            file.seek(self._bookmark, 0)
            for line in file.readlines():
                self.logs += line
                logs_since_bookmark += line
                self._bookmark = file.tell()
        return logs_since_bookmark

class LogWatcher:
    """
    An abstract class that can automatically detect changes in a
    :any:`LogFile<LogFile()>` and can then call the appropriate event methods
    that you can override from.

    When used as a context manager, it :any:`starts<start()>`, runs the with
    block, then :meth:`joins()` and :any:`stops<stop()>` .
    """
    def __init__(
            self, logfile,
            polling_interval=0.5, iters=1, daemon=True, join=False):
        """
        :param logfile: The :any:`LogFile<LogFile()>` to watch
        :type logfile: LogFile

        :param polling_interval: interval in seconds between polling the
            logfile.
        :type polling_interval: float

        :param iters: Specifies how many consecutive "successful events" until
            :any:`stopping<stop()>`. The event methods should return True for a
            successful event in order to automatically :any:`stop()`.
        :type iters: positive, int

        :param daemon: Determines whether to use a `daemon thread
            <https://docs.python.org/3/library/threading.html#threading.Thread.
            daemon>`_.
            Set to :any:`False` if you don't want to let the main program exit
            without letting the :any:`LogWatcher` stop first.
        :type daemon: bool

        :param join: Determines whether to call `join()
            <https://docs.python.org/3/library/threading.html#threading.Thread.
            join>`_
            when starting. Set to :any:`True` if you want to block/pause
            further execution once starting until the :any:`LogWatcher` has
            stopped. This will be overridden if the :any:`LogWatcher` is used
            as a context manager as it will always `join()
            <https://docs.python.org/3/library/threading.html#threading.Thread.
            join>`_
            but only after executing the with block.
        :type join: bool
        """
        self.logfile = logfile
        self.polling_interval = polling_interval
        self.iters = iters
        self.daemon = daemon
        self.join = join
        self._in_context_manager = False
        self._started = False
        self._event_handler = FileSystemEventHandler()
        self._event_handler.on_any_event = self.on_any_event

    def start(self):
        """
        Start watching the :any:`LogFile<LogFile()>`.
        """
        if not self._started:
            # for some reason, WindowsApiObserver
            # does not work on logfiles, at least for me
            # so DON'T TAKE MY WORD FOR IT
            # because of that, we're using a PollingObserver instead
            # TODO: check if other observers can work on other platforms
            self._observer = PollingObserver(self.polling_interval)
            self._observer.daemon = self.daemon

            self._successful_events = 0 # counter
            self._observer.schedule(
                self._event_handler,
                dirname(self.logfile.file_path),
                recursive=False)
            self._observer.start()
            self._started = True
            if self.join and not self._in_context_manager:
                self._observer.join()
        else:
            # already started
            pass

    def stop(self):
        """
        Stop watching the :any:`LogFile<LogFile()>`.
        """
        if self._started:
            self._observer.stop()
            del self._observer
            del self._successful_events
            self._started = False
        else:
            # already stopped
            pass

    def on_any_event(self, event):
        """
        Catch-all event handler. After calling the appropriate event method, it
        will call :any:`stop()` if the amount of successful events internally
        counted reaches the :attr:`iters` parameter.

        :param event:
            The event object representing the file system event.
        :type event:
            :class:`FileSystemEvent`
        """
        if (
                not event.is_directory and
                abspath(event.src_path) == abspath(self.logfile.file_path)):
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

    def on_moved(self, event):
        """
        Called by :meth:`on_any_event()` when the logfile is moved or renamed.

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
        Called by :meth:`on_any_event()` when the logfile is created.

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
        Called by :meth:`on_any_event()` when the logfile is deleted.

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
        Called by :meth:`on_any_event()` when the logfile is modified.

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
        Called by :meth:`on_any_event()` when the logfile opened for writing
        is closed.

        :param event:
            Event representing file closing.
        :type event:
            :class:`FileClosedEvent`
        
        :return: Whether or not the call was a successful event.
            :any:`True` by default.
        :rtype: bool
        """
        return True

    def __enter__(self):
        self._in_context_manager = True
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._observer.join()
        self.stop()
        self._in_context_manager = False
        return False

    def __del__(self):
        if self._started:
            self.stop()

class RegexLogWatcher(LogWatcher):
    """
    Log Watcher that will :any:`ingest()` whenever the
    :any:`LogFile<LogFile()>` is modified and will execute the specified
    callback if a specified regex is found within the
    :any:`LogFile<LogFile()>`'s recent/:any:`ingested<ingest()>` output.

    This class inherits the parameters and default arguments from
    :any:`LogWatcher`.
    """
    def __init__(
            self, logfile, pattern, callback, args=[], kwargs=dict(),
            polling_interval=0.5, iters=1, daemon=True, join=False):
        """
        :param regex: A regex pattern string to match against the logs
        :type regex: str

        :param callback: The function to call on a successful regex match
        :type callback: ~collections.abc.Callable

        :param args: The arguments to pass to the callback function in the form
            of an :class:`iterable<collections.abc.Iterable>`
        :type args: ~collections.abc.Iterable

        :param kwargs: The keyword arguments to pass to the callback function
            in the form of a :class:`mapping/dictionary<dict>`
        :type kwargs: dict
        """
        super().__init__(logfile, polling_interval, iters, daemon, join)
        self.pattern = pattern
        self.callback = callback
        if not isinstance(args, Iterable):
            raise TypeError("args must be an iterable.")
        else:
            self.args = args
        if not isinstance(kwargs, dict):
            raise TypeError("kwargs must be a mapping.")
        else:
            self.kwargs = kwargs

    def on_modified(self, event):
        """:return: :any:`True` if regex match is found"""
        matches = bool(regexsearch(self.pattern, self.logfile.ingest()))
        if matches and callable(self.callback):
            return self.callback(*self.args, **self.kwargs)
        else:
            return False

    def on_created(self, event):
        """
        :return: **self.on_modified(event)** so that it still checks for a
            regex match if the logfile had just been created
        """
        return self.on_modified(event)
