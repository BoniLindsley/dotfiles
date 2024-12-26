#!/usr/bin/env python3

# Using TODO as reminders on what to do.
# pylint: disable=fixme
# TODO: Show hotkey state in OSD.
# TODO: Add range. Destination is "range" cell away from target.
# TODO: Implement multi-cell instance creation.

# Installation: Might need libegl1 in Debian.

# Standard libraries
import asyncio
import datetime
import logging
import math
import sys
import time
import typing

from collections.abc import AsyncGenerator, Generator

# External dependencies.
import pygame
import pygame.font
import pygame.key
import pygame.time

from pygame.math import Vector2


_logger = logging.getLogger(__name__)


class NonZero(int):
    def __new__(cls, *args: typing.Any, **kwargs: typing.Any) -> "NonZero":
        instance = super().__new__(cls, *args, **kwargs)
        if not instance:
            raise ValueError("New value cannot be zero.")
        return instance


class SurfaceCoordinate(Vector2):
    pass


class WorldCoordinate(Vector2):
    pass


class Renderable(WorldCoordinate):
    def __init__(
        self, *args: typing.Any, color: None | pygame.Color = None, **kwargs: typing.Any
    ) -> None:
        if color is None:
            color = pygame.Color(255, 255, 255)

        super().__init__(*args, **kwargs)

        self.color = color

    def step(self) -> None:
        pass


class Pushback(Renderable):
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self.update(round(self))

    def push(self, other: "Movable") -> None:
        if other is self:
            return

        other_cell = other.cell
        if other_cell != self:
            return

        other_new_cell = other.last_cell
        if other_new_cell == other_cell:
            # TODO: What if this is outside the map?
            other_new_cell = other_cell + (0, 1)

        other.cell.update(other_new_cell)
        other.stop()


class Movable(Renderable):
    def __init__(
        self,
        *args: typing.Any,
        speed: None | float = None,
        target: "None | Movable" = None,
        **kwargs: typing.Any,
    ) -> None:
        if speed is None:
            speed = 0.15

        super().__init__(*args, **kwargs)

        self.cell = WorldCoordinate(round(self))
        self.destination = WorldCoordinate(self)
        self.last_cell = WorldCoordinate(self.cell)
        self.range = 1
        self.speed = speed
        self.target = target

        self.chase(target)

    def chase(self, target: "None | Movable") -> None:
        self.target = target
        if target is None:
            return

        destination = self.destination
        destination.update(target.cell)

    def move_by(self, movement: WorldCoordinate) -> None:
        last_cell = WorldCoordinate(self.cell)
        self += movement
        self.cell.update(
            math.ceil(self[0]) if movement[0] < 0 else math.floor(self[0]),
            math.ceil(self[1]) if movement[1] < 0 else math.floor(self[1]),
        )
        if self.cell != last_cell:
            self.last_cell = last_cell
            self.chase(self.target)

    def step(self) -> None:
        step_size = self.speed
        if not step_size:
            return

        difference = self.destination - self
        if not difference and self.target:
            self.chase(self.target)
            difference = self.destination - self

        if not difference:
            return

        movement = WorldCoordinate(0, 0)

        min_difference = min(abs(difference[0]), abs(difference[1]))
        if step_size and min_difference:
            sqrt_two = math.sqrt(2)
            movement_size = min(sqrt_two * min_difference, step_size)
            movement = movement + WorldCoordinate(
                1 if self[0] < self.destination[0] else -1,
                1 if self[1] < self.destination[1] else -1,
            ) * (movement_size / sqrt_two)
            step_size -= movement_size

        difference = self.destination - self - movement
        if step_size and difference:
            movement_size = step_size
            movement = movement + WorldCoordinate(
                max(-movement_size, min(movement_size, difference[0])),
                max(-movement_size, min(movement_size, difference[1])),
            )
            step_size -= movement_size

        self.move_by(movement)

    def stop(self) -> None:
        self.update(self.cell)
        self.last_cell.update(self.cell)
        self.destination.update(self.cell)


