import argparse
import os
import signal
import socket
import stat
import sys
import time


def _pid_exists(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _wait_for_socket(path):
    for attempt in range(10):
        try:
            mode = os.stat(path).st_mode
        except FileNotFoundError:
            time.sleep(1)
            continue
        if not stat.S_ISSOCK(mode):
            raise AttributeError("Found process communication file, but it is not a Unix Domain Socket")


def _attach_to(pid):
    if not _pid_exists(pid):
        print(f'Could not find process with PID {pid}, aborting.')
        return False

    _unix_socket_path = os.path.join(f'/tmp/{pid}-debug-socket')
    _debugger_enabled_filename = os.path.join(f'/tmp/{pid}.dbg-enabled')

    # The UNIX domain socket file does not exist, this is either to the
    # debugger not being enabled in the process (wrong PID?), due to a bug
    # causing the debugger not to start, or due to the debugger being run
    # in a "run always" mode, so we need to trigger it with a signal:

    try:
        os.stat(_unix_socket_path)
    except FileNotFoundError:
        if not os.path.isfile(_debugger_enabled_filename):
            print (f'No debugger available for PID {pid}. Aborting.')
            return False

        # The file is there, no just need to trigger the debugger:
        os.kill(pid, signal.SIGINT)

    print(f'Trying to attach to process with PID {pid}...')

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        _wait_for_socket(_unix_socket_path)
        sock.connect(_unix_socket_path)

        received = str(sock.recv(4096), "utf-8")

        while received:
            print(received)

            data = input()
            sock.sendall(bytes(data + "\n", "utf-8"))
            received = str(sock.recv(4096), "utf-8")

    print('Debugger terminated.')


def _check_non_negative_int(value):
    if not value.isdigit():
        raise argparse.ArgumentTypeError(f'{value} is an illegal value for pid')
    return int(value)


def _get_pid():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('pid', help='the PID of the process to attach to', type=_check_non_negative_int)
    args = parser.parse_args()

    return args.pid


def main():
    pid = _get_pid()
    return _attach_to(_get_pid())


if __name__ == '__main__':
    sys.exit(main())
