#!/usr/bin/env python3

# Standard libraries.
import asyncio
import curses
import typing

from unittest.mock import Mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35.curses_ext.selector_loop import EventLoop
from bonipy35.curses_ext.tower import (
    AttackSource,
    AttackTarget,
    Keymap,
    Mover,
    Peashooter,
    Projectile,
    Renderable,
    State,
    Sunflower,
    Wallnut,
    Zombie,
    async_run,
    run,
)


@pytest.fixture(name="state")
def fixture_state(window: Mock, monkeypatch: pytest.MonkeyPatch) -> State:
    window.getmaxyx.return_value = (35, 80)
    monkeypatch.setattr(curses, "color_pair", lambda number: number)
    monkeypatch.setattr(curses, "init_pair", Mock())
    return State(window)


class TestAttackOne:
    def test_radius_and_health(self) -> None:
        source = AttackSource(
            x=5, y=2, attack_radius_x=2, attack_radius_y=1, attack_power=10
        )
        targets = [
            AttackTarget(x=5, y=2, health=0),
            AttackTarget(x=5, y=4, health=10),
            AttackTarget(x=8, y=2, health=10),
        ]
        assert not source.attack_one(targets)
        target = AttackTarget(x=7, y=3, health=20)
        assert source.attack_one(targets + [target])
        assert target.health == 10


class TestMove:
    def test_steps(self) -> None:
        mover = Mover(x=5, y=0, move_step=-1, move_time_per_cell=3)
        mover.move()
        mover.move()
        assert mover.x == 5
        mover.move()
        assert mover.x == 4


class TestRenderable:
    def test_bounds(self, window: Mock) -> None:
        item = Renderable(x=0, y=0, curse_attr=0, curse_char="X")
        item.render(window, 0, 10)
        item.render(window, 10, 0)
        window.addstr.assert_not_called()
        item.render(window, 10, 10)
        window.addstr.assert_called_once_with(3, 1, "X", 0)


class TestIsShooting:
    def test_cooldown(self, state: State) -> None:
        state.zombies.clear()
        plant = Peashooter(x=5, y=5)
        assert not plant.is_shooting([])
        assert not plant.is_shooting([Zombie(x=4, y=5), Zombie(x=6, y=8)])
        assert plant.is_shooting([Zombie(x=6, y=5)])
        assert not plant.is_shooting([Zombie(x=6, y=5)])
        plant.shoot_cooldown = 1
        assert plant.is_shooting([Zombie(x=6, y=5)])


class TestKeymap:
    def test_selection(self) -> None:
        keymap = Keymap()
        assert keymap.handle_input(ord("1"))
        assert keymap.handle_input(ord("2"))
        assert keymap.new_plant_type is Sunflower
        assert not keymap.handle_input(ord("!"))


class TestPlantSeed:
    def test_cost_and_occupied_row(self, state: State) -> None:
        state.cursor.x, state.cursor.y = 10, 6
        state.plant_seed(Wallnut)
        assert state.sun_points == 50
        assert state.plants[0].y == 5
        assert state.plants[0].health == 300
        state.plant_seed(Sunflower)
        assert len(state.plants) == 1
        state.cursor.x = 12
        state.plant_seed(Peashooter)
        assert len(state.plants) == 1
        state.plant_seed(Sunflower)
        assert state.sun_points == 0
        state.cursor.x = 0
        state.plant_seed(Peashooter)
        assert len(state.plants) == 2

    @pytest.mark.parametrize("x,y", [(0, 5), (77, 5), (10, 0), (10, 20)])
    def test_invalid_positions(self, state: State, x: int, y: int) -> None:
        assert not state.can_plant_at(x, y)


class TestHandleInput:
    def test_controls(self, state: State) -> None:
        for key in (ord("w"), ord("a"), ord("s"), ord("d")):
            state.handle_input(key)
        assert (state.cursor.x, state.cursor.y) == (39, 10)
        state.handle_input(ord("3"))
        state.handle_input(ord(" "))
        assert isinstance(state.plants[0], Wallnut)
        state.game_over = True
        state.handle_input(ord(" "))
        assert len(state.plants) == 1
        state.handle_input(ord("Q"))
        assert state.is_stopping


