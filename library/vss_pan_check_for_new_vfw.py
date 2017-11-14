

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

#Method to identify new firewall
def comapre_sn(dvsn,dgdvsn):
    isDGAssigned=0
    for sn in dgdvsn:
        if sn == dvsn:
            isDGAssigned=1
            break
        else:
            isDGAssigned=0

    if isDGAssigned == 0:
        return True
    else:
        return False


def main():
    argument_spec = dict(
        ip_address=dict(required=True),
        password=dict(no_log=True),
        username=dict(default='admin'),
        api_key=dict(no_log=True)
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


    device = base.PanDevice.create_from_device(ip_address, api_key=api_key)
    xmldoc=device.op("show devices connected")
    lstdevices=[]
    for device in xmldoc.iter('devices'):
        entries = device.getchildren()
        for ent in entries:
            lstdevices.append(ent.get('name'))

    device = base.PanDevice.create_from_device(ip_address, api_key=api_key)
    xmldoc=device.op("show devicegroups")
    lstdgdevices=[]
    for device in xmldoc.iter('devices'):
        entries = device.getchildren()
        for ent in entries:
            lstdgdevices.append(ent.get('name'))

    devices=[]
    for dvsn in lstdevices:
        if comapre_sn(dvsn,lstdgdevices):
            print dvsn
            strtplname=""
            strdgname=""
            cmd="<show><config><running></running></config></show>"
            parameters = {'target':dvsn}
            device = base.PanDevice.create_from_device(ip_address, api_key=api_key)
            xmldoc=device.op(cmd=cmd,cmd_xml=False,extra_qs=parameters)
            for device in xmldoc.iter('tag'):
                entries = device.getchildren()
                for ent in entries:
                    if ent.get('name')=="tplname":
                        chd=ent.find("comments")
                        strtplname=chd.text
                        print chd.text
                    if ent.get('name')=="dgname":
                        chd=ent.find("comments")
                        strdgname=chd.text
                        print chd.text

            if strtplname and strdgname:
                print "Found both"

                devices.append(dvsn)

    response = {"retval": devices}
    module.exit_json(changed=False, meta=response)


if __name__ == '__main__':
    main()
