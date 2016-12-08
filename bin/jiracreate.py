#!/usr/bin/env python

import sys

from splunklib.searchcommands import \
    dispatch, ReportingCommand, Configuration, Option, validators

from common import fetch_jira, submit_issue
from jira_issue import NewIssue

import logging
logger = logging.getLogger('JiraCreateCommand')


@Configuration()
class JiraCreateCommand(ReportingCommand):
    """
    """

    # determine if we want to actually send this metric to dd
    send = Option(require=False, default=False, validate=validators.Boolean())
    jira = Option(name="jira", require=False, default='default')

    def get_owner(self):
        owner = getattr(self, "owner", None)
        return owner or self._metadata.searchinfo.owner

    def get_sid(self):
        sid = getattr(self, "sid", None)
        return sid or self._metadata.searchinfo.sid

    def get_session_key(self):
        key = getattr(self, "session_key", None)
        return key or self._metadata.searchinfo.session_key

    def get_app(self):
        app = getattr(self, "app", None)
        return app or self._metadata.searchinfo.app

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

        config = {}
        for name,value in jira.items():
            if name.startswith("default_"):
                name = name[8:]
            config[name] = value


        payload = {}
        payload['configuration'] = config
        payload['owner'] = self.get_owner()
        payload['sid'] = self.get_sid()
        payload['app'] = self.get_app()

        results = []
        for record in records:
            results.append(record)

        #payload['results'] = dict(results=results)
        # [OrderedDict([('_time', '1481165299.186'), ('count', '1')])
        payload['session_key'] = self.get_session_key()
    
        #import json
        #with open("/tmp/splunk-self.json", "w") as f:
        #    json.dump(self.search_results_info, f)

        #with open("/tmp/splunk-records.json", "w") as f:
        #    json.dump(results, f)

        new_issue = NewIssue(payload)
        assert new_issue.issuetype
        ticket, status = submit_issue(jira, new_issue)

        row = dict()
        if ticket:
            row['ticket'] = ticket.key
        row['status'] = status
        row.update(new_issue.jira_config)
        yield row

        #yield dict(result=result).update(new_issue.jira_config)

dispatch(JiraCreateCommand, sys.argv, sys.stdin, sys.stdout, __name__)