class View:
    def __init__(self, surface: pygame.Surface) -> None:
        self.position = WorldCoordinate(0.0, 0.0)
        self.scale = NonZero(32)
        self.surface = surface

    def render_grid(self) -> None:
        surface = self.surface
        scale = self.scale

        width, height = surface.get_size()
        grid_colour = (0, 0, 0)

        grid_top_left = self.to_surface(
            round(self.to_world(SurfaceCoordinate(0, 0))) - (0.5, 0.5)
        )

        for x in range(int(grid_top_left[0]), width, int(scale)):
            pygame.draw.line(
                surface=surface,
                color=grid_colour,
                start_pos=(x, 0),
                end_pos=(x, height),
            )

        for y in range(int(grid_top_left[1]), height, int(scale)):
            pygame.draw.line(
                surface=surface, color=grid_colour, start_pos=(0, y), end_pos=(width, y)
            )

    def to_surface(self, position: WorldCoordinate) -> SurfaceCoordinate:
        return SurfaceCoordinate(
            (position - self.position).elementwise() * self.scale
            + SurfaceCoordinate(self.surface.get_size()) // 2
        )

    def to_world(self, offset: SurfaceCoordinate) -> WorldCoordinate:
        return WorldCoordinate(
            (offset - SurfaceCoordinate(self.surface.get_size()) // 2).elementwise()
            // self.scale
            + self.position
        )


class FrameCounter:
    def __init__(self) -> None:
        self.frame = 0
        self.frame_time_ns = [time.monotonic_ns()]

    def get_fps(self) -> float:
        frame_time_ns = self.frame_time_ns

        sample_count = len(frame_time_ns)
        if sample_count < 2:
            return 0

        return (
            (sample_count - 1) * 1_000_000_000 / (frame_time_ns[-1] - frame_time_ns[0])
        )

    def step(self) -> None:
        self.frame += 1

        frame_time_ns = self.frame_time_ns
        frame_time_ns.append(time.monotonic_ns())
        if len(frame_time_ns) > 5:
            frame_time_ns[:] = frame_time_ns[1:]


class Game:
    def __init__(self) -> None:
        self.camera = camera = Movable(color=pygame.Color(0, 128, 0))
        self.frame_counter = FrameCounter()
        self.renderable: list[Renderable] = [camera]
        self.pointer_offset = SurfaceCoordinate(0, 0)

        pygame.init()
        self.surface = surface = pygame.display.set_mode(
            size=(640, 480), flags=pygame.RESIZABLE
        )

        self.font = pygame.font.Font(None, 32)
        self.view = View(surface)

    def render(self) -> None:
        self.frame_counter.step()
        background_colour = (64, 64, 64)
        self.surface.fill(background_colour)
        self.view.render_grid()
        self.render_cursor()
        for instance in self.renderable:
            pygame.draw.circle(
                surface=self.surface,
                color=instance.color,
                center=self.view.to_surface(instance),
                radius=self.view.scale // 2,
            )
        self.render_osd()
        self.render_pointer()
        pygame.display.flip()

    def render_cursor(self) -> None:
        scale = self.view.scale

        cursor_offset = self.view.to_surface(
            round(self.view.to_world(self.pointer_offset))
        )
        cursor_top_left = cursor_offset - (scale // 2, scale // 2)
        pygame.draw.rect(
            surface=self.surface,
            color=(128, 128, 128),
            rect=(*cursor_top_left, scale, scale),
        )

    def render_osd(self) -> None:
        lines = (
            f"Cell: {self.camera.cell}",
            f"FPS: {int(self.frame_counter.get_fps())} ({self.frame_counter.frame})",
            f"Instances: {len(self.renderable)}",
            f"Scale: {self.view.scale}",
        )
        img = self.font.render("\n".join(lines), True, (255, 0, 0))
        self.surface.blit(img, (20, 20))

    def render_pointer(self) -> None:
        cursor_x, cursor_y = self.pointer_offset
        cursor_width = 20
        cursor_height = 32
        pygame.draw.polygon(
            surface=self.surface,
            color=(128, 128, 128),
            points=(
                (cursor_x, cursor_y),
                (cursor_x + cursor_width, cursor_y),
                (cursor_x, cursor_y + cursor_height),
            ),
        )

    def step(self) -> None:
        for instance in self.renderable:
            instance.step()
        for instance in self.renderable:
            if not isinstance(instance, Pushback):
                continue
            for other in self.renderable:
                if not isinstance(other, Movable):
                    continue
                instance.push(other)
        self.view.position.update(self.camera)


class EventMapping:
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self.game = Game()
        self.default_button_mapping = {
            1: self.move,
            4: self.zoom_out,
            5: self.zoom_in,
        }
        self.button_mapping = self.default_button_mapping.copy()
        self.key_mapping = {
            pygame.K_d: self.create_instance_request,
            pygame.K_f: self.create_pushback_request,
            pygame.K_s: self.stop,
        }

    def cancel(self) -> None:
        self.button_mapping = self.default_button_mapping.copy()

    def create_instance(self) -> None:
        game = self.game
        game.renderable.append(
            Movable(
                round(game.view.to_world(game.pointer_offset)),
                color=pygame.Color(0, 128, 128),
                speed=0.1,
                target=game.camera,
            )
        )
        self.cancel()

    def create_instance_request(self) -> None:
        self.button_mapping[1] = self.create_instance

    def create_pushback(self) -> None:
        game = self.game
        game.renderable.append(
            Pushback(
                round(game.view.to_world(game.pointer_offset)),
                color=pygame.Color(128, 0, 0),
            )
        )
        self.cancel()

    def create_pushback_request(self) -> None:
        self.button_mapping[1] = self.create_pushback

    def move(self) -> None:
        game = self.game
        game.camera.destination.update(round(game.view.to_world(game.pointer_offset)))

    def noop(self) -> None:
        pass

    def stop(self) -> None:
        self.game.camera.stop()

    def zoom_in(self) -> None:
        max_scale = 64
        view = self.game.view
        view.scale = NonZero(min(view.scale + 1, max_scale))

    def zoom_out(self) -> None:
        min_scale = 16
        view = self.game.view
        view.scale = NonZero(max(view.scale - 1, min_scale))

    def process_event(self, *, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self.key_mapping.get(event.key, self.noop)()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.game.pointer_offset.update(event.pos)
            self.button_mapping.get(event.button, self.noop)()
        elif event.type == pygame.MOUSEMOTION:
            self.game.pointer_offset.update(event.pos)
        elif event.type == pygame.TEXTINPUT:
            # TODO: Figure out how to get key event instead of text events in SDL2.
            for key in event.text:
                self.key_mapping.get(pygame.key.key_code(key), self.noop)()
        elif not event:
            self.game.step()
            self.game.render()


async def await_event(fps: int) -> AsyncGenerator[pygame.event.Event, None]:
    second = datetime.timedelta(seconds=1)
    render_delay = second / fps
    next_time = datetime.datetime.now()
    while True:
        event = pygame.event.poll()
        if event.type == pygame.QUIT:
            break
        if event:
            sleep_delay = 0.0
        else:
            now = datetime.datetime.now()
            sleep_delay = max(0.0, (next_time - now).total_seconds())
            next_time = now + render_delay
        yield event
        if sleep_delay:
            await asyncio.sleep(delay=sleep_delay)


def wait_event(fps: int) -> Generator[pygame.event.Event, None, None]:
    second = datetime.timedelta(seconds=1)
    render_delay = second / fps
    millisecond = datetime.timedelta(milliseconds=1)
    pygame.time.set_timer(pygame.NOEVENT, millis=int(render_delay / millisecond))

    while True:
        event = pygame.event.wait()
        if event.type == pygame.QUIT:
            break
        yield event


async def amain() -> int:
    event_mapping = EventMapping()
    async for event in await_event(fps=30):
        event_mapping.process_event(event=event)
    return 0


def main() -> int:
    event_mapping = EventMapping()
    pygame.key.stop_text_input()
    for event in wait_event(fps=30):
        event_mapping.process_event(event=event)
    return 0


if __name__ == "__main__":
    sys.exit(main())
