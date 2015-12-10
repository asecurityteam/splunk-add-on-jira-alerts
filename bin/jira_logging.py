import sys, os
import logging, logging.handlers
import datetime

def get_logger(level, process_name='alert'):
    """ Setup a logging for a provided process name, i.e. my_script.py or my_app.
    Provide a logging level to set as well. """

    SPLUNK_HOME = os.environ.get('SPLUNK_HOME')
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')

    target = 'jira_' + process_name
    logger = logging.getLogger(target)
    lf = target + '.log'
    fh = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, lf), mode='a', maxBytes=25000000)
    formatter = logging.Formatter("%(asctime)-15s %(levelname)-5s %(module)s:%(lineno)d - %(message)s")
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.setLevel(level)

    return logger

# def log(msg):
#     pass

# def debug(msg):
#     pass

# def addAlertToCollection(results, issue, sessionKey):

#     try:
#     # since this alert was not previously processed, we will add it in to the collection
#         alerts_entry = {}
#         alerts_entry['search_id'] = results['sid']
#         alerts_entry['search_name'] = results['savedsearch_name']
#         alerts_entry['processed'] = True
#         alerts_entry['event_hash'] = results['event_hash']
#         alerts_entry['ttl'] = results['job_data']['ttl']
#         alerts_entry['trigger_time'] = results['trigger_time']
#         alerts_entry['keywords'] = results['keywords']
#         alerts_entry['event_count'] = results['event_count']
#         alerts_entry['result_count'] = results['result_count']

#         try:
#             # something went wrong here.
#             alerts_entry['issue_key'] = issue.key
#         except AttributeError:
#             # logr.debug('action=%s alerts_entry="%s" issue="%s" message="%s"' % ('trace', str(alerts_entry), str(issue), 'unable to access issue.key'))
#             alerts_entry['issue_key'] = issue['key']
#             alerts_entry['processed'] = True

#         # first add alerts to collections ...
#         alert_entry_uri = '/servicesNS/nobody/jira/storage/collections/data/alerts/'
#         serverResponse, serverContent = rest.simpleRequest(alert_entry_uri, sessionKey=sessionKey, jsonargs=json.dumps(alerts_entry))

#         new_alert = json.loads(serverContent)

#         alerts_entry['_key'] = new_alert['_key']

#         return alerts_entry

#     except Exception, e:
#         return False
#         # import traceback
#         # stack =  traceback.format_exc()
#         # logr.warn('action=%s message="%s"' % ('runtime', 'Unexpected exception seen processing saved searches'))
#         # logr.debug('action=%s exception="%s" message="%s"' % ('runtime', str(e), 'Unexpected exception processing alert'))
#         # logr.debug('action=%s stacktrace="%s" message="%s"' % ('runtime', stack, 'Unexpected exception'))


# def logCreateIssue(alerts_entry, issues_entry, index, sessionKey):

#     try:

#         # should update this to use server.conf or even inputs.conf
#         hostname = socket.gethostname()

#         # some timing things
#         # now = datetime.datetime.now()
#         # expires = datetime.datetime.fromtimestamp(alerts_entry['trigger_time'] + alerts_entry['ttl'])
#         # ttl = (expires - now).total_seconds()

#         event_str = (
#             'time="{time}" action="{action}" search_name="{search_name}" '
#             'project="{project}" key="{key}" issuetype="{issuetype}" labels="{labels}" '
#             'summary="{summary}" search_id="{search_id}" event_hash="{event_hash}" '
#             'keywords="{keywords}" group_by_field="{group_by_field}" '
#             'result_count="{result_count}" event_count="{event_count}" '
#             'update_count="{update_count}" ttl="{ttl}"'
#             )
#         event_vars = {
#             'time': now.strftime("%Y-%m-%d %H:%M:%S %Z"),
#             'action': 'create',
#             'search_name': issues_entry['search_name'],
#             'project': issues_entry['project'],
#             'key': issues_entry['key'],
#             'issuetype': issues_entry['issuetype'],
#             'labels': issues_entry['labels'],
#             'summary': issues_entry['summary'],
#             'search_id': issues_entry['search_id'][-40:],
#             'event_hash': issues_entry['event_hash'],
#             'keywords': alerts_entry['keywords'],
#             'group_by_field': issues_entry['group_by_field'],
#             'result_count': alerts_entry['result_count'],
#             'event_count': alerts_entry['event_count'],
#             'update_count': issues_entry['update_count'],
#             'ttl': issues_entry['ttl']
#             }

#         event = event_str.format(**event_vars)

#         input.submit(event, hostname = hostname, sourcetype = 'jira_issue', source = 'jira_handler.py', index = index )

#         return event

#     except Exception, e:
#         return False
#         import traceback
#         stack =  traceback.format_exc()
#         # logr.warn('action=%s message="%s"' % ('trace', 'Unexpected exception seen logging new issue'))
#         # logr.debug('action=%s exception="%s" message="%s"' % ('trace', str(e), 'Unexpected exception processing alert'))
#         # logr.debug('action=%s stacktrace="%s" message="%s"' % ('trace', stack, 'Unexpected exception'))


# def logUpdateIssue(alerts_entry, ancestor, index, sessionKey):
#     try:

#         # should update this to use server.conf or even inputs.conf
#         hostname = socket.gethostname()

#         # some timing things
#         now = datetime.datetime.now()
#         expires = datetime.datetime.fromtimestamp(ancestor['trigger_time'] + ancestor['ttl'])
#         ttl = (expires - now).total_seconds()

#         event_str = (
#             'time="{time}" action="{action}" search_name="{search_name}" '
#             'project="{project}" key="{key}" issuetype="{issuetype}" labels="{labels}" '
#             'summary="{summary}" search_id="{search_id}" event_hash="{event_hash}" '
#             'keywords="{keywords}" group_by_field="{group_by_field}" '
#             'result_count="{result_count}" event_count="{event_count}" '
#             'update_count="{update_count}" ttl="{ttl}"'
#             )
#         event_vars = {
#             'time': now.strftime("%Y-%m-%d %H:%M:%S %Z"),
#             'action': 'update',
#             'search_name': ancestor['search_name'],
#             'project': ancestor['project'],
#             'key': ancestor['key'],
#             'issuetype': ancestor['issuetype'],
#             'labels': ancestor['labels'],
#             'summary': ancestor['summary'],
#             'search_id': ancestor['search_id'][-40:],
#             'event_hash': ancestor['event_hash'],
#             'keywords': alerts_entry['keywords'],
#             'group_by_field': ancestor['group_by_field'],
#             'result_count': ancestor['result_count'],
#             'event_count': ancestor['event_count'],
#             'update_count': ancestor['update_count'],
#             'ttl': ttl
#             }

#         event = event_str.format(**event_vars)

#         input.submit(event, hostname = hostname, sourcetype = 'jira_issue', source = 'jira_handler.py', index = index )

#         return event

#     except Exception, e:
#         return False
#         import traceback
#         stack =  traceback.format_exc()
#         # logr.warn('action=%s message="%s"' % ('trace', 'Unexpected exception seen logging new issue'))
#         # logr.debug('action=%s exception="%s" message="%s"' % ('trace', str(e), 'Unexpected exception processing alert'))
#         # logr.debug('action=%s stacktrace="%s" message="%s"' % ('trace', stack, 'Unexpected exception'))
