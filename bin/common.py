# contains common logic for our report commands


def fetch_jira(jira_name, session_key):
 
    # includes are here to avoid errors including when running tests
    import splunk.entity
    import splunk.Intersplunk

    jira_params = splunk.entity.getEntity('/admin/jiras',
                                          jira_name,
                                          namespace='atlassian-add-on-jira-alerts',
                                          sessionKey=session_key,
                                          owner='nobody')
    if not jira_params:
        raise RuntimeError("Failed to find jira instance in our list")
    return jira_params


def submit_issue(jira, issue):
    pass