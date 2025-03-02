#!/usr/bin/env python3

# Standard libraries.
import argparse
import contextlib
import logging
import pathlib
import sys
import typing

from typing import Generator, List, Union

# External dependencies.
import matplotlib.pyplot as plt
import platformdirs
import sklearn  # type: ignore[import-untyped]
import torch
from torch import nn
import torchvision  # type: ignore[import-untyped]


_logger = logging.getLogger(__name__)
LOGGING_ALL = 1
LOGGING_TRACE = 5


def set_up_logging(*, logger: logging.Logger) -> None:
    logging.addLevelName(LOGGING_ALL, "ALL")
    logging.addLevelName(LOGGING_TRACE, "TRACE")

    formatter = logging.Formatter(
        datefmt="%Y-%m-%d %H:%M:%S",
        fmt="[{asctime}] [python/{name}] [{levelname[0]}] {message}",
        style="{",
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def set_logger_verbosity(
    *, logger: logging.Logger, verbosity: Union[None, int] = None
) -> None:
    if verbosity is None:
        verbosity = 0

    verbosity_map = {
        -2: logging.CRITICAL,
        -1: logging.ERROR,
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
        3: LOGGING_TRACE,
        4: LOGGING_ALL,
    }
    minimum_verbosity = min(verbosity_map)
    maximum_verbosity = max(verbosity_map)
    verbosity = min(maximum_verbosity, verbosity)
    verbosity = max(minimum_verbosity, verbosity)
    logging_level = verbosity_map.get(verbosity, logging.WARNING)
    logger.setLevel(logging_level)


def add_verbose_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        dest="verbosity",
        help="Incrase verbosity.",
    )


@contextlib.contextmanager
def suppress_keyboard_interrupt() -> Generator[None, None, None]:
    try:
        yield
    except KeyboardInterrupt:
        # Clear line echo-ing "^C".
        print()


