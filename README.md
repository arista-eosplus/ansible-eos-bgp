BGP Role for EOS
================

The arista.eos-bgp role creates an abstraction for EOS BGP configuration.
This means that you do not need to write any ansible tasks. Simply create
an object that matches the requirements below and this role will ingest that
object and perform the necessary configuration.

This role specifically enables configuration of BGP router, timers, neighbors,
networks and listeners.

Installation
------------

```
ansible-galaxy install arista.eos-bgp
```


Requirements
------------

Requires an SSH connection for connectivity to your Arista device. You can use
any of the built-in eos connection variables, or the convenience ``provider``
dictionary.

Role Variables
--------------

The tasks in this role are driven by the ``bgp`` and ``eos_purge_bgp_networks``
and ``eos_purge_bgp_neighbors`` objects described below:

**eos_purge_bgp_networks**

|           Key          |          Type         | Notes                                                     |
|:----------------------:|:---------------------:|-----------------------------------------------------------|
| eos_purge_bgp_networks | boolean: true, false* | Enables or disables the purging feature for BGP Networks. |

**eos_purge_bgp_neighbors**

|           Key           |          Type         | Notes                                                      |
|:-----------------------:|:---------------------:|------------------------------------------------------------|
| eos_purge_bgp_neighbors | boolean: true, false* | Enables or disables the purging feature for BGP Neighbors. |

**bgp** (dictionary) each entry contains the following keys:

|                      Key | Type                      | Notes                                                                                 |
|-------------------------:|---------------------------|---------------------------------------------------------------------------------------|
|                   bgp_as | string (required)         | The BGP autonomous system number to be configured for the local BGP routing instance. |
|                   enable | boolean: true, false*     | Configures the administrative state for the global BGP routing process. If enable is True then the BGP routing process is administartively enabled and if enable is False then the BGP routing process is administratively disabled. |
|            maximum_paths | int                       | Configures the maximum number of parallel routes. The EOS default for this attribute is 1. This value should be less than or equal to maximum_ecmp_paths. |
|       maximum_ecmp_paths | int                       | Configures the maximum number of ecmp paths for each route. The EOS default for this attribute is the maximum value, which varies by hardware platform. Check your Arista documentation for more information. This value should be greater than or equal to maximum_paths. |
|     log_neighbor_changes | boolean: true*, false     | Enables or disables the logging of neighbor changes. |
|             redistribute | list                      | A list of the types of routes to redistribute. |
|                   timers | dictionary                | See the following timers.* keys for each list item |
|        timers.keep_alive | int: 0-15                 | Configures the keep_alive value in seconds.  Values from 0 to 3600. Default is 60. |
|              timers.hold | string                    | Configures the hold timer. Values include 0 or 3 to 7200. Default is 180. |
|                    state | choices: present*, absent | Set the state for the BGP router configuration. |
|                neighbors | list                      | See the following neighbors.* keys for each list item |
|           neighbors.name | string (required)         | The name of the BGP neighbor to manage. This value can be either an IPv4 address or string (in the case of managing a peer group) |
|    neighbors.description | string                    | Configures the BGP neighbors description value. The value specifies an arbitrary description to add to the neighbor statement in the nodes running-configuration. |
|      neighbors.remote_as | int                       | Configures the BGP neighbors remote-as value. |
|   neighbors.route_map_in | string                    | Configures the BGP neigbhors route-map in value. The value specifies the name of the route-map. |
|  neighbors.route_map_out | string                    | Configures the BGP neighbors route-map out value. The value specifies the name of the route-map. |
| neighbors.send_community | boolean: true, false      | Configures the BGP neighbors send-community value. If enabled then the BGP send-community value is enable. If disabled, then the BGP send-community value is disabled. |
|     neighbors.peer_group | string                    | The name of the peer-group value to associate with the neighbor. This argument is only valid if the neighbor is an IPv4 address |
|         neighbors.enable | boolean: true*, false     | Configures the administrative state for the BGP neighbor process. If enable is True then the BGP neighbor process is administartively enabled and if enable is False then the BGP neighbor process is administratively disabled. |
|                listeners | list                      | See the following listeners.* keys for each list item |
|           listeners.name | string (required)         | The IPv4 network which describes the listen range. For example 192.168.1.0/24. |
|     listeners.peer_group | string (required)         | The name of the peer-group value to associate with the neighbor. |
|      listeners.remote_as | string (required)         | Configures the BGP listeners remote-as value. |
|                 networks | list                      | See the following networks.* keys for each list item |
|          networks.prefix | string (required)         | The IPv4 prefix to configure as part of the network statement. The value must be a valid IPv4 prefix |
|         networks.masklen | int (required)            | The IPv4 subnet mask length in bits. The value for the masklen must be in the valid range of 1 to 32. |
|        networks.routemap | string                    | Configures the BGP route-map name to apply to the network statement when configured. Note this module does not create the route-map |
|           networks.state | choices: present*, absent | Set the state for the BGP network.  To remove the network use the absent value. |

```
Note: Asterisk (*) denotes the default value if none specified
```

Connection Variables
--------------------

