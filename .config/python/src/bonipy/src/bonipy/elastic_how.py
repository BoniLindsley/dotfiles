#!/usr/bin/env python3

# Standard libraries.
import logging
import sys

# External dependencies.
import elasticsearch as es


_logger = logging.getLogger(__name__)


def set_up_server() -> None:
    client = es.Elasticsearch("http://localhost:9200")

    index = "index001"
    if index not in client.indices.get(index="*"):
        client.indices.create(index=index)

    document_id = "document001001"
    client.index(index=index, id=document_id, document={"foo": "foo", "bar": "bar2"})
    print(client.get(index=index, id=document_id)["_source"])
    client.update(index=index, id=document_id, doc={"foo": "foo2"})
    print(client.get(index=index, id=document_id)["_source"])

    print(client.search(index=index, query={"match": {"foo": "foo2"}}))


def main() -> int:
    _logger.setLevel(level=logging.DEBUG)
    set_up_server()
    return 0


if __name__ == "__main__":
    sys.exit(main())
