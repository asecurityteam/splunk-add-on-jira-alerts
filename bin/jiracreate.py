#!/usr/bin/env python

import sys

from splunklib.searchcommands import \
    dispatch, ReportingCommand, Configuration, Option, validators

from common import fetch_jira, submit_issue
from jira_issue import NewIssue

@Configuration()
class JiraCreateCommand(ReportingCommand):
    """
    """

    # determine if we want to actually send this metric to dd
    send = Option(require=False, default=False, validate=validators.Boolean())
    jira = Option(name="jira", require=False, default='default')

    def get_session_key(self):
        key = getattr(self, "session_key", None)
        if key is None:
            return self._metadata.searchinfo.session_key,

    def map(self, records):
        for r in records:
            yield r

    def reduce(self, records):
        """ Implementation """

        # this could likely be moved into the actual Issue statement.
        try:
            jira = fetch_jira(self.jira, session_key=self.get_session_key())
        except Exception as e:
            yield dict(Exception=str(e))
            return

        payload = {}
        payload['jira_config'] = jira
        for r in records:
            payload.setdefault('results', []).append(r)

        new_issue = NewIssue(payload)
        result = submit_issue(jira, new_issue)

        yield dict(result=result).update(jira)

dispatch(JiraCreateCommand, sys.argv, sys.stdin, sys.stdout, __name__)
