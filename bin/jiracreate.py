#!/usr/bin/env python

import sys

from splunklib.searchcommands import \
    dispatch, ReportingCommand, Configuration, Option, validators


@Configuration()
class JiraCreateCommand(ReportingCommand):
    """
    """

    # determine if we want to actually send this metric to dd
    send = Option(require=False, default=False, validate=validators.Boolean())
    jira = Option(name="jira", require=False, default=None)

    def get_session_key(self):
        key = getattr(self, "session_key", None)
        if key is None:
            return self._metadata.searchinfo.session_key,

    def map(self, records):
        for r in records:
            yield r

    def reduce(self, records):
        """ Implementation """
        for r in records:
            yield r

dispatch(JiraCreateCommand, sys.argv, sys.stdin, sys.stdout, __name__)
