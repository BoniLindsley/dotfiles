#!/usr/bin/env python3

# Standard libraries
import asyncio
import collections.abc as cabc
import contextlib
import pathlib
import logging
import sys

# External dependencies.
import js  # type: ignore[import-not-found]  # pylint: disable=import-error
import pyodide.ffi  # type: ignore[import-not-found]  # pylint: disable=import-error
import pyodide_js  # type: ignore[import-not-found]  # pylint: disable=import-error


_logger = logging.getLogger(__name__)


@contextlib.contextmanager
def log_exception(*, section_name: str) -> cabc.Iterator[None]:
    # pyscript just freezes if there are exceptions.
    # This is a workaround to at least give some feedback.
    try:
        yield
    except SystemExit as error:
        if error.code:  # pylint: disable=using-constant-test # Not really a constant...
            _logger.warning("End of %s. Exit code: %s", section_name, error.code)
        else:
            _logger.info("End of %s. Exit code: %s", section_name, error.code)
    except Exception as error:
        _logger.critical(
            "Exception from %s: %s with message = %s", section_name, type(error), error
        )
        raise


def mount_indexeddb(target: None | pathlib.Path = None) -> None:
    if target is None:
        target = pathlib.Path("/mnt/idbfs")
    _logger.debug("Mounting IndexedDB to %s", target)
    target.mkdir(exist_ok=True, parents=True)
    pyodide_js.FS.mount(
        pyodide_js.FS.filesystems.IDBFS,
        None,
        str(target),
    )
    _logger.debug("Mounted IndexedDB to %s", target)


async def sync_fs(is_loading: bool) -> object:
    """
    Usage:
    ```py
    mount_indexeddb()
    await sync_fs(True)
    // Use filesysstem with /mnt/idbfs
    await sync_fs(False)
    ```
    """
    if is_loading:
        _logger.debug("Syncing filesystem from storage.")
    else:
        _logger.debug("Syncing filesystem to storage.")
    error_future: asyncio.Future[object] = asyncio.Future()
    pyodide_js.FS.syncfs(is_loading, pyodide.ffi.create_proxy(error_future.set_result))

    error_result = await error_future
    if error_result is not None:
        if is_loading:
            _logger.error("Failed to load data from IndexedDB: %s", error_result)
        else:
            _logger.error("Failed to save data from IndexedDB: %s", error_result)
    return error_future


async def on_mount_idbfs_switch_change(event: pyodide.ffi.JsProxy) -> None:
    mount_idbfs_save = js.document.getElementById("mount-idbfs-save")
    if event.target.checked:
        mount_indexeddb(target=pathlib.Path("/mnt/idbfs"))
        await sync_fs(True)
        mount_idbfs_save.disabled = False
    else:
        await sync_fs(False)
        pyodide_js.FS.unmount("/mnt/idbfs")
        pyodide_js.FS.rmdir("/mnt/idbfs")
        mount_idbfs_save.disabled = True


async def on_mount_idbfs_save(event: pyodide.ffi.JsProxy) -> None:
    del event
    await sync_fs(False)


def create_breadcrumb_item(
    *, new_cwd: pathlib.Path, text: str
) -> pyodide.ffi.JsDomElement:
    document = js.document
    item = document.createElement("li")
    item.classList.add("breadcrumb-item")
    if text:
        button = document.createElement("button")
        button.classList.add("file-browser-breadcrumb-item-button")
        button.type = "button"
        button.value = str(new_cwd)
        button.appendChild(document.createTextNode(text))
        item.appendChild(button)
    return item


def set_file_browser_nav_list_cwd(
    *, cwd: pathlib.Path, nav_list: pyodide.ffi.JsDomElement
) -> None:
    nav_list.replaceChildren()
    nav_list.value = str(cwd)
    cwd_parts = cwd.parts
    text = cwd_parts[0]
    new_cwd = pathlib.Path(text)
    if text == "/":
        text = "MEMFS"

    nav_list.appendChild(create_breadcrumb_item(new_cwd=new_cwd, text=text))

    for text in cwd_parts[1:]:
        new_cwd /= text
        nav_list.appendChild(create_breadcrumb_item(new_cwd=new_cwd, text=text))


def set_file_browser_path(
    *,
    cwd: pathlib.Path,
    file_browser: pyodide.ffi.JsDomElement,
    nav_list: pyodide.ffi.JsDomElement
) -> None:
    set_file_browser_nav_list_cwd(cwd=cwd, nav_list=nav_list)
    new_rows = pyodide.ffi.to_js([[child.name] for child in cwd.iterdir()])
    js.DataTable.Api(file_browser).clear().rows.add(new_rows).draw()


def on_file_browser_nav_list_item_click(event: pyodide.ffi.JsProxy) -> None:
    target = event.target
    if not target.classList.contains("file-browser-breadcrumb-item-button"):
        return
    text = target.value
    target.dispatchEvent(
        js.CustomEvent.new(
            "cd",
            pyodide.ffi.to_js(
                {"bubbles": True, "detail": text},
                dict_converter=js.Object.fromEntries,
            ),
        )
    )


