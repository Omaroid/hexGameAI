#!/usr/bin/python3

"""
This module implements a basic graphical client
for the Hex board game.
"""


import asyncio
import sys
import hexgui
import hexgame
import random

from random import randint

INIT_STATE, START, PLAYING, WAITING_FOR_ACK,\
    WAITING_FOR_ADVERSARY_MOVE, END_STATE, CONNECTION_REFUSED = range(7)
HOST = '127.0.0.1'
PORT = 8888

@asyncio.coroutine
def send_message_callback(writer, row, col, state):
    """A callback that sends the move to the server and waits for ack."""
    writer.write("{}#{}\n".format(row, col).encode())
    yield from writer.drain()
    state[0] = WAITING_FOR_ACK

def game_client(loop, state):
    """The main client logic, based on a state machine."""
    reader, writer = yield from asyncio.open_connection(HOST, PORT, loop=loop)
    print("Connected to the game server")
    sys.stdout.flush()
    state[0] = INIT_STATE
    while state[0] not in (END_STATE, CONNECTION_REFUSED):
        if state[0] == INIT_STATE:
            data = yield from reader.readline()
            message = data.decode()
            if message.startswith("Start"):
                print(message)
                hexboard = hexgame.Hex.create_from_str(message[6:])
                hexgui.init_screen()
                hexgui.redraw(hexboard)
                state[0] = START
            if message.startswith("TooManyPlayers"):
                print(message)
                state[0] = CONNECTION_REFUSED
        if state[0] in [START, WAITING_FOR_ADVERSARY_MOVE]:
            data = yield from reader.readline()
            message = data.decode()
            if message.startswith("Play"):
                state[0] = PLAYING
                hexboard = hexgame.Hex.create_from_str(message[5:])
                hexgui.redraw(hexboard)
                hexgui.set_title("hexgui.Hex game - your turn")
                print(message)
            if message.startswith("End"):
                state[0] = END_STATE
                hexgui.set_title("Hex game - end of game")
                hexboard = hexgame.Hex.create_from_str(message[4:])
                hexgui.redraw(hexboard)
                print(message)
        if state[0] == PLAYING:
            stop_loop = False
            row, col = None, None
            _list=[]
            for i in range(hexboard.size):
                for j in range(hexboard.size):
                    if not hexboard.grid[i][j]:
                        _list.append([i,j])
            elt=random.choice(_list)
            row=elt[0]
            col=elt[1]
            yield from send_message_callback(writer, row, col, state)
        if state[0] == WAITING_FOR_ACK:
            data = yield from reader.readline()
            message = data.decode()
            if message.startswith("Ack"):
                print(message)
                hexboard = hexgame.Hex.create_from_str(message[4:])
                hexgui.redraw(hexboard)
                state[0] = WAITING_FOR_ADVERSARY_MOVE
                hexgui.set_title("Hex game - waiting for adversary move")
            if message.startswith("InvalidMove"):
                print(message)
                state[0] = PLAYING
        sys.stdout.flush()
    if state[0] == END_STATE:
        print("{} wins the game".format(hexgui.player_names[hexboard.winner]))
    writer.close()

def main():
    """Runs the graphical client."""
    loop = asyncio.get_event_loop()
    state = [None]
    loop.run_until_complete(game_client(loop, state))
    if state[0] != CONNECTION_REFUSED:
        loop.run_until_complete(hexgui.handle_events(hex, None))
        hexgui.teardown_screen()
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()


if __name__ == '__main__':
    main()
