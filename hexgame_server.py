#!/usr/bin/python3

"""
This module implements an Hex game server, which is based
on the hexgame.py game engine, and communicates with clients
using sockets.
"""


import asyncio
import random
import sys
import hexgame

DEFAULT_HEXSIZE = 11
HOST = '127.0.0.1'
PORT = 8888
TIMEOUT = None  # Change this if you want to add a timeout to each move


@asyncio.coroutine
def waiting_for_players(reader, writer, readers, writers, hexsize):
    """This coroutine waits for entering connections from players."""
    addr = writer.get_extra_info('peername')
    if len(writers) >= 2:
        writer.write(
            "TooManyPlayers".encode())
        yield from writer.drain()
        writer.close()
    else:
        writers.append(writer)
        readers.append(reader)
        print("New player connected with peername {}".format(addr))
        sys.stdout.flush()
        if len(writers) == 2:
            yield from handle_game(readers, writers, hexsize)


@asyncio.coroutine
def handle_game(readers, writers, hexsize):
    """This coroutine implements the main game and communication logic."""
    # We randomize the first player to start
    random_bool = int(random.randrange(2))
    players = {hexgame.BLUE: random_bool, hexgame.RED: 1 - random_bool}
    print("Starting game: {} # player 1 / {} # player 2".format(
        writers[random_bool].get_extra_info('peername'),
        writers[1 - random_bool].get_extra_info('peername')))
    sys.stdout.flush()
    hexboard = hexgame.Hex(hexsize)
    for writer in writers:
        writer.write("Start {}\n".format(hexboard.serialize()).encode())
        yield from writer.drain()
    while not hexboard.winner:
        writers[players[hexboard.current]].write(
            "Play {}\n".format(hexboard.serialize()).encode())
        yield from writers[players[hexboard.current]].drain()
        try:
            data = yield from asyncio.wait_for(
                readers[players[hexboard.current]].readline(), timeout=TIMEOUT)
        except asyncio.TimeoutError:
            print("Timeout for winner {}!".format(hexboard.current))
            hexboard.winner = (
                hexgame.RED
                if hexboard.current == hexgame.BLUE
                else hexgame.BLUE)
        if not hexboard.winner:
            move = [int(i) for i in data.decode().split('#')]
            print("Move {} received".format(move))
            sys.stdout.flush()
            try:
                hexboard.play(*move)
                writers[1 - players[hexboard.current]].write(
                    "Ack {}\n".format(hexboard.serialize()).encode())
                yield from writers[1 - players[hexboard.current]].drain()
            except hexgame.InvalidMoveException:
                writers[players[hexboard.current]].write(
                    "InvalidMove\n".encode())
                yield from writers[players[hexboard.current]].drain()

    for writer in writers:
        writer.write("End {}\n".format(hexboard.serialize()).encode())
        yield from writer.drain()
        writer.close()
    print("Player {} wins. Ending the game"
          .format(hexboard.winner))
    sys.stdout.flush()
    writers, readers = [], []
    asyncio.get_event_loop().stop()


def main():
    """
    Starts the server, waits for connections, plays the game,
    and shuts down gracefully.
    """
    hexsize = DEFAULT_HEXSIZE
    if len(sys.argv) > 1:
        hexsize = int(sys.argv[1])
    readers, writers = [], []
    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(
        lambda reader, writer: waiting_for_players(
            reader, writer, readers, writers, hexsize),
        HOST, PORT,
        loop=loop)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    print('Serving on {}'.format(server.sockets[0].getsockname()))
    print('Hit Ctrl+C to exit')
    print('-' * 60)
    print('Waiting for first player to connect...')
    sys.stdout.flush()
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    print('Closing the server')
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()


if __name__ == '__main__':
    main()
