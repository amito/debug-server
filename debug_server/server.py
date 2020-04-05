import errno
import os
import socketserver

try:
    import ipdb as pdb
except ImportError:
    import pdb


class StreamDebugServerHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self.server._client_connected = True

        wfile = self.request.makefile('w', buffering=None, encoding='utf-8')
        rfile = self.request.makefile('r', buffering=None, encoding='utf-8')

        self.server._start_pdb(stdout=wfile, stdin=rfile)

        self.request.close()


class TCPDebugServer(socketserver.TCPServer):
    def __init__(self, bind_port, local):
        """@param bind_port: the port the server should bind to.
           @param local: whether the server should bind to localhost or to 0.0.0.0
        """
        self.allow_reuse_address = True

        self._bind_port = bind_port
        self._bind_host = '127.0.0.1' if local else '0.0.0.0'
        socketserver.TCPServer.__init__(self, (self._bind_host, self._bind_port), StreamDebugServerHandler)

        self._client_connected = False

    def verify_request(self, request, client_address):
        return not self._client_connected


class UnixStreamDebugServer(socketserver.UnixStreamServer):
    def __init__(self, signum):
        self._signum = signum
        self._server_address = os.path.join('/tmp', f'{os.getpid()}-debug-socket')
        socketserver.UnixStreamServer.__init__(self, self._server_address, StreamDebugServerHandler)

    def _start_pdb(self, stdout, stdin):
        debugger = pdb.Pdb(stdout=stdout, stdin=stdin, nosigint=True)
        debugger.botframe = self._frame
        debugger.interaction(self._frame, self._traceback)

    def handle_request(self, frame=None, traceback=None):
        self._frame = frame
        self._traceback = traceback
        try:
            socketserver.UnixStreamServer.handle_request(self)
        finally:
            os.unlink(self._server_address)

