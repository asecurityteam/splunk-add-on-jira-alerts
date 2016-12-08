import os
import sys
import json
import requests
import time
from jira_splunk import *
import logging, logging.handlers

SPLUNK_HOME = os.environ.get('SPLUNK_HOME')

# set logging:
logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(formatter)
logging.root.addHandler(handler)

# creates outbound message from alert payload contents
# and attempts to send to the specified endpoint
def process_alert(payload):

    # logging.debug("Original JSON payload received from sendmodalert, payload=%s" % str(payload))

    # get the config for handling the triggered alert
    jira_config = get_jira_settings(payload['server_uri'], payload['session_key'])

    # WARNING - this will dump your plaintext password to Splunk's _internal index
    # logging.debug("JIRA config initialised jira_config=%s" % str(jira_config))

    # get alert object from results
    new_event = jira_issue.NewIssue(payload)

    # open a new JIRA server connection
    jconn = get_jira_connection(jira_config)

    if new_event:
        logging.info('Built new JIRA Issue object from Splunk alert, search_name="%s" sid="%s"' % (new_event.search_name, new_event.sid))
        # logging.debug("New JIRA-ready event for REST API, new_event=%s" % new_event.__dict__)
    else:
        logging.warn("Unable to create JIRA Issue object from Splunk alert")

    if new_event.ancestor:
        # new_issue.update_issue(jconn)
        pass
    else:
        new_issue = new_event.become_issue(jconn)

        # ignore linking errors for now
        linked_results = new_event.link_issue(jconn)

        if jira_config.get('attachment'):
            # ignore attachment errors for now
            attached_results = new_event.attach_results(jconn)

        if new_issue:
            logging.info('action=%s sid="%s" id="%s" key="%s" summary="%s" issuetype="%s" event_hash="%s" message="%s"' % ('create', new_event.sid, new_issue.id, new_issue.key, new_issue.fields.summary, new_issue.fields.issuetype, new_event.event_hash, 'Created new JIRA issue successfully'))
        else:
            logging.debug('Failed to create new JIRA issue, exiting. search_name="%s" sid="%s"' % (new_event.search_name, new_event.sid))
            sys.exit(2)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        try:
            # retrieving message payload from splunk
            raw_payload = sys.stdin.read()
            payload = json.loads(raw_payload)
            # pull out the payload
            process_alert(payload)
        except Exception, e:
            logging.exception('')
            # print >> sys.stderr, 'error="%s" message="%s"' % (str(e), 'Unable to fully process alert, exiting')
            sys.exit(3)
    else:
        logging.error('Unsupported execution mode, expected --execute flag')
        sys.exit(1)
