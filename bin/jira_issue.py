import os
import sys
import time
from dateutil.parser import parse
import datetime
import requests
import socket
import json
import splunk.rest as rest
import splunk.input as input
import re
import hashlib
import logging
import jira
import jinja2
from jira_formatters import *

# {% if results['host'] != None %}: ${results['host']}${% endif %}
DEFAULT_SUMMARY = '''${search_name}$'''


# h6. Event Data JIRA
# {% for row in results_jira %}${row}${% endfor %}

DEFAULT_DESCRIPTION = '''h3. ${search_name}$
\\
Event Data ASCII
\\
{noformat}{% for row in results_jira %}${row}${% endfor %}{noformat}
\\
Event Details
\\
{color:#707070}
~*Triggered*: {{${trigger_time_rendered}$}} | *Expires*: {{${expiration_time_rendered}$}} | *\# Results*: {{${result_count}$}} | *\# Events*: {{${event_count}$}} | *Results Link*: {{_[Results|${results_link}$]_}}~
\\
~*Hash*: {{${event_hash}$}} | *Unique Values*: {{${results_unique}$}}~
{color}
\\ \\
Search Query
\\
{color:#707070}~*App Name*: {{${app}$}} | *Owner*: ${owner_rendered}$~{color}
{noformat}${search_string}${noformat}'''

