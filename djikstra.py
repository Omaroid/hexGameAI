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
import math
from collections import defaultdict

INIT_STATE, START, PLAYING, WAITING_FOR_ACK,\
    WAITING_FOR_ADVERSARY_MOVE, END_STATE, CONNECTION_REFUSED = range(7)
HOST = '127.0.0.1'
PORT = 8888

EMPTY=0

class Graph():
    def __init__(self):
        self.edges = defaultdict(list)
        self.weights = {}

    def add_edge(self, from_node, to_node, weight):
        # Note: assumes edges are bi-directional
        self.edges[from_node].append(to_node)
        self.edges[to_node].append(from_node)
        self.weights[(from_node, to_node)] = weight
        self.weights[(to_node, from_node)] = weight

@asyncio.coroutine
def send_message_callback(writer, row, col, state):
    """A callback that sends the move to the server and waits for ack."""
    writer.write("{}#{}\n".format(row, col).encode())
    yield from writer.drain()
    state[0] = WAITING_FOR_ACK


@asyncio.coroutine
def game_client(loop, state):
    """The main client
                hexboard.current=2 logic, based on a state machine."""
    reader, writer = yield from asyncio.open_connection(HOST, PORT,
                                                        loop=loop)
    print("Connected to the game server")
    sys.stdout.flush()
    state[0] = INIT_STATE
    player=2
    init=0
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
                hexgui.set_title("Hex game - your turn")
                if init==0 and "1" not in message:
                    player=1
                    init=1
                print(message)
            if message.startswith("End"):
                state[0] = END_STATE
                hexgui.set_title("Hex game - end of game")
                hexboard = hexgame.Hex.create_from_str(message[4:])
                hexgui.redraw(hexboard)
                print(message)
        if state[0] == PLAYING:
            row, col = None, None
            graph = make_graph(hexboard.size, hexboard.grid, player)
            tab = find_best(hexboard.size, hexboard.grid, graph, player)
            row=tab[0]
            col=tab[1]
            yield from send_message_callback(writer,row, col,state)
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
        print("Joueur :"+str(player))
        print("{} wins the game".format(hexgui.player_names[hexboard.winner]))
    writer.close()


def make_graph(size, grid, current):
    graph= Graph()
    for i in range(size):
        for j in range(size):
            if grid[i][j]==current:

                f=""+str(i)+"#"+str(j)
                t=""+str(i-1)+"#"+str(j-1)
                if i>0 and j>0:
                    if grid[i-1][j-1]==current:
                        graph.add_edge(f,t,0)
                    else:
                        if grid[i-1][j-1]==EMPTY:
                            graph.add_edge(f,t,50)

                t=""+str(i)+"#"+str(j-1)
                if j>0:
                    if grid[i][j-1]==current:
                        graph.add_edge(f,t,0)
                    else:
                        if grid[i][j-1]==EMPTY:
                            graph.add_edge(f,t,50)

                t=""+str(i+1)+"#"+str(j-1)
                if j>0 and i<size-1:
                    if grid[i+1][j-1]==current:
                        graph.add_edge(f,t,0)
                    else:
                        if grid[i+1][j-1]==EMPTY:
                            graph.add_edge(f,t,50)

                t=""+str(i+1)+"#"+str(j)
                if i<size-1:
                    if grid[i+1][j]==current:
                        graph.add_edge(f,t,0)
                    else:
                        if grid[i+1][j]==EMPTY:
                            graph.add_edge(f,t,50)

                t=""+str(i-1)+"#"+str(j)
                if i>0:
                    if grid[i-1][j]==current:
                        graph.add_edge(f,t,0)
                    else:
                        if grid[i-1][j]==EMPTY:
                            graph.add_edge(f,t,50)

                t=""+str(i-1)+"#"+str(j+1)
                if i>0 and j<size-1:
                    if grid[i-1][j+1]==current:
                        graph.add_edge(f,t,0)
                    else:
                        if grid[i-1][j+1]==EMPTY:
                            graph.add_edge(f,t,50)

                t=""+str(i)+"#"+str(j+1)
                if j<size-1:
                    if grid[i][j+1]==current:
                        graph.add_edge(f,t,0)
                    else:
                        if grid[i][j+1]==EMPTY:
                            graph.add_edge(f,t,50)

                t=""+str(i+1)+"#"+str(j+1)
                if i<size-1 and j<size-1:
                    if grid[i+1][j+1]==current:
                        graph.add_edge(f,t,0)
                    else:
                        if grid[i+1][j+1]==EMPTY:
                            graph.add_edge(f,t,50)
            else:
                if grid[i][j]==EMPTY:
                    f=""+str(i)+"#"+str(j)
                    t=""+str(i-1)+"#"+str(j-1)
                    if i>0 and j>0:
                        if grid[i-1][j-1]==current:
                            graph.add_edge(f,t,1)
                        else:
                            if grid[i-1][j-1]==EMPTY:
                                graph.add_edge(f,t,100)

                    t=""+str(i)+"#"+str(j-1)
                    if j>0:
                        if grid[i][j-1]==current:
                            graph.add_edge(f,t,1)
                        else:
                            if grid[i][j-1]==EMPTY:
                                graph.add_edge(f,t,100)

                    t=""+str(i+1)+"#"+str(j-1)
                    if j>0 and i<size-1:
                        if grid[i+1][j-1]==current:
                            graph.add_edge(f,t,1)
                        else:
                            if grid[i+1][j-1]==EMPTY:
                                graph.add_edge(f,t,100)

                    t=""+str(i+1)+"#"+str(j)
                    if i<size-1:
                        if grid[i+1][j]==current:
                            graph.add_edge(f,t,1)
                        else:
                            if grid[i+1][j]==EMPTY:
                                graph.add_edge(f,t,100)

                    t=""+str(i-1)+"#"+str(j)
                    if i>0:
                        if grid[i-1][j]==current:
                            graph.add_edge(f,t,1)
                        else:
                            if grid[i-1][j]==EMPTY:
                                graph.add_edge(f,t,100)

                    t=""+str(i-1)+"#"+str(j+1)
                    if i>0 and j<size-1:
                        if grid[i-1][j+1]==current:
                            graph.add_edge(f,t,1)
                        else:
                            if grid[i-1][j+1]==EMPTY:
                                graph.add_edge(f,t,100)

                    t=""+str(i)+"#"+str(j+1)
                    if j<size-1:
                        if grid[i][j+1]==current:
                            graph.add_edge(f,t,1)
                        else:
                            if grid[i][j+1]==EMPTY:
                                graph.add_edge(f,t,100)

                    t=""+str(i+1)+"#"+str(j+1)
                    if i<size-1 and j<size-1:
                        if grid[i+1][j+1]==current:
                            graph.add_edge(f,t,1)
                        else:
                            if grid[i+1][j+1]==EMPTY:
                                graph.add_edge(f,t,100)
    return graph

