import csv
import gzip
import logging
import tempfile
import sys
import datetime
import os
import json
import StringIO
import re
import urlparse
import socket
from tabulate import tabulate

def is_net_addr(addr):
    is_addr = False
    for family in [ socket.AF_INET, socket.AF_INET6 ]:
        try:
            socket.inet_pton(family, addr)
            is_addr = True
        except socket.error:
            pass
    if is_addr:
        return True
    else:
        return False

def render_user(user):
    '''Takes a username and converts into JIRA @mention syntax. Skips local splunk users.'''
    if user in ['admin','nobody']:
        user_rendered = user
    else:
        user_rendered = '[~' + user + [']']
    return user_rendered

def json_to_csv(results):
    fields = results['fields']
    sf = StringIO.StringIO()
    csv_writer = csv.DictWriter(sf, fieldnames=fields, quoting=csv.QUOTE_MINIMAL)
    csv_writer.writeheader()
    for row in results['results']:
        for k,v in row.items():
            # collapse multiline stuff from table cmd, stats values(), etc
            if isinstance(v, list):
                row[k] = '\n'.join([str(d) for d in results['results']])
        csv_writer.writerow(row)
    sf.seek(0)
    # returns a list of CSV strings split by '\r\n'
    return sf.getvalue().split('\r\n')

def json_to_jira(results):
    fields = results['fields']
    header = '||' + '||'.join(fields) + '||' + '\r\n'
    table = []
    table.append(header)

    print >> sys.stderr, 'starting point results="%s"' % str(results)

    for row in results['results']:
        row_data = []
        for field in fields:
            try:
                # first collapse it
                if isinstance(row[field], list):
                    row[field] = '\r\n'.join([str(d) for d in row[field]])

                # add padding for empty cells
                if row[field] == '':
                    row[field] == ' '

                # this is a bit noisy / busy so have moved out functionality to render_user()
                # # try to assign a username if possible
                # if re.search('(user|uid)',field.lower()):
                #     row_data.append('[~' + row[field] + ']')

                # formatting for time strings
                if re.search('(time|created|modified)',field.lower()):
                    row_data.append('{{' + row[field] + '}}')

                # formatting for numeric values
                elif row[field].isdigit():
                    row_data.append('{{' + row[field] + '}}')

                # formatting for IP address values
                elif is_net_addr(row[field]):
                    row_data.append('{{' + row[field] + '}}')

                # me linky
                elif re.search('(url|link)',field.lower()):
                    link_bits = urlparse.urlsplit(row[field])
                    if link_bits.netloc and link_bits.scheme:
                        row_data.append('[' + link_bits.netloc + ' (' + link_bits.scheme + ')' + '|' + row[field] + ']')
                    else:
                        row_data.append(row[field])

                # no me linky
                elif re.search('(malware|virus|phish)',field.lower()):
                    link_bits = urlparse.urlsplit(row[field])
                    if link_bits.netloc and link_bits.scheme:
                        row_data.append('{{' + row[field] + '}}')
                    else:
                        row_data.append(row[field])

                else:
                    row_data.append(row[field])

            except KeyError:
                row_data.append('--')
                # logging.debug('action="%s" field="%s" data="%s" message="%s"' % ('trace',field, row, 'KeyError while creating JIRA table'))
        row_str = '|' + '|'.join(row_data) + '|' + '\r\n'
        table.append(row_str)
    return table


def json_to_tabulate(results, tablefmt='orgtbl'):
    csv_data = json_to_csv(results)
    headers = csv_data[0].split(',')
    table = []
    for row in csv_data[1:]:
        # skip empty rows
        if row != '':
            table.append(row.split(','))
    # returns a list of delimited strings to play with.  can iterate for printing out
    return tabulate(table, headers=headers, tablefmt=tablefmt).split('\r\n')