class Issue(object):

    def __init__(self, payload):
        # self.logger = logging.getLogger('jira_alert')
        self.jira_config = payload['configuration']
        self.index = self.jira_config.get('index','_internal')

        self.status = 'new'
        # Splunk event data fields
        self.search_name = payload['search_name']
        self.search_string = ''
        self.owner = payload['owner']
        self.app = payload['app']
        self.sid = payload['sid']
        self.job = None
        self.results = None
        self.results_unique = None
        self.results_simple = payload['result']
        self.results_file = payload['results_file']
        self.results_link = payload['results_link']
        self.trigger_time = ''
        self.trigger_time_rendered = ''
        self.expiration_time_rendered = ''
        self.ttl = ''
        self.keywords = {}
        self.fields = []
        self.event_count = 0
        self.result_count = 0

        # JIRA issue fields
        self.project = self.jira_config.get('project_key','')
        self.key = None
        self.id = None
        self.issuetype = self.jira_config.get('issue_type','')
        self.assignee = None
        self.reporter = None
        self.created = None
        self.updated = None
        self.resolution = None
        self.labels = self.jira_config.get('labels','').split(',')
        self.priority = None # not yet used
        self.summary = self.jira_config.get('summary', DEFAULT_SUMMARY)
        self.description = self.jira_config.get('description', DEFAULT_DESCRIPTION)
        self.comment = self.jira_config.get('comment')

        # Meta fields
        self.hostname = socket.gethostname()  # should eventually update this to use server.conf or even inputs.conf
        self.event_hash = None
        self.ancestor = None
        self.group_by_field = self.jira_config.get('group_by','')
        self.update_count = 0
        self.session_key = payload['session_key']
        self.context = {}

        self.process_results()

    def get_ancestor():
        pass

    def get_event_hash(self):
        '''Generate the event hash based on event data, less any datetime fields.'''
        search_name = self.search_name
        results_data = self.results['results']
        hashable_data = []

        if self.group_by_field in [None, '']:
            hash_fields = self.fields
        else:
            hash_fields = self.group_by_field

        for result in results_data:
            # reduce data set to hash_fields
            hashable_data.append( {k:v for (k,v) in result.iteritems() if k in hash_fields} )

        hash_vals = []
        # create unique set of values
        for hash_val in [v for entry in hashable_data for v in entry.values()]:
            if isinstance(hash_val, list):
                hash_vals.append('_'.join([h for h in hash_val]))
            else:
                hash_vals.append(hash_val)

        hash_set = set( sorted(hash_vals) )

        # convert to a single hashable string
        hash_data =  search_name + '_' + str( '_'.join([item for item in hash_set]) )
        hash_data = hash_data.lower()


        # generate the hash based on the final hash of data, including any unique values in the list of hash_fields.  should end up like:
        # 'Search Name_val1_val2'...
        event_hash = hashlib.md5(hash_data).hexdigest()

        # logr.debug('action=%s search_name=%s hash_fields=%s hash_data=%s event_hash=%s message="%s"' % ('event_hash', search_name, hash_fields, hash_data, event_hash, 'generated event hash for search results'))

        if event_hash:
            return event_hash
        else:
            return False

    def get_keywords(self, keywords):
        kv_matches = {}
        kv_matches_quoted = dict(re.findall(r'\"(.+)::(.+)\"', keywords))
        kv_matches_norm = dict(re.findall(r'(\S+)::(\S+)', keywords))

        if kv_matches_quoted:
            kv_matches.update(kv_matches_quoted)
        if kv_matches_norm:
            kv_matches.update(kv_matches_norm)

        return kv_matches

    def get_results(self):
        try:
            job_uri = '/servicesNS/nobody/%s/search/jobs/%s?output_mode=json' % (self.app, self.sid)
            serverResponse, serverContent = rest.simpleRequest(job_uri, sessionKey=self.session_key)
            self.job = json.loads(serverContent)['entry'][0]

            results_uri = '/servicesNS/nobody/%s/search/jobs/%s/results?output_mode=json' % (self.app, self.sid)
            serverResponse, serverContent = rest.simpleRequest(results_uri, sessionKey=self.session_key)
            self.results = json.loads(serverContent)

        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print >> sys.stderr, 'error="%s" object="%s" line=%s message="%s"' % (exc_type, exc_obj, exc_tb.tb_lineno, 'WARN: Unexpected exception seen getting search result data from REST API')

    def get_unique_values(self):
        '''Get the unique values for any number of fields.'''

        blacklisted_fields = ['count','_time',]

        filtered_data = []
        for result in self.results['results']:
            # reduce data set to hash_fields
            filtered_data.append( {k:v for (k,v) in result.iteritems() if k not in blacklisted_fields} )

        unique_values = {}
        val_set = set()
        keys = set([y for x in filtered_data for y in x.keys()])
        for key in keys:
            values = [v for e in filtered_data for k,v in e.items() if k == key]
            for item in values:
                try:
                    val_set.update( [item] )
                except TypeError, e:
                    val_set.update( [ piece for piece in item] )
                finally:
                    unique_values[key] = "/".join(v for v in val_set)
                    val_set.clear()

        if unique_values:
            return unique_values
        else:
            return False

    def attach_results(self, jconn):
        '''Attach the results.csv.gz file from dispatch as a JIRA attachment.  Append a chunk of the Splunk SID for readability'''
        try:
            with open(self.results_file, 'rb') as rf:
                attached_results = jconn.add_attachment(self.id, rf, "%s_at_%s.csv.gz" % ('Results', self.sid.split('_at_')[1]))
                print >> sys.stderr, 'attached_results="%s" results_file="%s"' % (attached_results, self.results_file)
                self.status = 'attached'
                return attached_results
        except jira.exceptions.JIRAError as e:
            # failing here because of permissions error in JIRA.
            logger = logging.getLogger('jira_alert')
            if 'You do not have permission to create attachments for this issue' in e.text:
                logger.debug('sid="%s" key="%s" message="%s"' % (self.sid, self.key, e.text))
            else:
                logger.debug('Unrecognized Exception, sid="%s" key="%s" message="%s"' % (self.sid, self.key, e.text))
                logger.exception('')

            self.status = 'attach_fail'
            return None

    def format_results(self):
        '''assumes results are always passed as part of 'results['results']' which is sourced from calling output_mode=json' in the REST API which provides a JSON-formatted string.'''
        # logger = logging.getLogger('jira_alert')
        try:
            # omit fields below (ie 'mv_fields') which are unneeded to display output in JIRA tables
            blacklist_fields = []
            # cap output at 50 rows for now
            output_max_rows = 50
            trimmed_results = self.results.copy()
            tmp_results = []
            allowed_fields = [ key['name'] for key in self.results['fields'] if key['name'] not in blacklist_fields ]
            for row in trimmed_results['results']:
                # print >> sys.stderr, 'printing row="%s"' % row
                tmp_results.append({key: row[key] for key in row if key in allowed_fields})
            trimmed_results['results'] = tmp_results
            trimmed_results['fields'] = allowed_fields

            self.results_jira = json_to_jira(trimmed_results)[0:output_max_rows]
            self.results_ascii = json_to_tabulate(trimmed_results)[0:output_max_rows]
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print >> sys.stderr, 'exception="%s" object="%s" line=%s message="%s"' % (exc_type, exc_obj, exc_tb.tb_lineno, 'Unexpected exception seen formatting results')

    def write_to_kv_store(self):
        pass

    def write_to_index(self):

        now = datetime.datetime.now()

        try:
            event_str = (
                'time="{time}" action="{action}" search_name="{search_name}" '
                'project="{project}" key="{key}" issuetype="{issuetype}" labels="{labels}" '
                'summary="{summary}" search_id="{search_id}" event_hash="{event_hash}" '
                'keywords="{keywords}" group_by_field="{group_by_field}" '
                'result_count="{result_count}" event_count="{event_count}" '
                'update_count="{update_count}" ttl="{ttl}"'
                )
            event_vars = {
                'time': now.strftime("%Y-%m-%d %H:%M:%S %Z"),
                'action': 'create',
                'search_name': self.search_name,
                'project': self.project,
                'key': self.key,
                'issuetype': self.issuetype,
                'labels': ' '.join(self.labels),
                'summary': self.summary,
                'search_id': self.sid,
                'event_hash': self.event_hash,
                'keywords': str(self.keywords),
                'group_by_field': self.group_by_field,
                'result_count': self.result_count,
                'event_count': self.event_count,
                'update_count': self.update_count,
                'ttl': self.ttl
                }

            event = event_str.format(**event_vars)

            # first add alerts to collections ...
            event_submit_uri = '/services/receivers/simple?output_mode=json&host=%s&source=%s&sourcetype=%s&index=%s' % (self.hostname, 'jira_issue.py', 'jira_issue', self.index)
            serverResponse, serverContent = rest.simpleRequest(event_submit_uri, sessionKey=self.session_key, jsonargs=json.dumps(event))
            # print >> sys.stderr, 'DUMP serverContent=%s serverResponse="%s"' % (json.loads(serverContent), json.loads(serverResponse))

            return event

        except Exception, e:
            logger = logging.getLogger('jira_alert')
            logger.exception('')

    def process_results(self):
        ''' Crunch some of the results figures for grouping and formatting inside JIRA '''
        self.get_results()

        if self.job:
            self.search_string = self.job['content']['eventSearch']
            self.ttl = self.job['content']['ttl']
            # manipulate time string using dateutil
            # self.job['updated'] = 2016-03-01T21:03:03.000+11:00
            updated = parse(self.job['updated'])
            self.trigger_time = int(time.mktime(updated.timetuple())) # unix time: 1456830183
            self.trigger_time_rendered = str(updated)
            self.expiration_time_rendered = str(updated + datetime.timedelta(seconds=self.ttl))
            self.keywords = self.get_keywords(self.job['content']['keywords'])
            self.event_count = self.job['content']['eventCount']
            self.result_count = self.job['content']['resultCount']
        if self.results:
            self.fields = [field['name'] for field in self.results['fields']]
            self.results_unique = self.get_unique_values()

        self.event_hash = self.get_event_hash()
        self.owner_rendered = render_user(self.owner)

