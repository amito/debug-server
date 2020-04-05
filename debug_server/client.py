import argparse
import os
import signal
import socket
import stat
import sys


def _pid_exists(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _is_socket(path):
    try:
        mode = os.stat(path).st_mode
    except FileNotFoundError:
        # Basically, this check suffices... if the socket doesn't exist we'll
        # get here, and it's a good enough condition to trigger its creation
        # via the signal:
        return False
    # If we return False here, something really strange is happening - the file
    # is there, but it's not a socket...
    return stat.S_ISSOCK(mode)


def _attach_to(pid):
    if not _pid_exists(pid):
        print(f'Could not find process with PID {pid}, aborting.')
        return False

    _unix_socket_path = os.path.join(f'/tmp/{pid}-debug-socket')

    # The UNIX domain socket file does not exist, this is either to the
    # debugger not being enabled in the process (wrong PID?), due to a bug
    # causing the debugger not to start, or due to the debugger being run
    # in a "run always" mode, so we need to trigger it with a signal:
    # os.kill(pid, signal.SIGUSR1)

    print(f'Trying to attach to process with PID {pid}...')

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        # Connect to server and send data
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
