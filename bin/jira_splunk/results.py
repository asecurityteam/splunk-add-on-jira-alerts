import json
import re
import time
import hashlib
import splunk.rest as rest


class SplunkSearch(object):
    """Wraps around a splunk Job Search"""
    def __init__(self, app, sid, session_key, owner=None, search_string=None, search_name=None):
        self.app = app
        self.sid = sid
        self.session_key = session_key
        self.owner = owner
        self.search_string = search_string
        self.search_name = search_name
        self.__job = None

    @property
    def job(self):
        if not self.job:
            uri = '/servicesNS/nobody/%s/search/jobs/%s?output_mode=json' % (self.app, self.sid)
            serverResponse, serverContent = rest.simpleRequest(uri, sessionKey=self.session_key)
            self.__job = json.loads(serverContent)['entry'][0]
        return self.__job

    def read(self):
        results_uri = '/servicesNS/nobody/%s/search/jobs/%s/results?output_mode=json' % (self.app, self.sid)
        server_response, server_content = rest.simpleRequest(results_uri, self.session_key)
        if server_content:
            return json.loads(server_content)
        return None


class BaseResults(object):

    def __init__(self, search):
        self.search = search

    @property
    def ttl(self):
        return None

    @property
    def trigger_time(self):
        return None

    @property
    def event_count(self):
        return 0

    @property
    def result_count(self):
        return 0

    @property
    def keywords(self):
        return []

    @property
    def results(self):
        return []

    def get_unique_values(self):
        '''Get the unique values for any number of fields.'''

        blacklisted_fields = ['count','_time']

        filtered_data = []
        for result in self.results:
            # reduce data set to hash_fields
            filtered_data.append( {k:v for (k,v) in result.iteritems() if k not in blacklisted_fields} )

        unique_values = {}
        val_set = set()
        keys = set([y for x in filtered_data for y in x.keys()])
        for key in keys:
            values = [v for e in filtered_data for k, v in e.items() if k == key]
            for item in values:
                try:
                    val_set.update([item])
                except TypeError, e:
                    val_set.update([piece for piece in item])
                finally:
                    unique_values[key] = "/".join(v for v in val_set)
                    val_set.clear()

        if unique_values:
            return unique_values
        else:
            return False

    def get_event_hash(self, group_by_field):
        '''Generate the event hash based on event data, less any datetime fields.'''
        hashable_data = []

        if group_by_field in [None, '']:
            hash_fields = self.fields
        else:
            hash_fields = self.group_by_field

        for result in self.results:
            # reduce data set to hash_fields
            hashable_data.append({k: v for (k, v) in result.iteritems() if k in hash_fields})

        hash_vals = []
        # create unique set of values
        for hash_val in [v for entry in hashable_data for v in entry.values()]:
            if isinstance(hash_val, list):
                hash_vals.append('_'.join([h for h in hash_val]))
            else:
                hash_vals.append(hash_val)

        hash_set = set(sorted(hash_vals))

        # convert to a single hashable string
        hash_data = self.search.search_name + '_' + str( '_'.join([item for item in hash_set]))
        hash_data = hash_data.lower()


        # generate the hash based on the final hash of data, including any unique values in the list of hash_fields.  should end up like:
        # 'Search Name_val1_val2'...
        event_hash = hashlib.md5(hash_data).hexdigest()

        # logr.debug('action=%s search_name=%s hash_fields=%s hash_data=%s event_hash=%s message="%s"' % ('event_hash', search_name, hash_fields, hash_data, event_hash, 'generated event hash for search results'))
        if event_hash:
            return event_hash
        else:
            return False


class SearchCommandResults(BaseResults):
    """Wraps around result parsing for search based results"""
    def __init__(self, search, records):
        BaseResults.__init__(self, search)

        self.__fields = []
        self.__results = []

        for record in records:
            if not self.__fields:
                self.__fields = [dict(name=n) for n in record.keys()]
            self.__results.append(dict(record.items()))

    @property
    def results(self):
        return self.__results

    @property
    def fields(self):
        return self.__fields


class AlertResults(BaseResults):
    """Wraps around a result set as provided by an Alert"""
    def __init__(self, search, results, simple=None, as_file=None, link=None):
        BaseResults.__init__(self, search)
        self.results = results
        self.results_simple = simple
        self.results_file = as_file
        self.results_link = link

        self.results_unique = None
        self.job = None
        self.app = None
        self.sid = None

    def __get_keywords(self, keywords):
        kv_matches = {}
        kv_matches_quoted = dict(re.findall(r'\"(.+)::(.+)\"', keywords))
        kv_matches_norm = dict(re.findall(r'(\S+)::(\S+)', keywords))

        if kv_matches_quoted:
            kv_matches.update(kv_matches_quoted)
        if kv_matches_norm:
            kv_matches.update(kv_matches_norm)

        return kv_matches

    @property
    def ttl(self):
        return self.search.job['content']['ttl']

    @property
    def trigger_time(self):
        updated = self.search.job['updated']
        return int(time.mktime(updated.timetuple()))

    @property
    def event_count(self):
        return self.search.job['content']['eventCount']

    @property
    def result_count(self):
        return self.search.job['content']['resultCount']

    @property
    def keywords(self):
        return self.__get_keywords(self.search.job['content']['keywords'])

    @property
    def results(self):
        return self.search.read()

