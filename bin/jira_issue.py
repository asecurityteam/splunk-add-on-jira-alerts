import os
import sys
import time
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

DEFAULT_DESCRIPTION = '''h3. ${search_name}$\n
h6. Event Data ASCII\n
{noformat}{% for row in results_ascii %}${row}${% endfor %}{noformat}\n

h6. Event Details\n
{color:#707070}
~*Triggered*: {{${trigger_time}$}} | *Expires In*: {{${ttl}$s}} | *\# Results*: {{${result_count}$}} | *\# Events*: {{${event_count}$}} | *Results Link*: {{_[Results|${results_link}$]_}}~
~*Hash*: {{${event_hash}$}} | *Unique Values*: {{${results_unique}$}}~
{color}\n

h6. Search Query\n
{color:#707070}~*App Name*: {{${app}$}} | *Owner*: [~${owner}$]~{color}
{noformat}${search_string}${noformat}'''

class Issue(object):

    def __init__(self, payload):
        # self.logger = logging.getLogger('jira_alert')
        self.jira_config = payload['configuration']
        self.index = 'alerts'  # need to implement config for this

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
        ''' Get the unique values for any number of fields.'''

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

    def get_results_file(self):
        pass

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

            # self.results_jira = json_to_jira(trimmed_results)[0:output_max_rows]

            self.results_ascii = json_to_tabulate(trimmed_results)[0:output_max_rows]
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print >> sys.stderr, 'exception="%s" object="%s" line=%s message="%s"' % (exc_type, exc_obj, exc_tb.tb_lineno, 'Unexpected exception seen formatting results')

    def write_to_kv_store(self):
        pass

    def write_to_index(self):
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

            input.submit(event, hostname = self.hostname, sourcetype = 'jira_issue', source = 'jira_issue.py', index = self.index )
            return event

        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print >> sys.stderr, 'error="%s" object="%s" line=%s message="%s"' % (exc_type, exc_obj, exc_tb.tb_lineno, 'WARN: Unable to submit event to Splunk')

    def process_results(self):
        ''' Crunch some of the results figures for grouping and formatting inside JIRA '''
        self.get_results()
        if self.job:
            self.search_string = self.job['content']['eventSearch']
            self.trigger_time = self.job['updated']
            self.ttl = self.job['content']['ttl']
            self.keywords = self.get_keywords(self.job['content']['keywords'])
            self.event_count = self.job['content']['eventCount']
            self.result_count = self.job['content']['resultCount']
        if self.results:
            self.fields = [field['name'] for field in self.results['fields']]
            self.results_unique = self.get_unique_values()

        self.event_hash = self.get_event_hash()

        # placeholder to prepare jinja2 template context
        # self.context = self

        # if self.get_ancestor():
        #    update JIRA
        # else:
        # create JIRA

class NewIssue(Issue):
    def __init__(self, payload):
        Issue.__init__(self, payload)

    def render_summary(self):
        raw_summary = self.summary
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
        """Create a new issue in JIRA using the alert data and open JIRA server conn """

        simple_link = False

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

            link_object = {
              'object': {
                'url': self.results_link,
                'title': 'Splunk Search Results [@' + self.sid[-15:] + ']',
                'icon': {
                  'url16x16': 'http://www.splunk.com/content/dam/splunk2/images/icons/favicons/favicon.ico'
                }
              }
            }

            simple_link = jira.add_simple_link(new_issue.key, link_object)

            # actions to add:
            ## 1 add results as CSV attachment
            #
            ## 2 add issue data to collection of open issues
            self.key = new_issue.key

            ## 3 log Splunk event to alerts index
            self.status = 'created'

            try:
                new_issue_event = self.write_to_index()
            except Exception, e:
                logger = logging.getLogger('jira_alert')
                logger.debug('message="%s" new_issue_event="%s"' % ('Not authorized to access the issue creation REST endpoint', new_issue_event))

            return new_issue

        except jira.exceptions.JIRAError as e:
            import traceback
            stack =  traceback.format_exc()

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