class TestUpdate:
    def test_simulation(
        self, state: State, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("random.randint", lambda lower, upper: 1)
        state.zombie_spawn_timer = 119
        state.plants = [
            Sunflower(x=10, y=5),
            Peashooter(x=20, y=5),
            Wallnut(x=25, y=5),
        ]
        state.plants[-1].health = 0
        state.zombies = [
            Zombie(x=10, y=5),
            Zombie(x=22, y=5),
            Zombie(x=30, y=8),
        ]
        state.zombies[-1].health = 0
        state.projectiles = [Projectile(x=10, y=5), Projectile(x=100, y=5)]
        state.update()
        assert state.sun_points == 135
        assert len(state.plants) == 2
        assert state.plants[0].health == 90
        assert state.zombies[0].health == 50
        assert all(
            projectile.x <= state.game_width
            for projectile in state.projectiles
        )
        state.zombies = [Zombie(x=0, y=5)]
        state.update()
        assert state.game_over
        state.update()

    def test_spawn_without_new_zombie(
        self, state: State, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("random.randint", lambda lower, upper: upper)
        state.zombie_spawn_timer = 119
        state.plants = [Sunflower(x=5, y=5)]
        state.update()
        assert len(state.zombies) == 2
        assert state.sun_points == 100


class TestRender:
    def test_entities_and_game_over(self, state: State, window: Mock) -> None:
        state.plants = [Peashooter(x=5, y=5)]
        state.projectiles = [Projectile(x=6, y=5)]
        state.game_over = True
        state.render(window)
        assert any(
            call.args[2] == "+" for call in window.addstr.call_args_list
        )
        assert any(
            "GAME OVER" in call.args[2]
            for call in window.addstr.call_args_list
        )
        state.height = 26
        state.keymap.render(window, state)
        state.game_height = 1
        state.draw_lawn(window)

    def test_small_terminal(
        self, state: State, window: Mock, loop: EventLoop
    ) -> None:
        del loop
        state.height = 1
        state.render(window)
        window.addnstr.assert_called()

    def test_no_colors(
        self, window: Mock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(curses, "has_colors", lambda: False)
        monkeypatch.setattr(curses, "color_pair", lambda number: 0)
        State(window)


class TestRenderLoop:
    @pytest.mark.parametrize("size", [(35, 80), (1, 1)])
    def test_resize_and_stop(
        self,
        state: State,
        window: Mock,
        loop: EventLoop,
        size: tuple[int, int],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        window.getmaxyx.return_value = size

        async def stop(delay: float) -> None:
            assert delay == 0.2
            state.is_stopping = True

        monkeypatch.setattr(asyncio, "sleep", stop)
        loop.run_until_complete(state.run_render_loop(window))
        assert (state.height, state.width) == size
        window.noutrefresh.assert_called()


class TestAsyncRun:
    def test_quit(self, state: State, window: Mock, loop: EventLoop) -> None:
        del state
        window.getch.side_effect = [ord("!"), ord("q")] + [-1] * 20
        assert loop.run_until_complete(async_run()) == 0
        assert not asyncio.all_tasks(loop)

    def test_render_failure(
        self, state: State, loop: EventLoop, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        del state
        monkeypatch.setattr(
            State, "render", Mock(side_effect=RuntimeError("render failed"))
        )
        with pytest.raises(RuntimeError, match="render failed"):
            loop.run_until_complete(async_run())
        assert not asyncio.all_tasks(loop)

    def test_render_finishes(
        self, state: State, loop: EventLoop, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        del state

        async def finish(self: State, window: "curses.window") -> None:
            del self, window

        monkeypatch.setattr(State, "run_render_loop", finish)
        assert loop.run_until_complete(async_run()) == 0
        assert not asyncio.all_tasks(loop)

    def test_cancel(self, state: State, loop: EventLoop) -> None:
        del state
        task = loop.create_task(async_run())
        loop.call_later(0.001, task.cancel)
        with pytest.raises(asyncio.CancelledError):
            loop.run_until_complete(task)
        assert not asyncio.all_tasks(loop)


class TestRun:
    def test_shared_runner(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def runner(
            coro: typing.Coroutine[typing.Any, typing.Any, int],
        ) -> int:
            assert asyncio.iscoroutine(coro)
            coro.close()
            return 7

        monkeypatch.setattr("bonipy35.curses_ext.selector_loop.run", runner)
        assert run() == 7
