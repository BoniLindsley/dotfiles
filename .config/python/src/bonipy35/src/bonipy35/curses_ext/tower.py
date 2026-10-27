#!/usr/bin/env python3

"""Tower defence example: asyncio animation alongside awaited curses input."""

# This should be Python 3.5 compatible.

# Standard libraries.
import argparse
import asyncio
import curses
import logging
import random
import sys
import typing

# Internal modules.
from .. import contextlib_ext
from .. import logging_ext
from . import selector_loop
from . import ui

_logger = logging.getLogger(__name__)


class Position:
    def __init__(
        self, *args: typing.Any, x: int, y: int, **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.x = x
        self.y = y


AttackTargets = typing.Sequence["AttackTarget"]


class AttackSource(Position):
    def __init__(
        self,
        *args: typing.Any,
        attack_radius_x: int,
        attack_radius_y: int,
        attack_power: int,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.attack_power = attack_power
        self.attack_radius_x = attack_radius_x
        self.attack_radius_y = attack_radius_y

    def attack_one(self, attack_targets: AttackTargets) -> bool:
        for attack_target in attack_targets:
            if (
                attack_target.health > 0
                and abs(self.y - attack_target.y) <= self.attack_radius_y
                and abs(self.x - attack_target.x) <= self.attack_radius_x
            ):
                attack_target.health -= self.attack_power
                return True
        return False


class AttackTarget(Position):
    def __init__(
        self, *args: typing.Any, health: int, **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.health = health


class Renderable(Position):
    def __init__(
        self,
        *args: typing.Any,
        curse_attr: int,
        curse_char: str,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.curse_attr = curse_attr
        self.curse_char = curse_char

    def render(
        self, window: "curses.window", height: int, width: int
    ) -> None:
        y = self.y + 3
        if not 0 <= y < height:
            return
        x = self.x + 1
        if not 0 <= x < width:
            return
        window.addstr(y, x, self.curse_char, self.curse_attr)


class Mover(Position):
    def __init__(
        self,
        *args: typing.Any,
        move_step: int,
        move_time_per_cell: int,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.move_step = move_step
        self.move_time_per_cell = move_time_per_cell

        self.move_progress = 0

    def move(self) -> None:
        self.move_progress += 1
        while True:
            new_progress = self.move_progress - self.move_time_per_cell
            if new_progress < 0:
                break
            self.move_progress = new_progress
            self.x += self.move_step


class Plant(AttackTarget, Renderable):
    cost = 0
    name = "plant"

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        kwargs.setdefault("curse_attr", curses.color_pair(1) | curses.A_BOLD)
        super().__init__(*args, **kwargs)
        self.shoot_cooldown = 0

    def is_shooting(self, attack_targets: AttackTargets) -> bool:
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if self.shoot_cooldown > 0:
            return False

        for attack_target in attack_targets:
            if attack_target.y == self.y and attack_target.x > self.x:
                self.shoot_cooldown = 30  # Cooldown frames
                return True
        return False


class Peashooter(Plant):
    cost = 100
    name = "peashooter"

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(
            *args,
            curse_char="P",
            health=100,
            **kwargs,
        )


class Sunflower(Plant):
    cost = 50
    name = "sunflower"

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(
            *args,
            curse_char="S",
            health=100,
            **kwargs,
        )


class Wallnut(Plant):
    cost = 50
    name = "wallnut"

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(
            *args,
            curse_attr=curses.color_pair(5) | curses.A_BOLD,
            curse_char="W",
            health=300,
            **kwargs,
        )


class Zombie(AttackSource, AttackTarget, Mover, Renderable):
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(
            *args,
            attack_power=10,
            attack_radius_x=1,
            attack_radius_y=0,
            curse_attr=curses.color_pair(2) | curses.A_BOLD,
            curse_char="Z",
            health=100,
            move_step=-1,
            move_time_per_cell=3,
            **kwargs,
        )


class Projectile(AttackSource, Mover, Renderable):
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(
            *args,
            attack_power=50,
            attack_radius_x=1,
            attack_radius_y=0,
            curse_attr=curses.color_pair(3),
            curse_char="*",
            move_step=2,
            move_time_per_cell=1,
            **kwargs,
        )


class Keymap:
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self.plant_hotkeys = [
            ("1", ord("1"), Peashooter),
            ("2", ord("2"), Sunflower),
            ("3", ord("3"), Wallnut),
        ]  # type: typing.List[typing.Tuple[str, int, typing.Type[Plant]]]
        self.instructions = []  # type: list[str]
        self.new_plant_type = self.plant_hotkeys[0][2]  # type: type[Plant]

        self.update_instructions()

    def handle_input(self, next_char: int) -> bool:
        for _, key_char, new_plant_type in self.plant_hotkeys:
            if next_char == key_char:
                if self.new_plant_type != new_plant_type:
                    self.new_plant_type = new_plant_type
                    self.update_instructions()
                return True
        return False

    def render(self, window: "curses.window", state: "State") -> None:
        plant_text = "Selected: {} (${})".format(
            self.new_plant_type.name, self.new_plant_type.cost
        )
        window.addnstr(
            1, 20, plant_text, max(0, state.width - 21), curses.color_pair(1)
        )

        start_y = state.game_height + 5
        for i, instruction in enumerate(self.instructions):
            if start_y + i < state.height - 1:
                window.addnstr(
                    start_y + i,
                    2,
                    instruction,
                    max(0, state.width - 3),
                    curses.color_pair(4),
                )

    def update_instructions(self) -> None:
        instructions = self.instructions
        instructions[:] = [
            "Controls:",
            "WASD/Arrow Keys: Move cursor",
            "SPACE: Plant selected plant",
        ]
        for key, _, new_plant_type in self.plant_hotkeys:
            instructions.append(
                "{}: {} (${})".format(
                    key, new_plant_type.name, new_plant_type.cost
                )
            )
        instructions.append("Q: Quit")


class State:
    def __init__(self, window: "curses.window") -> None:
        self.height, self.width = window.getmaxyx()
        self.game_width = min(80, max(1, self.width - 2))
        self.game_height = min(20, max(1, self.height - 5))

        self.is_stopping = False
        self.sun_points = 100
        self.plants = []  # type: list[Plant]
        self.zombies = []  # type: list[Zombie]
        self.projectiles = []  # type: list[Projectile]
        self.game_over = False
        self.zombie_spawn_timer = 0

        if curses.has_colors():
            # Initialize colors
            curses.init_pair(
                1, curses.COLOR_GREEN, curses.COLOR_BLACK
            )  # Plants
            curses.init_pair(
                2, curses.COLOR_RED, curses.COLOR_BLACK
            )  # Zombies
            curses.init_pair(
                3, curses.COLOR_YELLOW, curses.COLOR_BLACK
            )  # Sun/Projectiles
            curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)  # UI
            curses.init_pair(
                5, curses.COLOR_MAGENTA, curses.COLOR_BLACK
            )  # Wallnut

        # Plant costs and properties
        self.cursor = Renderable(
            curse_attr=curses.color_pair(5) | curses.A_BOLD,
            curse_char="+",
            x=self.game_width // 2,
            y=self.game_height // 2,
        )
        self.keymap = Keymap()

        for _ in range(2):
            self.spawn_zombie()

    def render(self, window: "curses.window") -> None:
        if self.height < 28 or self.width < 44:
            loop = typing.cast(
                selector_loop.EventLoop, asyncio.get_event_loop()
            )
            ui.draw(loop, ["Tower needs 44 columns and 28 rows; q quits."])
            return
        self.draw_border(window)
        self.draw_ui(window)
        self.draw_lawn(window)
        height = self.height
        width = self.width
        for plant in self.plants:
            plant.render(window, height, width)
        for zombie in self.zombies:
            zombie.render(window, height, width)
        for projectile in self.projectiles:
            projectile.render(window, height, width)

        self.cursor.render(window, height, width)
        if self.game_over:
            self.draw_game_over(window)

    def draw_border(self, window: "curses.window") -> None:
        # Draw game border
        for y in range(self.game_height + 2):
            window.addstr(y + 2, 0, "|", curses.color_pair(4))
            window.addstr(
                y + 2, self.game_width + 1, "|", curses.color_pair(4)
            )

        for x in range(self.game_width + 2):
            window.addstr(2, x, "-", curses.color_pair(4))
            window.addstr(self.game_height + 3, x, "-", curses.color_pair(4))

    def draw_ui(self, window: "curses.window") -> None:
        title = "PLANTS VS ZOMBIES ASCII"
        window.addstr(
            0,
            (self.width - len(title)) // 2,
            title,
            curses.color_pair(4) | curses.A_BOLD,
        )

        # Sun points
        sun_text = "Sun: {}".format(self.sun_points)
        window.addstr(1, 2, sun_text, curses.color_pair(3))
        self.keymap.render(window, self)

    def draw_lawn(self, window: "curses.window") -> None:
        # Draw lawn rows (5 rows)
        for row in range(5):
            y = 5 + row * 3
            if y < self.game_height + 2:
                for x in range(1, self.game_width + 1):
                    window.addstr(y + 2, x, ".", curses.color_pair(1))

    def get_row_from_y(self, y: int) -> int:
        # Convert screen y to game row (0-4)
        return (y - 5) // 3

    def get_y_from_row(self, row: int) -> int:
        # Convert game row to screen y
        return 5 + row * 3

    def can_plant_at(self, x: int, y: int) -> bool:
        # Check if position is valid and empty
        if x < 5 or x >= self.game_width - 5:  # Leave space from edges
            return False

        row = self.get_row_from_y(y)
        if row < 0 or row >= 5:
            return False

        # Check if there's already a plant here
        for plant in self.plants:
            if plant.x == x and plant.y == self.get_y_from_row(row):
                return False

        return True

    def plant_seed(self, new_plant_type: "type[Plant]") -> None:
        x = self.cursor.x
        y = self.cursor.y

        if not self.can_plant_at(x, y):
            return

        # Snap to row
        row = self.get_row_from_y(y)
        actual_y = self.get_y_from_row(row)

        cost = new_plant_type.cost
        if self.sun_points < cost:
            return
        self.sun_points -= cost

        new_plant = new_plant_type(x=x, y=actual_y)
        self.plants.append(new_plant)

    def spawn_zombie(self) -> None:
        row = random.randint(0, 4)
        y = self.get_y_from_row(row)

        zombie = Zombie(x=self.game_width - 2, y=y)
        self.zombies.append(zombie)

    def handle_input(self, next_char: int) -> None:
        if next_char == ord("q") or next_char == ord("Q"):
            self.is_stopping = True
        elif next_char == ord(" ") and not self.game_over:
            self.plant_seed(self.keymap.new_plant_type)
        else:
            movements = {
                ord("w"): (0, -1),
                curses.KEY_UP: (0, -1),
                ord("s"): (0, 1),
                curses.KEY_DOWN: (0, 1),
                ord("a"): (-1, 0),
                curses.KEY_LEFT: (-1, 0),
                ord("d"): (1, 0),
                curses.KEY_RIGHT: (1, 0),
            }
            if next_char in movements:
                dx, dy = movements[next_char]
                self.cursor.x = min(
                    self.game_width - 1, max(0, self.cursor.x + dx)
                )
                self.cursor.y = min(
                    self.game_height - 1, max(0, self.cursor.y + dy)
                )
            else:
                self.keymap.handle_input(next_char)

    def update(self) -> None:
        if self.game_over:
            return

        # Spawn zombies periodically
        self.zombie_spawn_timer += 1
        if (
            self.zombie_spawn_timer >= 120
        ):  # Every 24 seconds at five frames per second
            if random.randint(1, 3) == 1:  # 33% chance
                self.spawn_zombie()
            self.zombie_spawn_timer = 0

        for plant in self.plants:
            if isinstance(plant, Sunflower) and random.randint(1, 100) == 1:
                self.sun_points += 25

        for plant in self.plants:
            if isinstance(plant, Peashooter) and plant.is_shooting(
                self.zombies
            ):
                projectile = Projectile(x=plant.x + 1, y=plant.y)
                self.projectiles.append(projectile)

        for zombie in list(self.zombies):
            if not zombie.attack_one(self.plants):
                zombie.move()

        remaining_projectiles = []  # type: list[Projectile]
        for proj in list(self.projectiles):
            if not proj.attack_one(self.zombies):
                proj.move()
                remaining_projectiles.append(proj)
        self.projectiles[:] = remaining_projectiles[:]

        self.remove_defeated()

    def remove_defeated(self) -> None:
        self.plants[:] = [plant for plant in self.plants if plant.health > 0]

        remaining_zombies = []  # type: list[Zombie]
        for zombie in self.zombies:
            if zombie.health > 0:
                remaining_zombies.append(zombie)
            else:
                self.sun_points += 10  # Reward for killing zombie
        self.zombies[:] = remaining_zombies[:]

        self.projectiles[:] = [
            proj for proj in self.projectiles if proj.x <= self.game_width
        ]

        self.game_over = any(zombie.x <= 0 for zombie in self.zombies)

    def draw_game_over(self, window: "curses.window") -> None:
        msg = "GAME OVER! Press Q to quit"
        y = self.game_height // 2 + 3
        x = (self.game_width - len(msg)) // 2
        window.addstr(y, x, msg, curses.color_pair(2) | curses.A_BOLD)

    async def run_render_loop(self, window: "curses.window") -> None:
        while not self.is_stopping:
            self.height, self.width = window.getmaxyx()
            self.game_width = min(80, max(1, self.width - 2))
            self.game_height = min(20, max(1, self.height - 5))
            self.cursor.x = min(self.cursor.x, self.game_width - 1)
            self.cursor.y = min(self.cursor.y, self.game_height - 1)
            # Animation ticks are application work, not input polling.
            if self.height >= 28 and self.width >= 44:
                self.update()
            window.erase()
            self.render(window)
            window.noutrefresh()
            curses.doupdate()
            await asyncio.sleep(1 / 5)


async def async_run() -> int:
    loop = typing.cast(selector_loop.EventLoop, asyncio.get_event_loop())
    state = State(loop.window)
    draw_task = loop.create_task(state.run_render_loop(loop.window))
    input_task = loop.create_task(loop.getch())
    try:
        while not state.is_stopping:
            # Propagate rendering failures even while input is blocked.
            await asyncio.wait(
                [draw_task, input_task], return_when=asyncio.FIRST_COMPLETED
            )
            if draw_task.done():
                draw_task.result()
                break
            state.handle_input(input_task.result())
            if not state.is_stopping:
                input_task = loop.create_task(loop.getch())
    finally:
        draw_task.cancel()
        input_task.cancel()
        await asyncio.gather(draw_task, input_task, return_exceptions=True)
    return 0


def run() -> int:
    return selector_loop.run(async_run())


def main(argv: "None | list[str]" = None) -> int:
    """Parse command line arguments and call `run`."""

    logging_ext.set_up_logging(logger=_logger)
    parser = argparse.ArgumentParser(
        description="Tower defence using asyncio and ncurses"
    )
    logging_ext.add_verbose_flag(parser)
    arguments = parser.parse_args(None if argv is None else argv[1:])

    logging_ext.set_logger_verbosity(
        logger=_logger, verbosity=arguments.verbosity
    )

    with contextlib_ext.suppress_keyboard_interrupt():
        return run()

    return 2


if __name__ == "__main__":
    sys.exit(main())
