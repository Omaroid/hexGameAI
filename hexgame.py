#!/usr/bin/python3

"""
This module provides the core of the game engine for
the game of Hex.

Author: Sylvain B.
Version: 1.0
"""

EMPTY, BLUE, RED = 0, 1, 2


class InvalidMoveException(Exception):
    """This exception is raised when a move is invalid."""
    pass


class Hex():
    """
    The Hex class represents an Hex board of a give size
    in a given state.
    """

    def __init__(self, size):
        self.size = size
        [self.grid, self.winner, self.current, self.edges] = [None] * 4
        self.reset()

    @staticmethod
    def create_from_str(serialized_string):
        """
        Initializes an hex board using a string representing this board

        Arguments:
        - The string used to initialize the board.
        """
        winner_str, grid_str = serialized_string.split('/')
        grid = [[int(x) for x in row.split('-')]
                for row in grid_str.split('#')]
        assert len(grid) == len(grid[0]), 'Invalid grid dimension!'
        hexboard = Hex(len(grid))
        hexboard.grid = grid
        hexboard.winner = None if winner_str == "" else int(winner_str)
        return hexboard

    def _2d_2_1d(self, i, j):
        return i * self.size + j

    def _1d_2_2d(self, val):
        return val // self.size, val % self.size

    def reset(self):
        """Resets the game."""
        self.grid = [[EMPTY for _ in range(self.size)]
                     for _ in range(self.size)]
        self._create_graph()
        self.current = BLUE
        self.winner = None

    def _left(self):
        return self.size ** 2

    def _right(self):
        return self.size ** 2 + 1

    def _top(self):
        return self.size ** 2 + 2

    def _bottom(self):
        return self.size ** 2 + 3

    def _create_graph(self):
        self.edges = [[] for _ in range(self.size ** 2 + 4)]
        for i in range(self.size):
            for j in range(self.size):
                if i < self.size - 1:
                    self.edges[self._2d_2_1d(i, j)].append(
                        self._2d_2_1d(i + 1, j))
                    self.edges[self._2d_2_1d(i + 1, j)].append(
                        self._2d_2_1d(i, j))
                    if j > 0:
                        self.edges[self._2d_2_1d(i, j)].append(
                            self._2d_2_1d(i + 1, j - 1))
                        self.edges[self._2d_2_1d(i + 1, j - 1)].append(
                            self._2d_2_1d(i, j))
                if j < self.size - 1:
                    self.edges[self._2d_2_1d(i, j)].append(
                        self._2d_2_1d(i, j + 1))
                    self.edges[self._2d_2_1d(i, j + 1)].append(
                        self._2d_2_1d(i, j))

        for i in range(self.size):
            self.edges[self._left()].append(self._2d_2_1d(i, 0))
            self.edges[self._2d_2_1d(i, self.size - 1)].append(self._right())
        for j in range(self.size):
            self.edges[self._top()].append(self._2d_2_1d(0, j))
            self.edges[self._2d_2_1d(self.size - 1, j)].append(self._bottom())

    def play(self, i, j):
        """
        Plays a move: puts a piece of the current player
        into the specified cell.

        Arguments:
        - row
        - column
        Exceptions:
        - InvalidMoveException if the current cell is not empty.
        """
        if self.grid[i][j] != EMPTY:
            raise InvalidMoveException(
                "Cell ({}, {}) is not empty!".format(i, j))
        self.grid[i][j] = self.current
        if self._check_winner():
            self.winner = self.current
        self.current = BLUE if self.current == RED else RED
        return self.winner

    def _check_winner(self):
        if self.current == BLUE:
            return self._is_connected(self._left(), self._right(), BLUE)
        return self._is_connected(self._top(), self._bottom(), RED)

    def _is_connected(self, i, j, player, marked=None):
        if not marked:
            marked = set()
        if i == j:
            return True
        marked.add(i)
        for k in self.edges[i]:
            if k not in marked:
                if k in (self._left(), self._right(),
                         self._top(), self._bottom()):
                    if self._is_connected(k, j, player, marked):
                        return True
                else:
                    i_2, j_2 = self._1d_2_2d(k)
                    if self.grid[i_2][j_2] == player:
                        if self._is_connected(k, j, player, marked):
                            return True
        return False

    def serialize(self):
        """Returns a string representing the board"""
        return "{}/{}".format(
            self.winner if self.winner else "",
            "#".join("-".join(str(i) for i in r) for r in self.grid))
