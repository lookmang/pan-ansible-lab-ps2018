

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
        device_serial=dict(required=True),
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

    strtplname=""
    strdgname=""

    cmd="<show><config><running></running></config></show>"
    parameters = {'target':dvsn}
    device = base.PanDevice.create_from_device(ip_address, api_key=api_key)
    xmldoc=device.op(cmd=cmd,cmd_xml=False,extra_qs=parameters)

    or_hostname=xmldoc.find('./result/config/devices/entry/deviceconfig/system/hostname')
    or_hostname_val=or_hostname.text
    new_hostname_val=or_hostname.text.replace("-","_")

    devices=[]
    devices.append(new_hostname_val)
    response={'retval':'None'}

    for device in xmldoc.iter('tag'):
        entries = device.getchildren()
        for ent in entries:
            if ent.get('name')=="tplname":
                chd=ent.find("comments")
                strtplname=chd.text
            if ent.get('name')=="dgname":
                chd=ent.find("comments")
                strdgname=chd.text

    if strdgname=="SVC_1_2":
        # If Essentials package, assign SVC_1_2 (Essentials) Device group to the device
        try:
            xpath_dg="/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='SVC_1_2']/devices"
            xapi = pan.xapi.PanXapi(
                hostname=ip_address,
                api_key=api_key
            )
            xapi.set(xpath=xpath_dg,element='<entry name="%s"></entry>' % dvsn)

            xpath_tmpl="/config/devices/entry[@name='localhost.localdomain']/template-stack/entry[@name='NaaS_SRBHONBG_1_01']/devices"
            xapi = pan.xapi.PanXapi(
                hostname=ip_address,
                api_key=api_key
            )
            xapi.set(xpath=xpath_tmpl,element='<entry name="%s"></entry>' % dvsn)

            response={'retval':'Template and DG added successfully','template':'NaaS_SRBHONBG_1_01','DG':'SVC_1_2'}

        except Exception as ex:
            response= {"retval":"Error","errmsg":ex.message}
    else:

        #If not Essentials package, create device group with host name of the firewall
        xpath_dg="/config/devices/entry[@name='localhost.localdomain']/device-group"
        xapi = pan.xapi.PanXapi(
            hostname=ip_address,
            api_key=api_key
        )
        xapi.set(xpath=xpath_dg,element='<entry name="%s"><devices><entry name=\'%s\'/></devices></entry>' % (or_hostname_val, dvsn) )

        #Move the DG under parent DG (SVC_0)
        dg_move_xml = [
            '<request>',
            '<move-dg>',
            '<entry name="%s">',
            '<new-parent-dg>SVC_0</new-parent-dg>',
            '</entry>',
            '</move-dg>',
            '</request>'
        ]

        request_cmd_xml = (''.join(dg_move_xml)) % (or_hostname_val)
        xapi.op(cmd=request_cmd_xml,cmd_xml=False)

        #Clone SVC_2_2 to new DG with hostname
        load_xml = [
            '<load>',
            '<config>',
            '<partial>',
            '<from>running-config.xml</from>',
            '<from-xpath>/config/devices/entry[@name=\'localhost.localdomain\']/device-group/entry[@name=\'SVC_2_2\']</from-xpath>',
            '<to-xpath>/config/devices/entry[@name=\'localhost.localdomain\']/device-group/entry[@name=\'%s\']</to-xpath>',
            '<mode>merge</mode>',
            '</partial>',
            '</config>',
            '</load>'
        ]
        load_cmd = (''.join(load_xml)) % (or_hostname_val)
        xapi.op(cmd=load_cmd,cmd_xml=False)

        #Clone Template
        tmpl_clone_src_xpath="/config/devices/entry[@name='localhost.localdomain']/template/entry[@name='1_02']"
        tmpl_clone_xpath="/config/devices/entry[@name='localhost.localdomain']/template"
        xapi.clone(xpath=tmpl_clone_xpath,xpath_from=tmpl_clone_src_xpath,newname=new_hostname_val )

        #Clone Template stack
        tmplst_clone_src_xpath="/config/devices/entry[@name='localhost.localdomain']/template-stack/entry[@name='NaaS_SRBHONBG_1_01']"
        tmplst_clone_xpath="/config/devices/entry[@name='localhost.localdomain']/template-stack"
        xapi.clone(xpath=tmplst_clone_xpath,xpath_from=tmplst_clone_src_xpath,newname=new_hostname_val+"_ST" )

        #Move new template to the top within the template stack
        load_tmpl_mpove_xml = [
              '<templates>',
              '<member>%s</member>',
              '<member>SRBHONBG</member>',
              '<member>NaaS</member>',
              '</templates>'
        ]
        tmpl_mpove_xml= (''.join(load_tmpl_mpove_xml)) % (new_hostname_val)
        tmplst_move_xpath="/config/devices/entry[@name='localhost.localdomain']/template-stack/entry[@name='"+new_hostname_val+"_ST']/templates"
        xapi.edit(xpath=tmplst_move_xpath,element=tmpl_mpove_xml)


        tmplst_device_xpath="/config/devices/entry[@name='localhost.localdomain']/template-stack/entry[@name='"+new_hostname_val+"_ST']/devices"
        xapi.edit(xpath=tmplst_device_xpath,element='<devices><entry name=\'%s\'/></devices>' % dvsn)

        response={'retval':'Template and DG added successfully','template':new_hostname_val+"_ST",'DG':or_hostname_val}


    module.exit_json(changed=False, meta=response)


if __name__ == '__main__':
    main()
