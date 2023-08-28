#!/usr/bin/env python

# Standard libraries.
import os
import pathlib
import platform
import sys
import venv

# External dependencies.
import bonipy.repl


class SetupPython:
    @classmethod
    def get_broken_app_list(cls) -> "list[str]":
        return [
            "khal",  # CLI/TUI CalDAV dir viewer. # Broken dependency.
            "mps-youtube",  # Youtube search TUI  # Superceded by yewtube.
            "tartube",  # GUI for yt-dlp. Broken dependency.
            "todoman",  # CLI/TUI CalDAV todo viewer. # Broken dependency.
            "ttrv",  # TUI Reddit. # Removed from PyPI.
            "youtube-dl",  # Video downloader  # Unmaintained.
        ]

    @classmethod
    def get_unused_app_list(cls) -> "list[str]":
        return [
            "ansible",  # Configuration deployment. Breaks apt manual/auto.
            "cookiecutter",  # CLI to create project templates.
            "i3pystatus",  # i3 bar # 'git+https://github.com/enkore/i3pystatus.git'
            "pymap",  # IMAP server. Uses asyncio.
            "ranger-fm",  # File manager TUI  # Might be easier to use vim.
            "rss2email",  # RSS feed downloader.
            "topydo[columns,ical,prompt]",  # CLI/CMD/TUI Todo.txt tool.
            "vdirsyncer[google]",  # CLI CalDAV synchronize.
        ]

    @classmethod
    def get_app_list(cls) -> "list[str]":
        return [
            "mintotp",  # OTP CLI.
            "pelican[markdown]",  # Static website generator
            "pip",  # Python package manager
            "pipx",  # Python application dependency isolation.
            "pulsemixer",  # PulseAudio control TUI
            "rainbowstream",  # Twitter TUI.  # Requires Twitter account.
            "rtv",  # TUI Reddit.
            "streamlink",  # Live video viewer. # Requires python3-pycountry
            "yewtube",  # Youtube search TUI
            "yt-dlp",  # Video downloader
        ]

    @classmethod
    def get_unused_library_list(cls) -> "list[str]":
        library_packages = [
            "IMAPClient",  # IMAP protocol library
            "Importmagic",  # Automatically manage imports.
            "PySide6",  # GUI library.
            "asciimatics",  # TUI library.
            "beancount",  # Library for argument parsing.
            "colour",
            "epc",  # Emacs RPC stack.
            "keyring",  # Password storage.
            "myst-parser",  # Markdown parser. For Sphinx.
            "netifaces",  # For network traffic.
            "psutil",  # For computer metrics.
            "pydantic",  # Data validation
            "textual",  # TUI library.
            "virtualenv",  # Separate packaging
        ]
        if platform.system() == "Windows":
            library_packages.append("windows-curses")

        # if platform.system() != "Windows":
        #     library_packages.extend(
        #         (
        #             "basiciw",  # For displaying wireless details. Requires libiw-dev
        #             "sagecipher",  # Password storage using ssh. Compiling difficult.
        #         )
        #     )
        return library_packages

    @classmethod
    def get_library_list(cls) -> "list[str]":
        return [
            "Markdown",  # Parser library.
            "appdirs",  # Default directories by convention.
            "click",  # Library for argument parsing.
            "click-repl",  # Library for interactive prompt.
            "portalocker",  # Exclusive file access.
            "requests",  # HTTP client library.
            "types-Markdown",  # Library type hint.
            "types-appdirs",  # Library type hint.
            "types-requests",  # Library type hint.
            "watchdog",  # File monitoring library
        ]

    @classmethod
    def get_unused_tools_list(cls) -> "list[str]":
        return [
            "autopep8",  # Code formatter. Prefer Black.
            "build",  # Creates packages for PyPI.
            "devpi-server",  # Cache Python PyPI packages.
            "pylsp-mypy",  # LSP plugin for static type checking.
            "python-lsp-black",  # LSP plugin for formatting.
            "python-lsp-server[Rope]",  # LSP. Rope for completion.
            "twine",  # Uploads packages to PyPI.
            "yapf",  # Code formatter. Prefer Black.
        ]

    @classmethod
    def get_tools_list(cls) -> "list[str]":
        return [
            "Sphinx",  # Documentation generator.
            "black",  # Code formatter.
            "cmakelang",  # Foramtter with `cmake-format`. `cmake-lint` broken.
            "coverage",  # Test unit test coverage.
            "fprettify",  # Code formatter for Fortran.
            "mypy",  # Static type checker.
            "pipenv",  # Virtual environments based on "${PWD}"
            "pylint",  # Static code analysis.
            "pytest",  # Unit test framework.
            "tox",  # Continuous integration package.
            "types-six",  # Library type hint.
        ]

    @classmethod
    def get_packages(cls) -> "list[str]":
        packages = []
        packages.extend(cls.get_app_list())
        packages.extend(cls.get_library_list())
        packages.extend(cls.get_tools_list())
        packages.sort()
        return packages

    @classmethod
    def get_xdg_lib_home(cls) -> pathlib.Path:
        try:
            return pathlib.Path(os.environ["XDG_LIB_HOME"])
        except KeyError:
            pass

        if platform.system() == "Windows":
            try:
                return pathlib.Path(os.environ["LocalAppData"])
            except KeyError:
                pass

        try:
            return pathlib.Path(os.environ["XDG_LOCAL_HOME"]) / "lib"
        except KeyError:
            pass

        try:
            return pathlib.Path(os.environ["HOME"]) / ".local" / "lib"
        except KeyError:
            pass

        return pathlib.Path()

    @classmethod
    def get_venv_executable(cls) -> pathlib.Path:
        if "VIRTUAL_ENV" in os.environ or sys.prefix != sys.base_prefix:
            return pathlib.Path(sys.executable)
        xdg_lib_home = cls.get_xdg_lib_home()
        venv_path = xdg_lib_home / "python" / "venv" / "default"
        env_builder = venv.EnvBuilder(with_pip=True)
        env_builder.create(venv_path)
        return venv_path / "bin" / "python"

    @classmethod
    def run(cls) -> None:
        python_executable = cls.get_venv_executable()
        packages = cls.get_packages()
        if packages:
            bonipy.repl.oops.execute(
                [
                    str(python_executable),
                    "-m",
                    "pip",
                    "install",
                    "--compile",
                    "--upgrade",
                    *packages,
                ]
            )


setup_python = SetupPython.run
