

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.basic import get_exception

try:
    import pan.xapi
    from pan.xapi import PanXapiError
    import pandevice
    from pandevice import base
    from pandevice import firewall
    from pandevice import panorama
    from pandevice import objects
    import xmltodict
    import json
    import xml.etree.ElementTree as ET
    from xml.dom import minidom
    import time
    HAS_LIB = True
except ImportError:
    HAS_LIB = False


def main():
    argument_spec = dict(
        ip_address=dict(required=True),
        password=dict(no_log=True),
        username=dict(default='admin'),
        api_key=dict(no_log=True),
        device_serial=dict(default=None),
        operation=dict(required=True, choices=['add','assign','remove','delete']),
        devicegroup=dict(default=None)
        )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False,
                           required_one_of=[['api_key', 'password']]
                           )
    if not HAS_LIB:
        module.fail_json(msg='Missing required libraries.')

    ip_address = module.params["ip_address"]
    password = module.params["password"]
    username = module.params['username']
    api_key = module.params['api_key']
    dvsn=module.params['device_serial']
    operation = module.params['operation']
    devicegroup = module.params['devicegroup']


    if operation=="assign":
        # If Essentials package, assign SVC_1_2 (Essentials) Device group to the device
        try:
            xpath_dg="/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='%s']/devices" % devicegroup
            xapi = pan.xapi.PanXapi(
                hostname=ip_address,
                api_username=username,
                api_password=password,
                api_key=api_key
            )
            xapi.set(xpath=xpath_dg,element='<entry name="%s"></entry>' % dvsn)

        except PanXapiError:
            exc = get_exception()
            module.fail_json(msg=exc.message)
        module.exit_json(changed=changed, msg='Device Group \'%s\' successfully assigned to \'%s\'' % (devicegroup, dvsn) )

    elif operation == "add":

        try:
            #If not Essentials package, create device group with host name of the firewall
            xpath_dg="/config/devices/entry[@name='localhost.localdomain']/device-group"
            xapi = pan.xapi.PanXapi(
                hostname=ip_address,
                api_username=username,
                api_password=password,
                api_key=api_key
            )
            xapi.set(xpath=xpath_dg,element='<entry name="%s"></entry>' % devicegroup )

        except PanXapiError:
            exc = get_exception()
            module.fail_json(msg=exc.message)
        module.exit_json(changed=changed, msg='Device Group \'%s\' successfully added ' % devicegroup )



if __name__ == '__main__':
    main()
