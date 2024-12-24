#!/usr/bin/env python3

# Standard libraries.
import collections.abc as cabc
import dataclasses
import random
import sys

# External dependencies.
import textual.app
import textual.coordinate
import textual.binding
import textual.widgets

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Button, OptionList, ProgressBar, Rule, Static

# Reference: https://textual.textualize.io/widget_gallery


@dataclasses.dataclass
class Character:
    username: str = ""
    ap: int = 0
    hp: int = 0
    max_hp: int = 0


class CharacterStatus(Vertical):
    username = reactive("")
    ap = reactive(0)
    hp = reactive(0)
    max_hp = reactive(0)

    def compose(self) -> ComposeResult:
        yield Static(id="username_text")
        yield Static(id="hp_text")
        yield ProgressBar(id="hp_bar", show_eta=False, show_percentage=False, total=20)
        yield Static(id="ap_text")
        yield ProgressBar(id="ap_bar", show_eta=False, show_percentage=False, total=20)

    def set_character(self, new_character: Character) -> None:
        self.ap = new_character.ap
        self.max_hp = new_character.max_hp
        self.hp = new_character.hp
        self.username = new_character.username

    def watch_ap(self, old_ap: int, new_ap: int) -> None:
        del old_ap
        ap_bar = self.query_one("#ap_bar", ProgressBar)
        ap_bar.progress = new_ap
        ap_text = self.query_one("#ap_text", Static)
        ap_text.update(f"AP: {new_ap}")

    def watch_hp(self, old_hp: int, new_hp: int) -> None:
        del old_hp
        hp_bar = self.query_one("#hp_bar", ProgressBar)
        hp_bar.progress = new_hp
        hp_text = self.query_one("#hp_text", Static)
        hp_text.update(f"HP: {new_hp} / {self.max_hp}")

    def watch_max_hp(self, old_max_hp: int, new_max_hp: int) -> None:
        del old_max_hp
        hp_text = self.query_one("#hp_text", Static)
        hp_text.update(f"HP: {self.hp} / {new_max_hp}")

    def watch_username(self, old_username: str, new_username: str) -> None:
        del old_username
        username_text = self.query_one("#username_text", Static)
        username_text.update(new_username)


id_attack_patterns = {
    0: (0, 0, 0, 0),
    1: (0, 0, 0, 1),
    2: (0, 0, 1, 0),
    3: (0, 1, 0, 0),
    4: (1, 0, 0, 0),
    5: (1, 0, 0, 1),
    6: (1, 0, 1, 0),
    7: (1, 0, 1, 1),
    8: (1, 1, 0, 1),
    9: (1, 1, 1, 1),
}


class AttackPatternTable(textual.widgets.DataTable[str]):
    attack_pattern_ids = reactive((0, 0))

    def on_mount(self) -> None:
        self.add_columns("Attacker", "1", "2", "3", "4")
        self.cursor_type = "column"

        self.clear()
        self.add_row("User", "O", "", "O", "")
        self.add_row("Enemy", "O", "", "O", "")

    def watch_attack_pattern_ids(
        self,
        old_attack_pattern_ids: tuple[int, int],
        new_attack_pattern_ids: tuple[int, int],
    ) -> None:
        del old_attack_pattern_ids
        for row, pattern_id in enumerate(new_attack_pattern_ids):
            for column, is_attacking in enumerate(
                id_attack_patterns[pattern_id], start=1
            ):
                self.update_cell_at(
                    textual.coordinate.Coordinate(row=row, column=column),
                    "O" if is_attacking else "",
                )
        self.move_cursor(column=0)


