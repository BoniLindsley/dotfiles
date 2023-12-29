#!/usr/bin/env python3

# Standard libraries.
import collections.abc as cabc
import datetime
import functools
import json
import pathlib
import typing as t

# External dependencies.
import click
import click_repl

_P = t.ParamSpec("_P")
_T = t.TypeVar("_T")

JsonData = t.Any


class Data(t.TypedDict):
    red_herb: int
    red_potion: int
    updated_at: datetime.datetime
    zenny: int


def echo_data(data: Data) -> None:
    last_now_string = data["updated_at"].strftime("%y-%m-%d %H:%M:%S")
    click.echo(f"Time: {last_now_string}")
    click.echo(f"Zenny: {data['zenny']}")
    click.echo(f"Red Herb: {data['red_herb']}")
    click.echo(f"Red Potion: {data['red_potion']}")


def new_data() -> Data:
    data: Data = {
        "red_herb": 0,
        "red_potion": 0,
        "zenny": 0,
        "updated_at": datetime.datetime.now(),
    }
    return data


def update(data: Data) -> None:
    last_updated_at = data["updated_at"].replace(microsecond=0)
    now = datetime.datetime.now()
    data["updated_at"] = now

    time_passed = now.replace(microsecond=0) - last_updated_at
    steps = int(time_passed.total_seconds())
    data["zenny"] += steps


class State(t.TypedDict):
    data: Data
    data_path: pathlib.Path


def load_state(state: State) -> None:
    data_path = state["data_path"]
    try:
        with data_path.open(encoding="utf-8") as file:
            data = json.load(file)
            data["updated_at"] = datetime.datetime.fromisoformat(data["updated_at"])
    except FileNotFoundError:
        click.echo("File not found: {data_path}")
        return

    state["data"] = data


def new_state() -> State:
    state: State = {"data": new_data(), "data_path": pathlib.Path() / "data.json"}
    return state


def save_state(state: State) -> None:
    data = state["data"]

    data_source: JsonData = data.copy()
    data_source["updated_at"] = data_source["updated_at"].isoformat()
    data_path = state["data_path"]
    with data_path.open("w", encoding="utf-8") as file:
        json.dump(data_source, file)


STATE_META_KEY = ".".join((__name__, "state"))


def pass_state(
    f: cabc.Callable[t.Concatenate[State, _P], _T]
) -> cabc.Callable[t.Concatenate[_P], _T]:
    @click.pass_context  # type: ignore[arg-type]
    def new_func(ctx: click.Context, *args: _P.args, **kwargs: _P.kwargs) -> _T:
        state = ctx.meta[STATE_META_KEY]
        return ctx.invoke(f, state, *args, **kwargs)

    return functools.update_wrapper(new_func, f)


@click.group(invoke_without_command=True)
@click.pass_context
@click.option(
    "--data-path", default="data.json", type=click.Path(path_type=pathlib.Path)
)
def cli(ctx: click.Context, data_path: pathlib.Path) -> None:
    state = ctx.meta[STATE_META_KEY] = new_state()
    state["data_path"] = data_path

    subcommand = ctx.invoked_subcommand
    if subcommand not in {"load", "new"}:  # They create data.
        load_state(state)
    if subcommand is None:
        ctx.invoke(repl)


@cli.command()
@click.pass_context
@pass_state
def load(state: State, ctx: click.Context) -> None:
    load_state(state)
    ctx.invoke(status)


@cli.command()
@pass_state
def new(state: State) -> None:
    data = state["data"] = new_data()
    echo_data(data)


@cli.command()
@click.pass_context
def repl(ctx: click.Context) -> None:
    ctx.invoke(status)
    click_repl.repl(ctx)


@cli.command()
@pass_state
def status(state: State) -> None:
    data = state["data"]
    update(data)
    echo_data(data)


@cli.command()
@click.pass_context
@pass_state
def save(state: State, ctx: click.Context) -> None:
    ctx.invoke(status)
    save_state(state)


def main() -> t.NoReturn:
    cli.main()


if __name__ == "__main__":
    main()
