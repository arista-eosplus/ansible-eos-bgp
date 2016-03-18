# (c) 2015, Peter Sprygada <psprygada@ansible.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import re
import collections

from ansible import errors

def parse_config(config, indent=1):
    regexp = re.compile(r'^\s*(.+)$')
    line_re = re.compile(r'\S')
    invalid_re = re.compile(r'^(!|end)')

    ancestors = list()
    data = collections.OrderedDict()
    banner = False

    for line in config:
        text = str(line).strip()

        if not invalid_re.match(text):

            # handle top level commands
            if line_re.match(line):
                data[text] = collections.OrderedDict()
                ancestors = [text]

            # handle sub level commands
            else:
                match = regexp.match(line)
                if match:
                    line_indent = match.start(1)
                    level = int(line_indent / indent)

                    try:
                        ancestors[level] = text
                    except IndexError:
                        ancestors.append(text)

                    try:
                        child = data[ancestors[0]]
                        for a in ancestors[1:level]:
                            child = child[a]
                        child[text] = collections.OrderedDict()
                    except KeyError:
                        # FIXME deal with indent inconsistencies
                        if '_errors' not in data:
                            data['_errors'] = list()
                        data['_errors'].append((ancestors, text))

    return data


def config_block(value, ancestors, indent=1):
    config = parse_config(value.split('\n'), indent)
    try:
        for ancestor in ancestors.split('.'):
            config = config[ancestor]
        return config.keys()
    except KeyError:
        # raise errors.AnsibleFilterError('Config block not found for parent')
        return None


def re_findall(value, regex):
    return re.findall(regex, value, re.M)


def re_search(value, regex):
    return re.search(regex, value, re.M)


class FilterModule(object):

    def filters(self):
        return {
            'config_block': config_block,
            're_findall': re_findall,
            're_search': re_search,
        }