class LinearRegressionTraining:

    class Model(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            torch.manual_seed(42)
            self.weights = nn.Parameter(
                torch.randn(1, dtype=torch.float), requires_grad=True
            )
            self.bias = nn.Parameter(
                torch.randn(1, dtype=torch.float), requires_grad=True
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.weights * x + self.bias

    def __init__(self) -> None:
        all_features = torch.arange(start=0, end=1, step=0.02).unsqueeze(dim=1)
        weight = 0.7
        bias = 0.3
        all_labels = weight * all_features + bias
        train_split = int(0.8 * len(all_features))

        self.train_features = all_features[:train_split]
        self.train_labels = all_labels[:train_split]
        self.test_features = all_features[train_split:]
        self.test_labels = all_labels[train_split:]
        self.predictions = all_labels[train_split:]

        self.model = self.Model()

    def plot(self) -> None:
        figure = plt.figure(figsize=(10, 7))
        axes = figure.add_axes((0, 0, 1, 1))
        axes.scatter(self.train_features, self.train_labels, c="b", s=4, label="Train")
        axes.scatter(self.test_features, self.test_labels, c="g", s=4, label="Test")
        axes.scatter(
            self.test_features, self.predictions, c="r", s=4, label="Predictions"
        )
        figure.legend(prop={"size": 14})
        plt.show()

    def predict(self) -> None:
        self.model.eval()
        with torch.inference_mode():
            self.predictions = self.model(self.test_features)

    def run(self) -> None:
        self.train()
        self.predict()
        self.plot()

    def train(self) -> None:
        loss_fn = nn.L1Loss()
        optimizer = torch.optim.SGD(params=self.model.parameters(), lr=0.01)
        for epoch in range(100):
            del epoch
            self.model.train()
            y_pred = self.model(self.train_features)
            loss = loss_fn(y_pred, self.train_labels)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()


class CircleTraining:

    class Model(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            torch.manual_seed(42)
            self.layer_1 = nn.Linear(in_features=2, out_features=10)
            self.layer_2 = nn.Linear(in_features=10, out_features=10)
            self.layer_3 = nn.Linear(in_features=10, out_features=1)
            self.relu = nn.ReLU()

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.layer_3(self.relu(self.layer_2(self.relu(self.layer_1(x)))))  # type: ignore[no-any-return]

    def __init__(self) -> None:
        all_features, all_labels = sklearn.datasets.make_circles(
            n_samples=1000, noise=0.03, random_state=42
        )
        self.all_features = torch.from_numpy(all_features).type(torch.float)
        self.all_labels = torch.from_numpy(all_labels).type(torch.float)
        self.train_features, self.test_features, self.train_labels, self.test_labels = (
            sklearn.model_selection.train_test_split(
                self.all_features,
                self.all_labels,
                test_size=0.2,
                random_state=42,
            )
        )
        self.predictions = self.test_labels
        self.model = self.Model()

    def plot(self) -> None:
        figure = plt.figure(figsize=(12, 6))
        train_axes = figure.add_subplot(1, 3, 1, title="Train")
        train_axes.scatter(
            x=self.train_features[:, 0],
            y=self.train_features[:, 1],
            c=self.train_labels,
            cmap=plt.cm.RdYlBu,  # type: ignore[attr-defined]  # pylint: disable=no-member
        )
        test_axes = figure.add_subplot(1, 3, 2, title="Test")
        test_axes.scatter(
            x=self.test_features[:, 0],
            y=self.test_features[:, 1],
            c=self.test_labels,
            cmap=plt.cm.RdYlBu,  # type: ignore[attr-defined]  # pylint: disable=no-member
        )
        test_axes = figure.add_subplot(1, 3, 3, title="Predictions")
        test_axes.scatter(
            x=self.test_features[:, 0],
            y=self.test_features[:, 1],
            c=self.predictions,
            cmap=plt.cm.RdYlBu,  # type: ignore[attr-defined]  # pylint: disable=no-member
        )
        plt.show()

    def predict(self) -> None:
        self.model.eval()
        with torch.inference_mode():
            test_logits = self.model(self.test_features).squeeze()
            y_pred_probs = torch.sigmoid(test_logits)
            self.predictions = torch.round(y_pred_probs)

    def run(self) -> None:
        self.train()
        self.predict()
        self.plot()

    def train(self) -> None:
        loss_fn = nn.BCEWithLogitsLoss()
        optimizer = torch.optim.SGD(params=self.model.parameters(), lr=0.1)
        for epoch in range(1000):
            del epoch
            self.model.train()
            y_logits = self.model(self.train_features).squeeze()
            loss = loss_fn(y_logits, self.train_labels)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()


class BlobTraining:

    class Model(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            torch.manual_seed(42)
            hidden_units = 8
            input_features = 2
            output_features = 4
            self.linear_layer_stack = nn.Sequential(
                nn.Linear(in_features=input_features, out_features=hidden_units),
                nn.Linear(in_features=hidden_units, out_features=hidden_units),
                nn.Linear(in_features=hidden_units, out_features=output_features),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.linear_layer_stack(x)  # type: ignore[no-any-return]

    def __init__(self) -> None:
        all_features, all_labels = (  # pylint: disable=unbalanced-tuple-unpacking
            sklearn.datasets.make_blobs(
                n_samples=1000,
                n_features=2,
                centers=4,
                cluster_std=1.5,
                random_state=42,
            )
        )
        self.all_features = torch.from_numpy(all_features).type(torch.float)
        self.all_labels = torch.from_numpy(all_labels).type(torch.LongTensor)  # type: ignore[call-overload]
        self.train_features, self.test_features, self.train_labels, self.test_labels = (
            sklearn.model_selection.train_test_split(
                self.all_features,
                self.all_labels,
                test_size=0.2,
                random_state=42,
            )
        )
        self.model = self.Model()
        self.loss_fn = nn.CrossEntropyLoss()
        self.accuracy_score = sklearn.metrics.accuracy_score

    class Prediction(typing.TypedDict):
        features: typing.Any
        labels: typing.Any
        logits: typing.Any

    def plot(self, prediction: Prediction) -> None:
        figure = plt.figure(figsize=(12, 6))
        train_axes = figure.add_subplot(1, 3, 1, title="Train")
        train_axes.scatter(
            x=self.train_features[:, 0],
            y=self.train_features[:, 1],
            c=self.train_labels,
            cmap=plt.cm.RdYlBu,  # type: ignore[attr-defined]  # pylint: disable=no-member
        )
        test_axes = figure.add_subplot(1, 3, 2, title="Test")
        test_axes.scatter(
            x=self.test_features[:, 0],
            y=self.test_features[:, 1],
            c=self.test_labels,
            cmap=plt.cm.RdYlBu,  # type: ignore[attr-defined]  # pylint: disable=no-member
        )
        test_axes = figure.add_subplot(1, 3, 3, title="Predictions")
        test_axes.scatter(
            x=prediction["features"][:, 0],
            y=prediction["features"][:, 1],
            c=prediction["labels"],
            cmap=plt.cm.RdYlBu,  # type: ignore[attr-defined]  # pylint: disable=no-member
        )
        plt.show()

    def predict(self, features: typing.Any) -> Prediction:
        self.model.eval()
        with torch.inference_mode():
            logits = self.model(features)
            probabilities = torch.softmax(logits, dim=1)
            labels = probabilities.argmax(dim=1)
        return {"features": features, "labels": labels, "logits": logits}

    def run(self) -> None:
        self.train()
        prediction = self.predict(self.test_features)
        self.plot(prediction)

    def train(self) -> None:
        optimizer = torch.optim.SGD(params=self.model.parameters(), lr=0.1)
        for epoch in range(100):
            self.model.train()
            train_logits = self.model(self.train_features)
            train_loss = self.loss_fn(train_logits, self.train_labels)
            optimizer.zero_grad()
            train_loss.backward()
            optimizer.step()

            if not epoch % 10:
                train_labels = torch.softmax(train_logits, dim=1).argmax(dim=1)
                train_acc = self.accuracy_score(
                    y_true=self.train_labels, y_pred=train_labels
                )

                prediction = self.predict(self.test_features)
                test_loss = self.loss_fn(prediction["logits"], self.test_labels)
                test_acc = self.accuracy_score(
                    y_true=self.test_labels, y_pred=prediction["labels"]
                )
                print(
                    f"Epoch: {epoch}"
                    f"| Loss: {train_loss:.5f}"
                    f", Acc: {train_acc*100:.2f}%"
                    f"| Test Loss: {test_loss:.5f}"
                    f", Test Acc: {test_acc*100:.2f}%"
                )


class VisionTraining:
    def __init__(self) -> None:
        user_cache_dir = pathlib.Path(
            platformdirs.PlatformDirs(appname="bonipy.torch_how").user_cache_dir
        )
        data_dir = user_cache_dir / "data"
        self.train_data = torchvision.datasets.MNIST(
            root=str(data_dir),
            train=True,
            download=False,
            transform=torchvision.transforms.ToTensor(),
            target_transform=None,
        )
        self.test_data = torchvision.datasets.MNIST(
            root=str(data_dir),
            train=False,
            download=False,
            transform=torchvision.transforms.ToTensor(),
        )

    def plot(self) -> None:
        image_index = 2
        figure = plt.figure(figsize=(12, 6))
        axes = figure.add_axes((0, 0, 1, 1), title=self.train_data[image_index][1])
        axes.imshow(self.train_data[image_index][0].squeeze())
        plt.show()

    def run(self) -> None:
        # self.train()
        # self.predict()
        self.plot()


# Reference: https://www.learnpytorch.io/03_pytorch_computer_vision/
# Reference: https://www.learnpytorch.io/03_pytorch_computer_vision/#2-prepare-dataloader


def run() -> int:
    _logger.debug("Using PyTorch version %s", torch.__version__)
    _logger.debug("Using PyTorch vision version %s", torchvision.__version__)
    # LinearRegressionTraining().run()
    # CircleTraining().run()
    # BlobTraining().run()
    VisionTraining().run()
    return 0


def parse_arguments(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_verbose_flag(parser)
    return parser.parse_args(args)


@suppress_keyboard_interrupt()
def main(argv: Union[None, List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv

    set_up_logging(logger=_logger)

    arguments = parse_arguments(argv[1:])
    set_logger_verbosity(logger=_logger, verbosity=arguments.verbosity)

    return run()


if __name__ == "__main__":
    sys.exit(main())
