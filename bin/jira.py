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
    logger.debug("JIRA config initialised jira_config=%s" % str(jira_config))

    # get alert object from results
    new_event = jira_issue.NewIssue(payload)
    # logger.debug("Built new JIRA conn jconn=%s" % new_event.__dict__)

    # open a new JIRA server connection
    jconn = get_jira_connection(jira_config)

    if new_event:
        logger.info('Built new JIRA Issue object from Splunk alert, search_name="%s" sid="%s"' % (new_event.search_name, new_event.sid))
        # logger.debug("Built new JIRA Issue object from Splunk alert new_event=%s" % str(new_event))
    else:
        logger.warn("Unable to create JIRA Issue object from Splunk alert")

    if new_event.ancestor:
        # new_issue.update_issue(jconn)
        pass
    else:
        new_issue = new_event.become_issue(jconn)

        if new_issue:
            logger.info('action=%s issue_id=%s summary="%s" issuetype="%s" message="%s"' % ('create', new_issue.id, new_issue.fields.summary, new_issue.fields.issuetype, 'Created new JIRA issue successfully'))
            logger.debug('action=%s issue_id=%s fields="%s" message="%s"' % ('create', new_issue.fields, new_issue.fields.issuetype, 'Created new JIRA issue successfully'))
                        # actions to add:
            ## 1 add results as CSV attachment
            #
            ## 2 add issue data to collection of open issues
            self.key = new_issue.key
            ## 3 log Splunk event to alerts index

if __name__ == "__main__":

    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        try:
            # retrieving message payload from splunk
            raw_payload = sys.stdin.read()
            payload = json.loads(raw_payload)
            # pull out the payload
            process_alert(payload)
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print >> sys.stderr, 'exception="%s" object="%s" line=%s message="%s"' % (exc_type, exc_obj, exc_tb.tb_lineno, 'Unexpected exception seen processing alert')
            sys.exit(3)
    else:
        print >> sys.stderr, "Unsupported execution mode, expected --execute flag"
        sys.exit(1)
