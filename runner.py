#!/usr/bin/env python3

"""
This module is intended to run batches of games between clients.
It uses three subprocesses for each game: one for the server, and
two for the clients. Synchronization ensures that the games are
run sequentially (not in parallel).
"""


from subprocess import Popen, PIPE, STDOUT
import threading
import sys
import argparse
import logging


SERVER_PATH = './hexgame_server.py'
CLIENT1 = './random_client.py'
CLIENT2 = './random_client.py'
LOG_LEVEL = logging.INFO
LOG_FILE = None


def run_server(server_evt, winners, hexsize=11):
    """Runs the server as a subprocess."""
    winning_client = None
    with Popen([SERVER_PATH, str(hexsize)], stdout=PIPE) as proc:
        client_peernames = []
        while proc.poll() is None:
            line = proc.stdout.readline().decode()
            logging.debug("[Server] %s", line.rstrip())
            if line.startswith('Waiting'):
                server_evt.set()
                logging.info('Connected')
            if line.startswith('New player connected'):
                client_peernames.append(line[35:].rstrip())
                logging.info('Peernames %s', ' / '.join(client_peernames))
            if line.startswith('Starting game'):
                players = [s.split('#')[0].strip()
                           for s in line[15:].split('/')]
                logging.info('Player 1 → %s / Player 2 → %s',
                             players[0], players[1])
            if line.startswith('Player'):
                winner = players[int(line[7]) - 1]
                winning_client = client_peernames.index(winner)
                logging.info(
                    'The winner is %s (client %s)', winner,
                    winning_client)
                winners[winning_client] += 1
            sys.stdout.flush()


def run_client(server_evt, client_evt, client, num):
    """Runs a client as a subprocess."""
    if num == 1:
        server_evt.wait()
    else:
        client_evt.wait()
    connection_success = False
    attempts = 10
    while not connection_success and attempts:
        with Popen([client], stdout=PIPE, stderr=STDOUT) as proc:
            while proc.poll() is None:
                out = proc.stdout.readline().decode()
                if out.startswith('ConnectionRefusedError'):
                    connection_success = False
                if out.startswith('Connected'):
                    connection_success = True
                    client_evt.set()
                    logging.debug("[Client {}] ".format(num) + out.rstrip())
                sys.stdout.flush()
            attempts -= 1
    sys.stdout.flush()


def main():
    """Runs a batch of games."""
    if LOG_FILE:
        logging.basicConfig(level=LOG_LEVEL,
                            filename=LOG_FILE)
    else:
        logging.basicConfig(level=LOG_LEVEL)
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch', nargs=1, default=[1], type=int)
    parser.add_argument('--hexsize', nargs=1, default=[11], type=int)
    arguments = vars(parser.parse_args(sys.argv[1:]))
    server_evt, client_evt = threading.Event(), threading.Event()

    winners = [0, 0]
    for batch_number in range(arguments['batch'][0]):
        logging.info("### Game number %d", batch_number + 1)
        t_server = threading.Thread(target=run_server,
                                    args=(server_evt,
                                          winners,
                                          arguments['hexsize'][0]))
        t_client1 = threading.Thread(target=run_client, args=(server_evt,
                                                              client_evt,
                                                              CLIENT1, 1))
        t_client2 = threading.Thread(target=run_client, args=(server_evt,
                                                              client_evt,
                                                              CLIENT2, 2))
        t_server.start()
        t_client1.start()
        t_client2.start()
        t_server.join()

    print('Winners {}'.format(str(winners)))


if __name__ == '__main__':
    main()
