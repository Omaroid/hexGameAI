#!/usr/bin/python3

import math
import cairo
import pygame
from PIL import Image
import asyncio

import hexgame

from random import randint

# Define the colors we will use in RGB format
GRAY = (200, 200, 200)
LIGHT_GRAY = (220, 220, 220)
BLUE = (31, 119, 180)
ORANGE = (255, 127, 14)

SIZE = WIDTH, HEIGHT = 800, 600

color_correspondance = {
    hexgame.BLUE: BLUE,
    hexgame.RED: ORANGE,
    hexgame.EMPTY: LIGHT_GRAY
}
player_names = {
    hexgame.BLUE: "Blue player",
    hexgame.RED: "Orange player"
}

screen = None
loop = None
event_queue = None
pygame_task = None


def pygame_event_loop(loop, event_queue):
    while True:
        event = pygame.event.wait()
        asyncio.run_coroutine_threadsafe(event_queue.put(event), loop=loop)


def bgra_surf_to_rgba_string(cairo_surface):
    # We use PIL to do this
    img = Image.frombuffer(
        'RGBA', (cairo_surface.get_width(),
                 cairo_surface.get_height()),
        cairo_surface.get_data().tobytes(), 'raw', 'BGRA', 0, 1)

    return img.tobytes('raw', 'RGBA', 0, 1)


def draw_hexagon(ctx, x, y, r, color=BLUE):
    angles = [(2 * i + 1) * math.pi / 6 for i in range(7)]
    xs = [x + r * math.cos(angle) for angle in angles]
    ys = [y + r * math.sin(angle) for angle in angles]
    ctx.set_line_width(2)
    ctx.move_to(xs[0], ys[0])
    for x, y in zip(xs[1:], ys[1:]):
        ctx.line_to(x, y)
    ctx.set_source_rgba(*[c / 255 for c in color], 1)
    ctx.fill_preserve()
    ctx.set_source_rgb(1, 1, 1)
    ctx.stroke()


def draw_polygon(ctx, points, color=BLUE):
    ctx.move_to(points[0][0], points[0][1])
    for x, y in points[1:]:
        ctx.line_to(x, y)
    ctx.set_source_rgb(*[c / 255 for c in color])
    ctx.fill_preserve()
    ctx.set_source_rgb(1, 1, 1)
    ctx.stroke()


def graphic_parameters(hex):
    x_stride = math.cos(math.pi / 6)
    y_stride = (1 - math.sin(math.pi / 6) / 2)
    hexa_size = int(min(WIDTH / (1.5 * (1 + hex.size) * x_stride),
                        HEIGHT / (y_stride * (1 + hex.size))))
    hexa_size /= 2
    x_stride *= 2 * hexa_size
    y_stride *= 2 * hexa_size
    x_offset = int((WIDTH - 1.5 * hex.size * x_stride + x_stride) / 2)
    y_offset = int((HEIGHT - hex.size * y_stride + 2 * hexa_size) / 2)

    return hexa_size, x_stride, y_stride, x_offset, y_offset


def draw_hexgame(ctx, hex):
    hexa_size, x_stride, y_stride, x_offset, y_offset = graphic_parameters(hex)

    upper_left = x_offset - 1.5 * x_stride, y_offset - 1.5 * hexa_size
    upper_right = (x_offset + x_stride * hex.size - int(0.5 * hexa_size),
                   y_offset - 1.5 * hexa_size)
    lower_right = (x_offset + 1.5 * x_stride * hex.size,
                   y_offset + y_stride * hex.size)
    lower_left = (x_offset + 0.5 * x_stride * hex.size - x_stride,
                  y_offset + y_stride * hex.size)

    center = ((upper_left[0] + lower_right[0]) / 2,
              (upper_left[1] + lower_right[1]) / 2)

    draw_polygon(ctx, [upper_left, upper_right, center], ORANGE)
    draw_polygon(ctx, [lower_right, upper_right, center], BLUE)
    draw_polygon(ctx, [lower_left, lower_right, center], ORANGE)
    draw_polygon(ctx, [lower_left, upper_left, center], BLUE)

    for i in range(hex.size):
        for j in range(hex.size):
            draw_hexagon(ctx,
                         x_offset + i * x_stride / 2 + x_stride * j,
                         y_offset + y_stride * i,
                         hexa_size,
                         color_correspondance[hex.grid[i][j]])