class NewIssue(Issue):
    def __init__(self, payload):
        Issue.__init__(self, payload)

    def render_summary(self):
        print >> sys.stderr, 'DEBUG summary=%s' % self.summary
        summary_env = jinja2.Environment(variable_start_string = '${',variable_end_string = '}$')
        # rendered_summary = summary_env.from_string(raw_summary).render(self.__dict__)
        rendered_summary = summary_env.from_string(self.summary).render(self.__dict__)

        return rendered_summary

    def render_description(self):
        raw_description = self.description
        # process results for printing inside template
        self.format_results()
        description_env = jinja2.Environment(variable_start_string = '${',variable_end_string = '}$')
        # rendered_description = description_env.from_string(raw_description).render(self.__dict__)
        rendered_description = description_env.from_string(self.description).render(self.__dict__)

        return rendered_description

    def become_issue(self, jconn):
        '''Create a new issue in JIRA using the alert data and open JIRA server conn'''

        issue_fields = {}
        issue_fields['summary'] = self.render_summary()
        issue_fields['labels'] = self.labels
        issue_fields['description'] = self.render_description()

        issue_fields['issuetype'] = {'name': self.issuetype}
        issue_fields['project'] = {'key': self.project}

        try:
            # create issue using JIRA python SDK
            # new_issue = jconn.create_issue(fields=issue_fields)
            # print >> sys.stderr, 'DEBUG issue_fields=%s' % issue_fields
            new_issue = jconn.create_issue(fields=issue_fields)

            # add link to Splunk results
            # link results

            # actions to add:
            ## 1 add results as CSV attachment
            #
            ## 2 add issue data to collection of open issues
            self.key = new_issue.key
            self.id = new_issue.id

            ## 3 log Splunk event to alerts index
            self.status = 'created'

            try:
                new_issue_event = self.write_to_index()
                print >> sys.stderr, 'DEBUG new_issue=%s' % new_issue_event

            except Exception, e:
                logger = logging.getLogger('jira_alert')
                logger.exception('')

            return new_issue

        except jira.exceptions.JIRAError as e:
            logger = logging.getLogger('jira_alert')
            logger.exception('')

            if 'Unauthorized' in e.text:
                # logger.debug('message="%s"' % 'Not authorized to access the issue creation REST endpoint')
                pass

            if 'Does Not Exist' in e.text:
                # logger.debug('Issue no longer exists')
                # jira_common.deleteIssue(issue_key, jira_conf['sessionKey'])
                pass
            else:
                # logger.debug('Unexpected exception updating issue')
                pass

            self.status = 'create_fail'
            return None

        except Exception, e:
            self.status = 'create_fail'
            return None

    def link_issue(self, jconn):

        try:

            link_object = {
              'object': {
                'url': self.results_link,
                'title': 'Splunk Search Results [@' + self.sid.split('_at_')[1] + ']',
                'icon': {
                  'url16x16': 'http://www.splunk.com/content/dam/splunk2/images/icons/favicons/favicon.ico'
                }
              }
            }

            simple_link = jconn.add_simple_link(self.key, link_object)

            print >> sys.stderr, 'DEBUG link_object=%s simple_link=%s' % (link_object, simple_link)

            # add link to Splunk results
            # link results

            self.status = 'linked'
            return simple_link

        except jira.exceptions.JIRAError as e:
            logger = logging.getLogger('jira_alert')
            logger.exception('')

            self.status = 'link_fail'
            return None

    def add_to_collection(self):
        issues_entry = {}
        # JIRA fields
        issues_entry['project'] = issue.fields.project.key
        issues_entry['key'] = issue.key
        issues_entry['id'] = issue.id
        issues_entry['summary'] = issue.fields.summary
        issues_entry['issuetype'] = issue.fields.issuetype.name
        if issue.fields.assignee:
            issues_entry['assignee'] = issue.fields.assignee.key
        else:
            issues_entry['assignee'] = None
        issues_entry['reporter'] = issue.fields.reporter.key
        issues_entry['created'] = issue.fields.created
        issues_entry['updated'] = issue.fields.updated
        if issue.fields.resolution:
            issues_entry['resolution'] = issue.fields.resolution.name
        else:
            issues_entry['resolution'] = None
        issues_entry['labels'] = issue.fields.labels
        issues_entry['priority'] = issue.fields.priority.name
        # event data
        issues_entry['group_by_field'] = template_conf['group_by_field']
        issues_entry['event_hash'] = entry['event_hash']
        issues_entry['search_name'] = entry['savedsearch_name']
        issues_entry['search_id'] = entry['sid']
        issues_entry['trigger_time'] = entry['trigger_time']
        now = datetime.datetime.now()
        expires = datetime.datetime.fromtimestamp(entry['trigger_time'] + entry['ttl'])
        ttl = (expires - now).total_seconds()
        issues_entry['keywords'] = ttl
        issues_entry['keywords'] = entry['keywords']
        issues_entry['event_count'] = entry['event_count']
        issues_entry['result_count'] = entry['result_count']
        issues_entry['update_count'] = 0

        # ... then add issues to collections ...
        issues_entry_uri = '/servicesNS/nobody/jira/storage/collections/data/issues/'
        serverResponse, serverContent = rest.simpleRequest(issues_entry_uri, sessionKey=sessionKey, jsonargs=json.dumps(issues_entry))
        new_issue = json.loads(serverContent)

        new_alert = json.loads(serverContent)

        issues_entry['_key'] = new_alert['_key']

        return issues_entry
    def update_collection(self):
        pass


class SimilarIssue(Issue):

    def __init__(self, payload):
        Issue.__init__(self, payload)
        pass

    def get_ancestor():
        pass

    def get_summary():
        pass

    def get_comment():
        pass
