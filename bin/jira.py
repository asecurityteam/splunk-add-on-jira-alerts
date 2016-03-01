import os
import sys
import json
import requests
import time
from jira_helpers import get_jira_settings, get_jira_connection
# from jira_formatters import get_description, get_comment
import logging, logging.handlers
import jira_issue

SPLUNK_HOME = os.environ.get('SPLUNK_HOME')
BASE_LOG_PATH = os.path.join(SPLUNK_HOME, 'var', 'log', 'splunk')
# BASE_APP_DIR = os.path.join(SPLUNK_HOME, 'etc', 'apps', 'atlassian-add-on-jira')
# APP_LIB_DIR = os.path.join(BASE_APP_DIR, 'bin', 'lib')
# if not APP_LIB_DIR in sys.path:
#     sys.path.append(APP_LIB_DIR)


def get_logger(process_name = 'jira_alert', logging_level = logging.DEBUG):
    logger = logging.getLogger(process_name)
    fh = logging.handlers.RotatingFileHandler(os.path.join(BASE_LOG_PATH, process_name + '.log'), maxBytes=25000000, backupCount=2)
    formatter = logging.Formatter("log_level=%(levelname)-5s process=%(processName)s %(funcName)s:%(lineno)d %(message)s")
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel(logging_level)
    logger.propagate = False
    return logger

# creates outbound message from alert payload contents
# and attempts to send to the specified endpoint
def process_alert(payload):
    logger = get_logger()

    # logger.debug("Original JSON payload received from sendmodalert, payload=%s" % str(payload))

    # get the config for handling the triggered alert
    jira_config = get_jira_settings(payload['server_uri'], payload['session_key'])

    # WARNING - this will dump your plaintext password to Splunk's _internal index
    # logger.debug("JIRA config initialised jira_config=%s" % str(jira_config))

    # get alert object from results
    new_event = jira_issue.NewIssue(payload)
    # logger.debug("Built new JIRA conn jconn=%s" % new_event.__dict__)

    # open a new JIRA server connection
    jconn = get_jira_connection(jira_config)

    if new_event:
        logger.info('Built new JIRA Issue object from Splunk alert, search_name="%s" sid="%s"' % (new_event.search_name, new_event.sid))
        # logger.debug("New JIRA-ready event for REST API, new_event=%s" % new_event.__dict__)
    else:
        logger.warn("Unable to create JIRA Issue object from Splunk alert")

    if new_event.ancestor:
        # new_issue.update_issue(jconn)
        pass
    else:
        new_issue = new_event.become_issue(jconn)

        # ignore linking errors for now
        linked_results = new_event.link_issue(jconn)

        if jira_config['attachment']:
            # ignore attachment errors for now
            attached_results = new_event.attach_results(jconn)

        if new_issue:
            logger.info('action=%s sid="%s" id="%s" key="%s" summary="%s" issuetype="%s" event_hash="%s" message="%s"' % ('create', new_event.sid, new_issue.id, new_issue.key, new_issue.fields.summary, new_issue.fields.issuetype, new_event.event_hash, 'Created new JIRA issue successfully'))
        else:
            logger.debug('Failed to create new JIRA issue, exiting. search_name="%s" sid="%s"' % (new_event.search_name, new_event.sid))
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
            print >> sys.stderr, 'error="%s" message="%s"' % (str(e), 'Unable to fully process alert, exiting')
            sys.exit(3)
    else:
        print >> sys.stderr, "Unsupported execution mode, expected --execute flag"
        sys.exit(1)
