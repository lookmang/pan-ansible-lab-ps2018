

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
        device_ip=dict(default=None),
        device_username=dict(no_log=True),
        device_password=dict(no_log=True),
        device_api_key=dict(no_log=True),
        device_serial=dict(default=None),
        operation=dict(required=True, choices=['add','delete'])
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
    device_ip=module.params['device_ip']
    device_username = module.params['device_username']
    device_password = module.params['device_password']
    device_api_key = module.params['device_api_key']
    device_serial = module.params['device_serial']
    operation = module.params['operation']



    if operation=="add":

        try:

            if device_serial !="None":

                xpath_deviceconfig="/config/mgt-config/devices"
                xapi = pan.xapi.PanXapi(
                    hostname=ip_address,
                    api_username=username,
                    api_password=password,
                    api_key=api_key
                )
                xapi.set(xpath=xpath_deviceconfig,element='<entry name="%s"></entry>' % device_serial)

            else:

                cmd="<show><system><info></info></system></show>"
                device = base.PanDevice.create_from_device(device_ip, device_username,device_password,api_key=device_api_key)
                xmldoc=device.op(cmd=cmd,cmd_xml=False)
                serial_node=xmldoc.find('./result/system/serial')
                serial_text=serial_node.text

                xpath_deviceconfig="/config/mgt-config/devices"
                xapi = pan.xapi.PanXapi(
                    hostname=ip_address,
                    api_username=username,
                    api_password=password,
                    api_key=api_key
                )
                xapi.set(xpath=xpath_deviceconfig,element='<entry name="%s"></entry>' % serial_text)


        except PanXapiError:
            exc = get_exception()
            module.fail_json(msg=exc.message)
        module.exit_json(changed=True, msg='Device \'%s\' successfully added to Panorama')

    elif operation == "delete":

        try:

            module.exit_json(changed=False, msg='Need to develop ' )

        except PanXapiError:
            exc = get_exception()
            module.fail_json(msg=exc.message)
        module.exit_json(changed=False, msg='Need to develop ' )



if __name__ == '__main__':
    main()
