import os
import sys
import urllib
import json
import splunk
import splunk.rest as rest
import splunk.input as input
import splunk.entity as entity
import time
import hashlib
import datetime
import socket
import logging

# establish a starting time for the script
start = time.time()

SPLUNK_HOME = os.environ.get('SPLUNK_HOME')
BASE_LOG_PATH = os.path.join(SPLUNK_HOME, 'var', 'log', 'splunk')

BASE_APP_DIR = os.path.join(SPLUNK_HOME, 'etc', 'apps', 'atlassian-add-on-jira')

APP_BIN_DIR = os.path.join(BASE_APP_DIR, 'bin')
APP_LIB_DIR = os.path.join(BASE_APP_DIR, 'bin', 'lib')

if not APP_LIB_DIR in sys.path:
    sys.path.append(APP_LIB_DIR)


# Setup logging
# import jira_logging
# log_level = logger.DEBUG
# logr = jira_logger.get_logger(logger.DEBUG, 'scheduler')


log_level = logger.DEBUG
logr = logger.getLogger(__name__)
lf = 'jira_scheduler' + '.log'
fh = logger.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, lf), mode='a', maxBytes=25000000)
formatter = logger.Formatter("%(asctime)-15s %(levelname)-5s %(module)s:%(lineno)d - %(message)s")
fh.setFormatter(formatter)
logr.addHandler(fh)
logr.setLevel(log_level)

# custom JIRA libs
import jira_handler

sessionKey = ''

# grab a sessionKey for Splunk REST access
sessionKey = sys.stdin.readline().strip()
splunk.setDefault('sessionKey', sessionKey)

# Look for saved searches to scrape fired_alerts from
ss_query = {}
ss_query['run_alert_script'] = True

uri = '/servicesNS/nobody/jira/storage/collections/data/issue_settings?query=%s' % urllib.quote(json.dumps(ss_query))
serverResponse, serverContent = rest.simpleRequest(uri, sessionKey=sessionKey)

# Grab saved searches to work with from Issue Settings config
saved_searches = json.loads(serverContent)

num_searches = 0
num_alerts = 0

if len(saved_searches) > 0:

    # logr.debug('action=%s num_searches=%s message="%s"' % ('query', len(saved_searches), 'found saved searches with alerts to process from fired_alerts'))
    # logger.debug('action=%s saved_searches="%s" message="%s"' % ('trace', str(saved_searches), 'dump of saved searches to work with'))

    for search in saved_searches:
        num_searches += 1

        uri = '/servicesNS/nobody/%s/alerts/fired_alerts/%s?output_mode=json' % (search['app_name'], urllib.quote(search['search_name']))

        serverResponse, serverContent = rest.simpleRequest(uri, sessionKey=sessionKey)
        fired_alerts = json.loads(serverContent)

        if len(fired_alerts['entry']) > 0:
            logr.info('action=%s num_fired_alerts=%s search_name="%s" message="%s"' % ('query', len(fired_alerts['entry']), search['search_name'], 'found search results in list fired_alerts'))

            # process new events
            for alert in fired_alerts['entry']:
                try:
                    # Send alert to jira_handler to process
                    process_result = jira_handler.processAlert(alert, search, sessionKey)
                except Exception, e:
                    import traceback
                    stack =  traceback.format_exc()
                    exc_type, exc_obj, exc_tb = sys.exc_info()

                    logr.error('action=%s error="%s" object="%s" line=%s message="%s"' % ('runtime', exc_type, exc_obj, exc_tb.tb_lineno, 'Unexpected exception seen processing alerts'))
                    logr.warn('action=%s stacktrace="%s" message="%s"' % ('runtime', stack, 'Unexpected exception'))

                if process_result:
                    logr.debug('action=%s search_name="%s" sid=%s message="%s"' % ('process_alert', search['search_name'], alert['content']['sid'], 'finished processing alert successfully'))
                    num_alerts += 1

        else:
            logr.debug('action=%s num_fired_alerts=%s search_name="%s" message="%s"' % ('query', len(fired_alerts), search['search_name'], 'no search results found in fired_alerts'))

else:
    logr.warn('action=%s num_searches=%s message="%s"' % ('query', len(saved_searches), 'no saved searches found, check the Issue Settings to enable JIRA handler to pull saved searches.'))

end = time.time()
duration = round((end-start), 3)
logr.info('action=%s num_searches=%s num_alerts=%s duration=%ss message="%s"' % ('runtime', num_searches, num_alerts, duration, 'scheduler finished'))
