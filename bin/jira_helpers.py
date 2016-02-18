import os
import sys
import requests
import json
import logging

# SPLUNK_HOME = os.environ.get('SPLUNK_HOME')
# BASE_LOG_PATH = os.path.join(SPLUNK_HOME, 'var', 'log', 'splunk')
# BASE_APP_DIR = os.path.join(SPLUNK_HOME, 'etc', 'apps', 'atlassian-add-on-jira')
# APP_LIB_DIR = os.path.join(BASE_APP_DIR, 'bin', 'lib')

# if not APP_LIB_DIR in sys.path:
#     sys.path.append(APP_LIB_DIR)
import jira

def splunkd_auth_header(session_key):
    return {'Authorization': 'Splunk ' + session_key}

def validate_jira_settings(jira_settings):
    url = jira_url(jira_settings, '/myself')
    requests.get(
        url=url,
        auth=(jira_settings.get('jira_username'), jira_settings.get('jira_password')),
        verify=False,
        timeout=10
    ).json()
    return True

def update_jira_settings(jira_settings, server_uri, session_key):
    r = requests.post(
        url=server_uri+'/servicesNS/nobody/atlassian-add-on-jira-alerts/alerts/alert_actions/jira?output_mode=json',
        data={
            'param.jira_url':       jira_settings.get('jira_url'),
            'param.jira_username':  jira_settings.get('jira_username'),
            'param.project_key':    jira_settings.get('project_key', ''),
            'param.issue_type':     jira_settings.get('issue_type', ''),
            'param.summary':        jira_settings.get('summary', ''),
            'param.description':    jira_settings.get('description', ''),
            'param.priority':       jira_settings.get('priority', ''),
            'param.labels':         jira_settings.get('labels', ''),
            'param.attachment':     jira_settings.get('attachment', ''),
            'param.assignee':       jira_settings.get('assignee', ''),
            'param.grouping':       jira_settings.get('grouping', ''),
            'param.group_by':       jira_settings.get('group_by', ''),
            'param.link':           jira_settings.get('link', ''),
            'param.comment':        jira_settings.get('comment', '')
        },
        headers=splunkd_auth_header(session_key),
        verify=False).json()
    requests.post(
        url=server_uri + '/servicesNS/nobody/atlassian-add-on-jira-alerts/storage/passwords/%3Ajira_password%3A?output_mode=json',
        data={
            'password': jira_settings.get('jira_password')
        },
        headers=splunkd_auth_header(session_key),
        verify=False)

def update_jira_dialog(content, server_uri, session_key):
    uri = server_uri + '/servicesNS/nobody/atlassian-add-on-jira-alerts/data/ui/alerts/jira'
    requests.post(url=uri, data={'eai:data': content}, headers=splunkd_auth_header(session_key), verify=False)

def get_jira_settings(server_uri, session_key):
    result = dict()
    for k,v in get_jira_action_config(server_uri, session_key).items():
        if k.startswith('param.'):
            result[k[len('param.'):]] = v
    result['jira_password'] = get_jira_password(server_uri, session_key)
    return result

def get_jira_password(server_uri, session_key):
    password_url = server_uri + '/servicesNS/nobody/atlassian-add-on-jira-alerts/storage/passwords/%3Ajira_password%3A?output_mode=json'

    try:
        # attempting to retrieve cleartext password, disabling SSL verification for practical reasons
        result = requests.get(url=password_url, headers=splunkd_auth_header(session_key), verify=False)
        if result.status_code != 200:
            print >> sys.stderr, "ERROR Fetching password via Splunk REST API: %s" % str(result.json())
            return False
        else:
            splunk_response = json.loads(result.text)
            # logger.debug(splunk_response)
            jira_password = splunk_response.get("entry")[0].get("content").get("clear_password")
    except KeyError, e:
        print >> sys.stderr, "No password found at given REST API endpoint, exception=%s" % e
        return False
    except Exception, e:
        print >> sys.stderr, "ERROR Error retrieving password, exception=%s" % e
        return False

    return jira_password

def get_jira_username(server_uri, session_key):
    return get_jira_action_config(server_uri, session_key).get('jira_username')

def get_jira_action_config(server_uri, session_key):
    url = server_uri + '/servicesNS/nobody/atlassian-add-on-jira-alerts/alerts/alert_actions/jira?output_mode=json'
    result = requests.get(url=url, headers=splunkd_auth_header(session_key), verify=False)
    return json.loads(result.text)['entry'][0]['content']

def jira_url(jira_settings, endpoint):
    return '%s/rest/api/latest%s' % (jira_settings.get('jira_url'), endpoint)

def get_jira_connection(jira_config):
    """Open a connection to the specified JIRA server; return it or False if anything else happens."""

    try:
        options = {'server': jira_config['jira_url']}
        basic_auth = (jira_config['jira_username'], jira_config['jira_password'])

        return jira.JIRA(options=options, basic_auth=basic_auth)
    # should check here for UNAUTHORIZED problems... 'x-seraph-loginreason': 'AUTHENTICATED_FAILED'
    except Exception, e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print >> sys.stderr, 'exception="%s" object="%s" line=%s message="%s"' % (exc_type, exc_obj, exc_tb.tb_lineno, 'Unexpected exception seen connecting to JIRA server')
        return False
