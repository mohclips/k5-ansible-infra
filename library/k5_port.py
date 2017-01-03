#!/usr/bin/python

ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'community',
                    'version': '1.0'}

DOCUMENTATION = '''
---
module: k5_network
short_description: Create network on K5 in particular AZ
version_added: "1.0"
description:
    - Explicit K5 call to create a network in an AZ - replaces os_network from Openstack module, but is more limited. Use os_network to update the network. 
options:
   name:
     description:
        - Name of the network.
     required: true
     default: None
   state:
     description:
        - State of the network. Can only be 'present'.
     required: true
     default: None
   availability_zone:
     description:
        - AZ to create the network in.
     required: true
     default: None
   k5_auth:
     description:
       - dict of k5_auth module output.
     required: true
     default: None
requirements:
    - "python >= 2.6"
'''

EXAMPLES = '''
# Create a network in an AZ
- k5_network:
     name: network-01
     state: present
     availability_zone: uk-1a
     k5_auth: "{{ k5_auth_facts }}"
'''

RETURN = '''
k5_router_facts:
    description: Dictionary describing the router details.
    returned: On success when router is created
    type: dictionary
    contains:
        id:
            description: Router ID.
            type: string
            sample: "474acfe5-be34-494c-b339-50f06aa143e4"
        name:
            description: Router name.
            type: string
            sample: "router1"
        admin_state_up:
            description: Administrative state of the router.
            type: boolean
            sample: true
        status:
            description: The router status.
            type: string
            sample: "ACTIVE"
        tenant_id:
            description: The tenant ID.
            type: string
            sample: "861174b82b43463c9edc5202aadc60ef"
        external_gateway_info:
            description: The external gateway parameters. Will always be null.
            type: dictionary
            sample: null
        availability_zone:
            description: The AZ the router was created in.
            type: string
            sample: uk-1a
'''


import requests
import os
import json
from ansible.module_utils.basic import *


############## Common debug ###############
k5_debug = False
k5_debug_out = []

def k5_debug_get():
    """Return our debug list"""
    return k5_debug_out

def k5_debug_clear():
    """Clear our debug list"""
    k5_debug_out = []

def k5_debug_add(s):
    """Add string to debug list if env K5_DEBUG is defined"""
    if k5_debug:
        k5_debug_out.append(s)


############## router functions #############

def k5_get_endpoint(e,name):
    """Pull particular endpoint name from dict"""

    return e['endpoints'][name]

def k5_get_security_group_ids_from_names(module, k5_facts):
    """Get a list of ids from a list of names"""

    endpoint = k5_facts['endpoints']['networking']
    auth_token = k5_facts['auth_token']
    security_groups = module.params['security_groups']

    session = requests.Session()

    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Auth-Token': auth_token }

    url = endpoint + '/v2.0/security-groups'

    k5_debug_add('endpoint: {0}'.format(endpoint))
    k5_debug_add('REQ: {0}'.format(url))
    k5_debug_add('headers: {0}'.format(headers))

    try:
        response = session.request('GET', url, headers=headers)
    except requests.exceptions.RequestException as e:
        module.fail_json(msg=e)

    # we failed to get data
    if response.status_code not in (200,):
        module.fail_json(msg="RESP: HTTP Code:" + str(response.status_code) + " " + str(response.content), debug=k5_debug_out)

    #k5_debug_add("RESP: " + str(response.json()))


    # check if the security group names provided actually exist
    sgs={}
    sg_ids=[]
    for n in response.json()['security_groups']:
        sgs[n['name']] = n['id']

    
    for sg in security_groups:
        if sg in sgs.keys():
            sg_ids.append( sgs[sg] )
        else:
            module.fail_json(msg="Security Group " + sg +  " not found")

    k5_debug_add(sg_ids)

    return sg_ids


