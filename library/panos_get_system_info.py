

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
        system_info=dict(default='hostname')
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
    system_info = module.params['system_info']

    try:

            cmd="<show><system><info></info></system></show>"
            device = base.PanDevice.create_from_device(ip_address,username,password,api_key=api_key)
            xmldoc=device.op(cmd=cmd,cmd_xml=False)
            sysinfo_node=xmldoc.find('./result/system/%s' % system_info)
            sysinfo_text=sysinfo_node.text

    except PanXapiError:
        exc = get_exception()
        module.fail_json(msg=exc.message)
    #module.exit_json(stdout_lines=json.dumps(sysinfo_text),
    #msg='System Info')

    response = {"retval": sysinfo_text}
    module.exit_json(changed=False, meta=response)



if __name__ == '__main__':
    main()