def create_file_browser_nav_list() -> pyodide.ffi.JsDomElement:
    nav_list = js.document.createElement("ol")
    nav_list.classList.add("breadcrumb")
    nav_list.classList.add("file-browser-path")
    pyodide.ffi.wrappers.add_event_listener(
        nav_list, "click", on_file_browser_nav_list_item_click
    )
    return nav_list


@log_exception(section_name="use")
async def use_as_file_browser(
    *, cwd: pathlib.Path, file_browser: pyodide.ffi.JsDomElement
) -> None:
    # Datatable initialisation creates a div where the table is
    # and then moves the table into it.
    # The "dom" element is created inside the same div.
    #
    # ```html
    # <table id="file_browser">
    # ```
    #
    # Becomes
    #
    # ```html
    # <div id="file_browser_wrapper">
    #   <div class="file-browser-toolbar">
    #   <table id="file_browser">
    # ```
    js.DataTable.new(
        file_browser,
        pyodide.ffi.to_js(
            {
                "dom": '<"file-browser-toolbar">t',
                "info": False,
                "paging": False,
                "searching": False,
            },
            dict_converter=js.Object.fromEntries,
        ),
    )

    # Put a nav bar into the "dom" element toolbar.
    #
    # TODO: Delay nav bar creation until datatable is ready.
    #
    # There is a race condition between datatable initialisation
    # so that its toolbar being ready,
    # and element search by class name here.
    # References:
    #
    # *   https://datatables.net/reference/event/init
    # *   https://datatables.net/reference/option/dom
    nav_list = create_file_browser_nav_list()
    nav_bar = js.document.createElement("nav")
    nav_bar.ariaLabel = "breadcrumb"
    nav_bar.appendChild(nav_list)
    nav_div = file_browser.parentNode.getElementsByClassName("file-browser-toolbar")[0]
    nav_div.appendChild(nav_bar)
    del nav_div
    del nav_bar

    # Initialise both nav bar and table content based on given `cwd`.
    # Event callback relies on `nav_list.value` to be initilised at least once in here.
    set_file_browser_path(cwd=cwd, file_browser=file_browser, nav_list=nav_list)

    # Use a common event handler as a way to change file listing.
    def on_wrapper_cd(event: pyodide.ffi.JsProxy) -> None:
        text = event.detail
        new_cwd = pathlib.Path(nav_list.value) / text

        if not new_cwd.is_dir():
            return

        set_file_browser_path(cwd=new_cwd, file_browser=file_browser, nav_list=nav_list)

    pyodide.ffi.wrappers.add_event_listener(
        file_browser.parentNode, "cd", on_wrapper_cd
    )

    # Allow table double click to change into the the clicked directory.
    def on_file_browser_dblclick(event: pyodide.ffi.JsProxy) -> None:
        target = event.target
        if not target.classList.contains("sorting_1"):
            return
        text = js.DataTable.Api(file_browser).row(target).data()[0]
        target.dispatchEvent(
            js.CustomEvent.new(
                "cd",
                pyodide.ffi.to_js(
                    {"bubbles": True, "detail": text},
                    dict_converter=js.Object.fromEntries,
                ),
            )
        )

    pyodide.ffi.wrappers.add_event_listener(
        file_browser, "dblclick", on_file_browser_dblclick
    )


def set_up_logging(*, verbosity: int = 0) -> None:
    all_level = 1
    trace_level = 5

    verbosity_map: dict[int, int] = {
        -2: logging.CRITICAL,
        -1: logging.ERROR,
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
        3: trace_level,
        4: all_level,
    }

    logging.addLevelName(trace_level, "TRACE")
    logging_level = verbosity_map.get(min(4, verbosity))
    logging.basicConfig(level=logging_level)
    _logger.debug("Logging level is set to %d", logging_level)


@log_exception(section_name="async script")
async def amain() -> int:
    mount_idbfs_switch = js.document.getElementById("mount-idbfs-switch")
    pyodide.ffi.wrappers.add_event_listener(
        mount_idbfs_switch, "change", on_mount_idbfs_switch_change
    )
    mount_idbfs_save = js.document.getElementById("mount-idbfs-save")
    pyodide.ffi.wrappers.add_event_listener(
        mount_idbfs_save, "click", on_mount_idbfs_save
    )

    file_browser = js.document.getElementById("file-browser")
    await use_as_file_browser(cwd=pathlib.Path.cwd(), file_browser=file_browser)
    _logger.debug("Done.")
    return 0


task: asyncio.Task[object]


def main() -> int:
    global task
    set_up_logging(verbosity=2)
    # Ideally, this should be `asyncio.run`.
    # Not available in pyscript at the moment.
    # Need to keep the instance alive.
    task = asyncio.create_task(amain())
    return 0


if __name__ == "__main__":
    with log_exception(section_name="main script"):
        sys.exit(main())