def k5_get_subnet_id_from_name(module, k5_facts):
    """Get an id from a subnet_name"""

    endpoint = k5_facts['endpoints']['networking']
    auth_token = k5_facts['auth_token']
    subnet_name = module.params['subnet_name']

    session = requests.Session()

    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Auth-Token': auth_token }

    url = endpoint + '/v2.0/subnets'

    k5_debug_add('endpoint: {0}'.format(endpoint))
    k5_debug_add('REQ: {0}'.format(url))
    k5_debug_add('headers: {0}'.format(headers))

    try:
        response = session.request('GET', url, headers=headers)
    except requests.exceptions.RequestException as e:
        module.fail_json(msg=e)

    # we failed to get data
    if response.status_code not in (200,):
        module.fail_json(msg="RESP: HTTP Code:" + str(response.status_code) + " " + str(response.content), debug=k5_debug_out)

    #k5_debug_add("RESP: " + str(response.json()))

    for n in response.json()['subnets']:
        #k5_debug_add("Found subnet name: " + str(n['name']))
        if str(n['name']) == subnet_name:
            #k5_debug_add("Found it!")
            return n['id']

    return ''


def k5_get_network_id_from_name(module, k5_facts):
    """Get an id from a network_name"""

    endpoint = k5_facts['endpoints']['networking']
    auth_token = k5_facts['auth_token']
    network_name = module.params['network_name']

    session = requests.Session()

    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Auth-Token': auth_token }

    url = endpoint + '/v2.0/networks'

    k5_debug_add('endpoint: {0}'.format(endpoint))
    k5_debug_add('REQ: {0}'.format(url))
    k5_debug_add('headers: {0}'.format(headers))

    try:
        response = session.request('GET', url, headers=headers)
    except requests.exceptions.RequestException as e:
        module.fail_json(msg=e)

    # we failed to get data
    if response.status_code not in (200,):
        module.fail_json(msg="RESP: HTTP Code:" + str(response.status_code) + " " + str(response.content), debug=k5_debug_out)

    #k5_debug_add("RESP: " + str(response.json()))

    for n in response.json()['networks']:
        #k5_debug_add("Found network name: " + str(n['name']))
        if str(n['name']) == network_name:
            #k5_debug_add("Found it!")
            return n['id']

    return ''



def k5_check_port_exists(module, k5_facts):
    """Check if a port_name already exists"""
   
    endpoint = k5_facts['endpoints']['networking']
    auth_token = k5_facts['auth_token']
    port_name = module.params['name']
 
    session = requests.Session()

    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Auth-Token': auth_token }

    url = endpoint + '/v2.0/ports'

    k5_debug_add('endpoint: {0}'.format(endpoint))
    k5_debug_add('REQ: {0}'.format(url))
    k5_debug_add('headers: {0}'.format(headers))

    try:
        response = session.request('GET', url, headers=headers)
    except requests.exceptions.RequestException as e:
        module.fail_json(msg=e)

    # we failed to get data 
    if response.status_code not in (200,):
        module.fail_json(msg="RESP: HTTP Code:" + str(response.status_code) + " " + str(response.content), debug=k5_debug_out)

    #k5_debug_add("RESP: " + str(response.json()))

    for n in response.json()['ports']:
        #k5_debug_add("Found port name: " + str(n['name']))
        if str(n['name']) == port_name:
            #k5_debug_add("Found it!")
            return True

    return False

