from functools import wraps
import os
import pathlib
import signal
import sys

from debug_server.server import UnixStreamDebugServer


_DEBUGGER_ENABLED_FILENAME = os.path.join('/tmp', f'{os.getpid()}.dbg-enabled')


"""
There are generally two modes of running the debugger:
1. Let the debugger start only after an unhandled exception: communicating with the debugger in this case is done via a
UNIX domain socket.
2. Let the debugger start at any time: communicating with the debugger in this case must be done through signals.
The debugger then defaults to the SIGINT signal for communication. The debugger attaches a new signal handler to
whatever signal handlers that may exist for the chosen signal, such that the debugger signal handler takes precedence.
"""

def _add_handler(signum, handler):
    """Gets a UNIX signal number 'signum' and a signal handler method which gets a (signum, frame) params.
    Adds the 'handler' function as a signal handler for 'signum', such that if 'signum' already has a signal handler,
    this signal handler will still be performed, only after 'handler' is finished.

    This is used as a helper function to add the debugger's signal handler without harming code which has a specialized
    handler for 'signum'.
    """
    current_handler = signal.getsignal(signum)

    if current_handler == signal.Handlers.SIG_DFL:
        signal.signal(signum, handler)
        return

    @wraps(current_handler)
    def new_signal_handler(signum, frame):
        handler(signum, frame)
        current_handler(signum, frame)

    signal.signal(signum, new_signal_handler)


class GlobalDebugger:
    def __init__(self, run_always=False, signum=signal.SIGINT):
        self._run_always = run_always
        self._signum = signum

        # Server creation time is decided based on the value of 'run_always':
        self._debug_server = None

    def _create_server(self):
        self._debug_server = UnixStreamDebugServer(signum=self._signum)

    def _global_exception_hook(self, exctype, value, traceback):
        if not self._debug_server:
            self._create_server()
        self._debug_server.handle_request(traceback=traceback)

    def _patch_global_exception_hook(self):
        sys.excepthook = self._global_exception_hook

    def _debugger_handler(self, signum, frame):
        self._create_server()
        self._debug_server.handle_request(frame=frame)

    def _patch_signal_handler(self):
        _add_handler(self._signum, self._debugger_handler)

    def _create_debugger_enabled_file(self):
        pathlib.Path(_DEBUGGER_ENABLED_FILENAME).touch()

    def start(self):
        if self._run_always:
            self._create_debugger_enabled_file()
            self._patch_signal_handler()
        self._patch_global_exception_hook()

    def __del__(self):
        if os.path.exists(_DEBUGGER_ENABLED_FILENAME):
            os.unlink(_DEBUGGER_ENABLED_FILENAME)


def interact(run_always=False):
    global_debugger = GlobalDebugger(run_always=run_always)
    global_debugger.start()

