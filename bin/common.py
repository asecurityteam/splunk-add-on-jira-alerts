# contains common logic for our report commands

from jira_helpers import get_jira_connection

PARAMETERS = ['jira_url',
              'jira_username',
              'jira_password',
              'issue_type',
              'project_key',
              'description',
              'priority',
              'labels',
              'assignee',
              'owner',
              'sid',
              'app',
              'title',
              'attachment']


def build_jira_config(command, params):
    """Take a report command and the jira parameters"""
    config = {}
    for name, value in params.items():
        if name.startswith("default_"):
            name = name[8:]

        if name in PARAMETERS:
            attribute_value = getattr(command, name, None)
            value = attribute_value or value
            if value is not None:
                config[name] = value
    return config


def fetch_jira(command, session_key):
    # includes are here to avoid errors including when running tests
    import splunk.entity
    import splunk.Intersplunk

    jira_name = command.jira

    jira_params = splunk.entity.getEntity('/admin/jiras',
                                          jira_name,
                                          namespace='atlassian-add-on-jira-alerts',
                                          sessionKey=session_key,
                                          owner='nobody')
    if not jira_params:
        raise RuntimeError("Failed to find jira instance in our list")
    return build_jira_config(command, jira_params)



def submit_issue(issue):
    jconn = get_jira_connection(issue.jira_config)
    result = issue.become_issue(jconn)
    return (result, issue.status)