def k5_create_port(module):
    """Create a port in an AZ on K5"""
    
    global k5_debug

    k5_debug_clear()

    if 'K5_DEBUG' in os.environ:
        k5_debug = True

    if 'auth_spec' in module.params['k5_auth']: 
        k5_facts = module.params['k5_auth']
    else:
        module.fail_json(msg="k5_auth_facts not found, have you run k5_auth?")        

    endpoint = k5_facts['endpoints']['networking']
    auth_token = k5_facts['auth_token']

    port_name = module.params['name']
    subnet_name = module.params['subnet_name']
    network_name = module.params['network_name']
    fixed_ip = module.params['fixed_ip']
    security_groups = module.params['security_groups']

    if k5_check_port_exists(module, k5_facts):
        if k5_debug:
            module.exit_json(changed=False, msg="Port " + port_name + " already exists", debug=k5_debug_out)
        else:
            module.exit_json(changed=False, msg="Port " + port_name + " already exists")

    # we need the network_id not network_name, so grab it
    network_id = k5_get_network_id_from_name(module, k5_facts)
    if network_id == '':
        if k5_debug:
            module.exit_json(changed=False, msg="Network " + network_name + " not found", debug=k5_debug_out)
        else:
            module.exit_json(changed=False, msg="Network " + network_name + " not found")
    
    # we need the subnet_id not subnet_name, so grab it
    subnet_id = k5_get_subnet_id_from_name(module, k5_facts)
    if subnet_id == '':
        if k5_debug:
            module.exit_json(changed=False, msg="Subnet " + subnet_name + " not found", debug=k5_debug_out)
        else:
            module.exit_json(changed=False, msg="Subnet " + subnet_name + " not found")

    # check the security groups exist
    sec_grp_list = k5_get_security_group_ids_from_names(module, k5_facts)

    az = module.params['availability_zone']
    
    # actually the project_id, but stated as tenant_id in the API
    #tenant_id = k5_facts['auth_spec']['os_project_id']
    
    k5_debug_add('auth_token: {0}'.format(auth_token))
    k5_debug_add('port_name: {0}'.format(port_name))
    k5_debug_add('subnet_name: {0} {1}'.format(subnet_name, subnet_id))
    k5_debug_add('network_name: {0} {1}'.format(network_name, network_id))
    k5_debug_add('fixed_ip: {0}'.format(fixed_ip))
    k5_debug_add('security_groups: {0}'.format(security_groups))
    k5_debug_add('az: {0}'.format(az))

    session = requests.Session()

    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Auth-Token': auth_token }

    url = endpoint + '/v2.0/ports'

    query_json = {"port":{
        "network_id": network_id, 
        "name": port_name, 
        "availability_zone":az, 
        "fixed_ips": [{
            "subnet_id": subnet_id, 
            "ip_address": fixed_ip
        }],
        "security_groups": sec_grp_list
    }}

    k5_debug_add('endpoint: {0}'.format(endpoint))
    k5_debug_add('REQ: {0}'.format(url))
    k5_debug_add('headers: {0}'.format(headers))
    k5_debug_add('json: {0}'.format(query_json))

    try:
        response = session.request('POST', url, headers=headers, json=query_json)
    except requests.exceptions.RequestException as e:
        module.fail_json(msg=e)

    # we failed to make a change
    if response.status_code not in (201,):
        module.fail_json(msg="RESP: HTTP Code:" + str(response.status_code) + " " + str(response.content), debug=k5_debug_out)
    
    k5_debug_add('response json: {0}'.format(response.json()))

    if k5_debug:
      module.exit_json(changed=True, msg="Port Creation Successful", k5_subnet_facts=response.json()['port'], debug=k5_debug_out )

    module.exit_json(changed=True, msg="Port Creation Successful", k5_subnet_facts=response.json()['subnet'] )


######################################################################################

def main():

    module = AnsibleModule( argument_spec=dict(
        name = dict(required=True, default=None, type='str'),
        state = dict(required=True, type='str'), # should be a choice
        subnet_name = dict(required=True, default=None, type='str'),
        network_name = dict(required=True, default=None, type='str'),
        fixed_ip = dict(required=True, default=None, type='str'),
        security_groups = dict(required=True, default=None, type='list'),
        availability_zone = dict(required=True, default=None, type='str'),
        k5_auth = dict(required=True, default=None, type='dict')
    ) )

    if module.params['state'] == 'present':
        k5_create_port(module)
    else:
       module.fail_json(msg="No 'absent' function in this module, use os_port module instead") 


######################################################################################

if __name__ == '__main__':  
    main()



