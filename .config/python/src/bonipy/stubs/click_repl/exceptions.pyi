#!/usr/bin/env python3

class InternalCommandException(Exception): ...
class ExitReplException(InternalCommandException): ...