def djikstra(graph, initial, end):
    shortest_paths = {initial: (None, 0)}
    current_node = initial
    visited = set()

    while current_node != end:
        visited.add(current_node)
        destinations = graph.edges[current_node]
        weight_to_current_node = shortest_paths[current_node][1]

        for next_node in destinations:
            weight = graph.weights[(current_node, next_node)] + weight_to_current_node
            if next_node not in shortest_paths:
                shortest_paths[next_node] = (current_node, weight)
            else:
                current_shortest_weight = shortest_paths[next_node][1]
                if current_shortest_weight > weight:
                    shortest_paths[next_node] = (current_node, weight)

        next_destinations = {node: shortest_paths[node] for node in shortest_paths if node not in visited}
        if not next_destinations:
            return "Route Non Possible"
        current_node = min(next_destinations, key=lambda k: next_destinations[k][1])

    path = list()
    while current_node is not None:
        path.append(current_node)
        next_node = shortest_paths[current_node][0]
        current_node = next_node
    #print(path)
    return path

def find_best(size, grid, graph, current):
    lst=list()
    if current==1:
        for i in range(size):
            for j in range(size):
                lst.append(djikstra(graph, ""+str(i)+"#0", ""+str(j)+"#"+str(size-1)))
    else:
        #orange
        for j in range(size):
            for i in range(size):
                lst.append(djikstra(graph, "0#"+str(j), ""+str(size-1)+"#"+str(i)))

    sum=math.inf
    path=random.choice(lst)
    for elt in lst:
        s=weigh(graph,elt)
        if s!=0 and s<sum:
            path=elt
            sum=s

    tab=random.choice(path).split("#")
    tab[0]=int(tab[0])
    tab[1]=int(tab[1])
    while grid[tab[0]][tab[1]]:
        tab=random.choice(path).split("#")
        tab[0]=int(tab[0])
        tab[1]=int(tab[1])
    return tab

def weigh(graph, elt):
    sum=0
    longeur=len(elt)-2
    for i in range(longeur):
        if isinstance(graph.weights.get((elt[i],elt[i+1])), int):
            sum+=graph.weights.get((elt[i],elt[i+1]))
    #print(sum)
    return sum

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
