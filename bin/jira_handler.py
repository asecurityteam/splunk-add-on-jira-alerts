import sys
import json
import requests
import time
from jira import JIRA
from jira_helpers import get_jira_password
import jira_logging as logger


# creates outbound message from alert payload contents
# and attempts to send to the specified endpoint
def send_message(payload):
    config = payload.get('configuration')

    ISSUE_REST_PATH = "/rest/api/latest/issue"
    url = config.get('jira_url')
    jira_url = url + ISSUE_REST_PATH
    username = config.get('jira_username')
    password = get_jira_password(payload.get('server_uri'), payload.get('session_key'))

    # create outbound JSON message body
    body = json.dumps({
        "fields": {
            "project": {
                "key" : config.get('project_key')
            },
            "summary": config.get('summary'),
            "description": config.get('description'),
            "issuetype": {
                "name": config.get('issue_type')
            }
        }
    })

    # create outbound request object
    try:
        headers = {"Content-Type": "application/json"}
        raw_result = requests.post(url=jira_url, data=body, headers=headers, auth=(username, password))
        result = raw_result.json()
        if 'errors' in result.keys():
            logger.error("JIRA server error received, error: %s" % (result['errors']))
    except Exception, e:
        logger.error("Error sending message: %s" % e
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        try:
            # retrieving message payload from splunk
            raw_payload = sys.stdin.read()
            payload = json.loads(raw_payload)

            # pull out the payload
            logger.debug("JSON payload from sendmodalert: %s" % str(payload))

            send_message(payload)
        except Exception, e:
            logger.error("Unexpected error: %s" % e)
            sys.exit(3)
    else:
        logger.error("Unsupported execution mode, expected \'--execute\' flag")
        sys.exit(1)