def distance(x1, y1, x2, y2):
    return (x1 - x2) ** 2 + (y1 - y2) ** 2


def get_case_from_pixel(hex, x, y):
    hexa_size, x_stride, y_stride, x_offset, y_offset = graphic_parameters(hex)

    row = (y - y_offset + hexa_size) / y_stride
    col = (x - x_offset - x_stride * int(row) / 2 + x_stride / 2) / x_stride

    current_row, current_col = int(row), int(col)
    current_dist = float("+inf")
    for i in range(max(0, int(row) - 1), min(hex.size, int(row) + 1)):
        for j in range(max(0, int(col) - 1), min(hex.size, int(col) + 1)):
            if distance(x, y,
                        x_offset + i * x_stride / 2 + x_stride * j,
                        y_offset + y_stride * i) < current_dist:
                current_dist = distance(x, y,
                                        x_offset + i * x_stride / 2
                                        + x_stride * j,
                                        y_offset + y_stride * i)
                current_row, current_col = i, j

    return current_row, current_col


def redraw(hex):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
    ctx = cairo.Context(surface)

    draw_hexgame(ctx, hex)

    # Create PyGame surface from Cairo Surface
    buf = bgra_surf_to_rgba_string(surface)
    image = pygame.image.frombuffer(buf, SIZE, "RGBA")
    # Tranfer to Screen
    screen.fill(GRAY)
    screen.blit(image, (0, 0))
    pygame.display.flip()


def set_title(title):
    loop.run_in_executor(None, pygame.display.set_caption, title)


def init_screen():
    global screen, loop, event_queue, pygame_task
    loop = asyncio.get_event_loop()
    event_queue = asyncio.Queue()
    pygame.init()
    pygame.display.set_mode(SIZE)
    screen = pygame.display.get_surface()
    pygame_task = loop.run_in_executor(None, pygame_event_loop, loop,
                                       event_queue)


def teardown_screen():
    pygame_task.cancel()
    pygame.display.quit()
    pygame.quit()


@asyncio.coroutine
def handle_events(hex, button_callback):
    while True:
        event = yield from event_queue.get()
        if event.type == pygame.QUIT:
            teardown_screen()
            break
        if event.type == pygame.MOUSEBUTTONDOWN:
            row, col = randint(0,10), randint(0,10)
            if row >= 0 and row < hex.size and col >= 0 and col < hex.size:
                if button_callback:
                    yield from button_callback(hex, row, col)


@asyncio.coroutine
def wait_for_next_click(hex, button_callback):
    stop_loop = False
    row, col = None, None
    while not stop_loop:
        event = yield from event_queue.get()
        if event.type == pygame.QUIT:
            teardown_screen()
            break
        if not hex.winner:
            row, col = randint(0,10), randint(0,10)
            if row >= 0 and row < hex.size and col >= 0 and col < hex.size:
                stop_loop = True
    yield from button_callback(hex, row, col)


@asyncio.coroutine
def _default_button_callback(hex, row, col):
    if not hex.winner:
        print("play move", row, col)
        winner = hex.play(row, col)
        redraw(hex)
        if winner:
            print("{} WINS!!!!".format(player_names[winner]))


def main():
    init_screen()

    hex = hexgame.Hex(2)
    redraw(hex)

    try:
        loop.run_until_complete(handle_events(hex,
                                              _default_button_callback))
    except KeyboardInterrupt:
        pass
    finally:
        pygame_task.cancel()
        pygame.quit()
        pygame.display.quit()


if __name__ == "__main__":
    main()