Ansible EOS roles require the following connection information to establish
communication with the nodes in your inventory. This information can exist in
the Ansible group_vars or host_vars directories, or in the playbook itself.

|         Key | Required | Choices    | Description                              |
| ----------: | -------- | ---------- | ---------------------------------------- |
|        host | yes      |            | Specifies the DNS host name or address for connecting to the remote device over the specified *transport*. The value of *host* is used as the destination address for the transport. |
|        port | no       |            | Specifies the port to use when building the connection to the remote device. This value applies to either acceptable value of *transport*. The port value will default to the appropriate transport common port if none is provided in the task (cli=22, http=80, https=443). |
|    username | no       |            | Configures the usename to use to authenticate the connection to the remote device.  The value of *username* is used to authenticate either the CLI login or the eAPI authentication depending on which *transport* is used. If the value is not specified in the task, the value of environment variable ANSIBLE_NET_USERNAME will be used instead. |
|    password | no       |            | Specifies the password to use to authenticate the connection to the remote device. This is a common argument used for either acceptable value of *transport*. If the value is not specified in the task, the value of environment variable ANSIBLE_NET_PASSWORD will be used instead. |
| ssh_keyfile | no       |            | Specifies the SSH keyfile to use to authenticate the connection to the remote device. This argument is only used when *transport=cli*. If the value is not specified in the task, the value of environment variable ANSIBLE_NET_SSH_KEYFILE will be used instead. |
|   authorize | no       | yes, no*   | Instructs the module to enter priviledged mode on the remote device before sending any commands. If not specified, the device will attempt to excecute all commands in non-priviledged mode. If the value is not specified in the task, the value of environment variable ANSIBLE_NET_AUTHORIZE will be used instead. |
|   auth_pass | no       |            | Specifies the password to use if required to enter privileged mode on the remote device.  If *authorize=no*, then this argument does nothing. If the value is not specified in the task, the value of environment variable ANSIBLE_NET_AUTH_PASS will be used instead. |
|   transport | yes      | cli*, eapi | Configures the transport connection to use when connecting to the remote device. The *transport* argument supports connectivity to the device over cli (ssh) or eapi. |
|     use_ssl | no       | yes*, no   | Configures the transport to use SSL if set to true only when *transport=eapi*.  If *transport=cli*, this value is ignored. |
|    provider | no       |            | Convience method that allows all the above connection arguments to be passed as a dict object. All constraints (required, choices, etc) must be met either by individual arguments or values in this dict. |

```
Note: Asterisk (*) denotes the default value if none specified
```

Ansible Variables
-----------------

|    Key | Choices      | Description                              |
| -----: | ------------ | ---------------------------------------- |
| no_log | true, false* | Prevents module arguments and output from being logged during the playbook execution. By default, no_log is set to true for tasks that gather and save EOS configuration information to reduce output size. Set to true to prevent all output other than task results. |

```
Note: Asterisk (*) denotes the default value if none specified
```

Dependencies
------------

The eos-bgp role is built on modules included in the core Ansible code.
These modules were added in ansible version 2.1

- Ansible 2.1.0

Example Playbook
----------------

The following example will use the arista.eos-bgp role to setup
a majority of BGP configuration without writing any tasks. We'll create a
``hosts`` file with our switch, then a corresponding ``host_vars`` file and
then a simple playbook which only references the eos-bgp role. By including
the role, we automatically get access to all of the tasks to configure BGP
settings. What's nice about this is that if you have a host without BGP
configuration, the tasks will be skipped without any issue.


Sample hosts file:

    [leafs]
    leaf1.example.com

Sample host_vars/leaf1.example.com

    provider:
      host: "{{ inventory_hostname }}"
      username: admin
      password: admin
      use_ssl: no
      authorize: yes
      transport: cli

    bgp:
      enable: true
      bgp_as: 65001
      maximum_paths: 25
      maximum_ecmp_paths: 100
      redistribute:
        - connected
        - aggregate
      log_neighbor_changes: yes
      timers:
        keep_alive: 0
        hold: 0
      neighbors:
        - name: 10.1.1.1
          remote_as: 65002
          peer_group: demoleaf
          enable: true
        - name: 10.1.1.3
          remote_as: 65002
          peer_group: demoleaf
          enable: true
      listeners:
        - name: 10.1.0.0/16
          peer_group: demoleaf
          remote_as: 65003

    eos_purge_bgp_networks: no
    eos_purge_bgp_neighbors: no


A simple playbook to configure BGP, leaf.yml

    - hosts: leafs
      roles:
         - arista.eos-bgp

Then run with:

    ansible-playbook -i hosts leaf.yml
​    


Developer Information
------------

Development contributions are welcome. Please see *Arista Roles for Ansible - Development Guidelines* ([test/arista-ansible-role-test/README](test/arista-ansible-role-test/README.md)) for additional information, including how to develop and run test cases for role development.




License
-------

Copyright (c) 2015, Arista Networks EOS+
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of Arista nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


Author Information
------------------

Please raise any issues using our GitHub repo or email us at ansible-dev@arista.com
