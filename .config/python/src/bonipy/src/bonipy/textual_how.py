#!/usr/bin/env python3

# Using todo as issue tracker.
# pylint: disable=fixme

# TODO: Allow tab navigation only in debug mode.
# TODO: Allow attack pattern to be changed in debug mode.
# TODO: End battle if hit points of either character reaches zero.

# Standard libraries.
import collections.abc as cabc
import dataclasses
import itertools
import random
import sys
import typing

# External dependencies.
import textual.app
import textual.coordinate
import textual.binding
import textual.message
import textual.widgets

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    Digits,
    OptionList,
    ProgressBar,
    Rule,
    Static,
)

# Reference: https://textual.textualize.io/widget_gallery


@dataclasses.dataclass
class Character:
    username: str = ""
    ap: int = 0
    hp: int = 0
    max_hp: int = 0


class IntegerStatic(Static):
    label = reactive("")
    maximum = reactive(0)
    text = reactive("")
    value = reactive(0)

    def __init__(
        self, *args: typing.Any, label: str = "", **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.label = label

    def compute_text(self) -> str:
        if not self.value:
            text = ""
        elif self.label:
            if self.maximum:
                text = f"{self.label}: {self.value} / {self.maximum}"
            else:
                text = f"{self.label}: {self.value}"
        elif self.maximum:
            text = f"{self.value} / {self.maximum}"
        else:
            text = f"{self.value}"
        return text

    def reset(self) -> None:
        self.value = 0

    def watch_text(self, old_text: str, new_text: str) -> None:
        del old_text
        self.update(new_text)


class CharacterStatus(Vertical):
    value = reactive(Character())

    def compose(self) -> ComposeResult:
        yield Static(id="username")
        yield IntegerStatic(id="hp", label="HP")
        yield ProgressBar(id="hp_bar", show_eta=False, show_percentage=False, total=20)
        yield IntegerStatic(id="ap", label="AP")
        yield ProgressBar(id="ap_bar", show_eta=False, show_percentage=False, total=20)

    def watch_value(self, old_character: Character, new_character: Character) -> None:
        del old_character
        self.query_one("#ap_bar", ProgressBar).progress = new_character.ap
        self.query_one("#ap", IntegerStatic).value = new_character.ap
        hp_widget = self.query_one("#hp", IntegerStatic)
        hp_widget.maximum = new_character.max_hp
        hp_widget.value = new_character.hp
        self.query_one("#hp_bar", ProgressBar).progress = new_character.hp
        self.query_one("#username", Static).update(new_character.username)


class AttackPatternPicker(Vertical):
    @dataclasses.dataclass
    class Picked(textual.message.Message):
        result: tuple[int, int] = (0, 0)

    class Card(Digits):
        number = reactive(0)

        def set_random(self) -> None:
            self.number = min(10, random.randrange(1, 13))

        def reset(self) -> None:
            self.number = 0

        def watch_number(self, old_number: int, new_number: int) -> None:
            del old_number
            if new_number > 9:
                character = "E"
            elif new_number > 0:
                character = str(new_number)
            else:
                character = ""
            self.update(character)

    class Hand(Vertical):
        def compose(self) -> ComposeResult:
            with Horizontal():
                yield AttackPatternPicker.Card()
                yield AttackPatternPicker.Card()
                yield AttackPatternPicker.Card()
            yield IntegerStatic(id="total", label="Total")
            yield IntegerStatic(id="base", label="Base")
            yield IntegerStatic(id="bonus", label="Bonus")

        def draw(self) -> None:
            cards = list(self.query(AttackPatternPicker.Card))
            cards[2].set_random()

        def get_value(self) -> int:
            base = self.query_one("#base", IntegerStatic).value
            bonus = self.query_one("#bonus", IntegerStatic).value
            return max(1, min(9, base + bonus))

        def reset(self) -> None:
            for card in self.query(AttackPatternPicker.Card):
                card.reset()
            for integer_widget in self.query(IntegerStatic):
                integer_widget.reset()

        def set_bonus(self, other_hand: "AttackPatternPicker.Hand") -> None:
            limit = 21
            total = self.query_one("#total", IntegerStatic).value
            other_total = other_hand.query_one("#total", IntegerStatic).value
            if total > limit:
                bonus = 0
            elif other_total > limit:
                bonus = 2
            elif total > other_total:
                bonus = 2
            elif total == other_total:
                bonus = 1
            else:
                bonus = 0
            self.query_one("#bonus", IntegerStatic).value = bonus

        def start(self) -> None:
            cards = list(self.query(AttackPatternPicker.Card))
            cards[0].set_random()
            cards[1].set_random()
            cards[2].reset()
            for integer_widget in self.query(IntegerStatic):
                integer_widget.reset()

        def stop(self) -> None:
            total = self.query_one("#total", IntegerStatic).value = sum(
                card.number for card in self.query(AttackPatternPicker.Card)
            )
            self.query_one("#base", IntegerStatic).value = int((total - 1) / 3) % 7 + 1

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield self.Hand(id="user_hand")
            yield OptionList("Add", "Skip", id="action")
            yield self.Hand(id="enemy_hand")

    async def on_option_list_option_selected(
        self, message: OptionList.OptionSelected
    ) -> None:
        if message.option_list.id == "action":
            user_hand = self.query_one("#user_hand", self.Hand)
            enemy_hand = self.query_one("#enemy_hand", self.Hand)
            if message.option.prompt == "Add":
                user_hand.draw()
            elif message.option.prompt == "Skip":
                enemy_hand.draw()
            user_hand.stop()
            enemy_hand.stop()
            user_hand.set_bonus(enemy_hand)
            enemy_hand.set_bonus(user_hand)
            self.post_message(
                self.Picked(result=(user_hand.get_value(), enemy_hand.get_value()))
            )

    def reset(self) -> None:
        for hand in self.query(self.Hand):
            hand.reset()

    def start(self) -> None:
        for hand in self.query(self.Hand):
            hand.start()
        self.query_one("#action", OptionList).focus()


AttackPatternID = int
AttackPattern = tuple[int, int, int, int]

id_attack_patterns: dict[AttackPatternID, AttackPattern] = {
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


class AttackPatternTable(Horizontal):

    @dataclasses.dataclass
    class Done(textual.message.Message):
        result: tuple[Character, Character]

    can_focus = True

    result = reactive(
        (
            (Character(), Character()),
            (Character(), Character()),
            (Character(), Character()),
            (Character(), Character()),
            (Character(), Character()),
        )
    )

    def compose(self) -> ComposeResult:
        yield CharacterStatus()
        with Vertical():
            yield DataTable()
        yield CharacterStatus()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        turn_count = 4
        table.add_columns("Attacker", *map(str, range(1, turn_count + 1)))
        table.cursor_type = "column"
        table.clear()
        table.add_row(*itertools.repeat("", turn_count + 1))
        table.add_row(*itertools.repeat("", turn_count + 1))

    def on_data_table_column_highlighted(
        self, message: DataTable.ColumnHighlighted
    ) -> None:
        turn = message.cursor_column
        for character_widget, character in zip(
            self.query(CharacterStatus), self.result[turn]
        ):
            character_widget.value = character

    def on_data_table_column_selected(self, message: DataTable.ColumnSelected) -> None:
        table = self.query_one(DataTable)
        turn = message.cursor_column
        if turn + 1 < len(message.data_table.columns):
            table.move_cursor(column=turn + 1)
        else:
            self.post_message(self.Done(result=self.result[-1]))

    def on_focus(self) -> None:
        self.query_one(DataTable).focus()

    def set_pattern(
        self,
        characters: tuple[Character, Character],
        pattern_ids: tuple[AttackPatternID, AttackPatternID],
    ) -> None:
        table = self.query_one(DataTable)
        for row, (character, pattern_id) in enumerate(zip(characters, pattern_ids)):
            table.update_cell_at(
                textual.coordinate.Coordinate(row=row, column=0),
                character.username + (f"({pattern_id})" if pattern_id else ""),
            )

        patterns = tuple(id_attack_patterns[pattern_id] for pattern_id in pattern_ids)

        for row, pattern in enumerate(patterns):
            for column, is_attacking in enumerate(pattern, start=1):
                table.update_cell_at(
                    textual.coordinate.Coordinate(row=row, column=column),
                    "O" if is_attacking else "",
                )

        def process_battle() -> cabc.Generator[tuple[Character, Character], None, None]:
            user = characters[0]
            enemy = characters[1]
            yield (user, enemy)
            for is_attacking in zip(patterns[0], patterns[1]):
                user_attack = user.ap if is_attacking[0] else 0
                enemy_attack = enemy.ap if is_attacking[1] else 0

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

        self.result = tuple(process_battle())  # type: ignore[assignment]

        table.move_cursor(column=0)


class BattleScreen(textual.screen.Screen[None]):
    characters = reactive(
        (
            Character(username="User", ap=1, hp=6, max_hp=6),
            Character(username="Enemy", ap=1, hp=3, max_hp=3),
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
        yield AttackPatternPicker()
        yield Rule()
        yield Static("Result")
        yield AttackPatternTable()
        yield Button("Continue")
        yield textual.widgets.Footer()

    def on_attack_pattern_picker_picked(
        self, message: AttackPatternPicker.Picked
    ) -> None:
        table = self.query_one(AttackPatternTable)
        table.set_pattern(self.characters, message.result)
        table.focus()

    def on_attack_pattern_table_done(self) -> None:
        self.query_one(Button).focus()

    def on_button_pressed(self) -> None:
        table = self.query_one(AttackPatternTable)
        characters = table.result[-1]
        self.characters = (
            dataclasses.replace(characters[0]),
            dataclasses.replace(characters[1]),
        )
        self.query_one("#user_action", OptionList).focus()

    async def on_option_list_option_selected(
        self, message: OptionList.OptionSelected
    ) -> None:
        if message.option_list.id == "user_action":
            if message.option.prompt == "Attack":
                self.query_one(AttackPatternPicker).start()
            elif message.option.prompt == "Run":
                await self.app.action_quit()

    def watch_characters(
        self,
        old_characters: tuple[Character, Character],
        new_characters: tuple[Character, Character],
    ) -> None:
        del old_characters
        self.query_one("#user_status", CharacterStatus).value = new_characters[0]
        self.query_one("#enemy_status", CharacterStatus).value = new_characters[1]
        self.query_one(AttackPatternPicker).reset()
        self.query_one(AttackPatternTable).set_pattern(new_characters, (0, 0))


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