class BattleScreen(textual.screen.Screen[None]):
    attack_pattern_ids = reactive((0, 0))
    characters = reactive(
        (
            Character(username="User", ap=1, hp=6, max_hp=6),
            Character(username="Enemy", ap=1, hp=3, max_hp=3),
        )
    )
    turn_results = reactive(
        (
            (Character(), Character()),
            (Character(), Character()),
            (Character(), Character()),
            (Character(), Character()),
            (Character(), Character()),
        )
    )

    def compose(self) -> ComposeResult:
        yield textual.widgets.Header()
        yield Static("Action", id="action_title")
        with Horizontal():
            yield CharacterStatus(id="user_status")
            yield OptionList("Attack", "Run", id="user_action")
            yield CharacterStatus(id="enemy_status")
        yield Rule()
        yield Static("Attack Pattern")
        with Horizontal():
            yield OptionList(*map(str, range(1, 10)), id="user_attack_option")
            yield OptionList(
                *map(str, range(1, 10)), disabled=True, id="enemy_attack_option"
            )
        yield Rule()
        yield Static("Result")
        with Horizontal():
            yield CharacterStatus(id="user_turn_status")
            yield AttackPatternTable(id="attack_pattern_table").data_bind(
                BattleScreen.attack_pattern_ids
            )
            yield CharacterStatus(id="enemy_turn_status")
        yield textual.widgets.Footer()
        yield Button("Continue", id="continue_button")

    def on_button_pressed(self, message: Button.Pressed) -> None:
        if message.button.id == "continue_button":
            self.characters = (
                dataclasses.replace(self.turn_results[-1][0]),
                dataclasses.replace(self.turn_results[-1][1]),
            )
            user_action = self.query_one("#user_action", OptionList)
            user_action.focus()

    def on_data_table_column_highlighted(
        self, message: AttackPatternTable.ColumnHighlighted
    ) -> None:
        turn = message.cursor_column
        result = self.turn_results[turn]
        user_turn_status = self.query_one("#user_turn_status", CharacterStatus)
        user_turn_status.set_character(result[0])
        enemy_turn_status = self.query_one("#enemy_turn_status", CharacterStatus)
        enemy_turn_status.set_character(result[1])

    def on_data_table_column_selected(
        self, message: AttackPatternTable.ColumnSelected
    ) -> None:
        turn = message.cursor_column
        if turn + 1 < len(message.data_table.columns):
            message.data_table.move_cursor(column=turn + 1)
        else:
            continue_button = self.query_one("#continue_button", Button)
            continue_button.focus()

    async def on_option_list_option_selected(
        self, message: OptionList.OptionSelected
    ) -> None:
        if message.option_list.id == "user_action":
            if message.option.prompt == "Attack":
                user_attack_option = self.query_one("#user_attack_option", OptionList)
                user_attack_option.focus()
            elif message.option.prompt == "Run":
                await self.app.action_quit()
                return
        elif message.option_list.id == "user_attack_option":
            user_pattern_id = message.option_list.highlighted
            if user_pattern_id is None:
                user_pattern_id = 0
            else:
                user_pattern_id += 1

            enemy_attack_option = self.query_one("#enemy_attack_option", OptionList)
            enemy_pattern_id = (
                int(random.gauss(mu=5, sigma=3)) % enemy_attack_option.option_count
            ) + 1
            enemy_attack_option.highlighted = enemy_pattern_id - 1

            self.attack_pattern_ids = (user_pattern_id, enemy_pattern_id)

            attack_pattern_table = self.query_one(
                "#attack_pattern_table", AttackPatternTable
            )
            attack_pattern_table.focus()

    def watch_attack_pattern_ids(
        self,
        old_attack_pattern_ids: tuple[int, int],
        new_attack_pattern_ids: tuple[int, int],
    ) -> None:
        del old_attack_pattern_ids

        def process_battle() -> cabc.Generator[tuple[Character, Character], None, None]:
            user = self.characters[0]
            enemy = self.characters[1]
            yield (user, enemy)
            for is_user_attacking, is_enemy_attacking in zip(
                id_attack_patterns[new_attack_pattern_ids[0]],
                id_attack_patterns[new_attack_pattern_ids[1]],
            ):
                user_attack = user.ap if is_user_attacking else 0
                enemy_attack = enemy.ap if is_enemy_attacking else 0

                if user_attack == enemy_attack:
                    user_attack = 0
                    enemy_attack = 0
                elif user_attack < enemy_attack:
                    user_attack = 0
                else:
                    enemy_attack = 0

                new_user = dataclasses.replace(user, hp=user.hp - enemy_attack)
                new_enemy = dataclasses.replace(enemy, hp=enemy.hp - user_attack)
                user = new_user
                enemy = new_enemy
                yield (user, enemy)

        self.turn_results = tuple(process_battle())  # type: ignore[assignment]

    def watch_characters(
        self,
        old_characters: tuple[Character, Character],
        new_characters: tuple[Character, Character],
    ) -> None:
        del old_characters
        user_status = self.query_one("#user_status", CharacterStatus)
        user_status.set_character(new_characters[0])
        enemy_status = self.query_one("#enemy_status", CharacterStatus)
        enemy_status.set_character(new_characters[1])
        self.attack_pattern_ids = (0, 0)


class HowApp(textual.app.App):  # type: ignore[type-arg]
    BINDINGS = [
        textual.binding.Binding("ctrl+q", "quit", "Quit", show=True, priority=True),
    ]
    ENABLE_COMMAND_PALETTE = True

    def on_mount(self) -> None:
        status_screen = BattleScreen()
        self.push_screen(status_screen)


def main() -> int:
    app = HowApp()
    app.run()
    return app.return_code or 0


if __name__ == "__main__":
    sys.exit(main())
