
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
    import urllib2
    import urllib
    import ssl

    HAS_LIB = True
except ImportError:
    HAS_LIB = False

def fw_api_request(req_url):
    #Send API request to the firewall and return the response
    sslctx = ssl.create_default_context()
    sslctx.check_hostname = False
    sslctx.verify_mode = ssl.CERT_NONE
    url = req_url
    response = urllib2.urlopen(url, context=sslctx)
    return response

def ckech_job_status(dvsn,jobid,panorama_ip,api_key):
    cmd="<show><jobs><id>"+jobid+"</id></jobs></show>"
    device = base.PanDevice.create_from_device(panorama_ip, api_key=api_key)
    xmldoc=device.op(cmd=cmd,cmd_xml=False)
    status=xmldoc.find('./result/job/status')
    return status.text


def commit_panorama_template(panorama_ip,api_key,dvsn,tmpl_stack):

    tmpl_commit_xml=  [
            "<commit-all>",
            "<template-stack>",
            "<name>%s</name>",
            "<merge-with-candidate-cfg>yes</merge-with-candidate-cfg>",
            "<force-template-values>yes</force-template-values>",
            "<device>",
            "<member>%s</member>",
            "</device>",
            "</template-stack>",
            "</commit-all>"
    ]

    commit_cmd_tmpl= (''.join(tmpl_commit_xml)) % (tmpl_stack, dvsn)
    try:
        cmd = "/api/?type=commit&action=all&"
        parameters = {'cmd':commit_cmd_tmpl}
        url = "https://"+panorama_ip+cmd+"Key="+api_key+"&"+urllib.urlencode(parameters)
        xmlstring = fw_api_request(url).read()
        xmldoc= ET.fromstring(xmlstring)
        jobid=xmldoc.find('./result/job')
        return {"retval":"Jobid","Jobid":jobid.text}
    except Exception as ex:
        return {"retval":"Error","errmsg":ex.message}


def commit_to_panorama(panorama_ip,api_key):
    try:
        cmd = '/api/?type=commit&'
        parameters = {'cmd':'<commit></commit>'}
        url = "https://"+panorama_ip+cmd+"Key="+api_key+"&"+urllib.urlencode(parameters)
        xmlstring = fw_api_request(url).read()
        xmldoc= ET.fromstring(xmlstring)
        jobid=xmldoc.find('./result/job')
        return {"retval":"Jobid","Jobid":jobid.text}
    except Exception as ex:
        return {"retval":"Error","errmsg":ex.message}

def commit_panorama_device_grp(panorama_ip,api_key,dvsn,device_group):

    dg_commit_xml= [
            "<commit-all>",
            "<shared-policy>",
            "<merge-with-candidate-cfg>yes</merge-with-candidate-cfg>",
            "<include-template>yes</include-template>",
            "<force-template-values>yes</force-template-values>",
            "<device-group>",
            "<entry name=\"%s\">",
            "<devices>",
            "<entry name=\"%s\"/>",
            "</devices>",
            "</entry>",
            "</device-group>",
            "</shared-policy>",
            "</commit-all>"
    ]

    commit_cmd_dg= (''.join(dg_commit_xml)) % (device_group, dvsn)
    try:
        cmd = "/api/?type=commit&action=all&"
        parameters = {'cmd':commit_cmd_dg}
        url = "https://"+panorama_ip+cmd+"Key="+api_key+"&"+urllib.urlencode(parameters)
        xmlstring = fw_api_request(url).read()
        xmldoc= ET.fromstring(xmlstring)
        jobid=xmldoc.find('./result/job')
        return {"retval":"Jobid","Jobid":jobid.text}
    except Exception as ex:
        return {"retval":"Error","errmsg":ex.message}


def main():
    argument_spec = dict(
        ip_address=dict(required=True),
        password=dict(no_log=True),
        username=dict(default='admin'),
        api_key=dict(no_log=True),
        device_serial=dict(required=True),
        template=dict(default=None),
        device_group=dict(default=None),
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
    template=module.params['template']
    device_group=module.params['device_group']


    panorama_comit_job=commit_to_panorama(ip_address,api_key)
    if panorama_comit_job["retval"]!="Error":
        wait_timeout = time.time() + 60*10
        while True:
            pano_com_status=ckech_job_status(dvsn,panorama_comit_job["Jobid"],ip_address,api_key)
            if pano_com_status=="FIN" or time.time() > wait_timeout:
                break
            else:
                continue
            time.sleep(60)

        if pano_com_status=="FIN":
            jobid= commit_panorama_template(ip_address,api_key,dvsn,template)
            if jobid["retval"]!="Error":
                wait_timeout = time.time() + 60*10

                while True:
                    job_status=ckech_job_status(dvsn,jobid["Jobid"],ip_address,api_key)
                    if job_status=="FIN" or time.time() > wait_timeout:
                        break
                    else:
                        continue
                    time.sleep(60)

                if job_status=="FIN":
                    install_jobid=commit_panorama_device_grp(ip_address,api_key,dvsn,device_group)
                    if install_jobid["retval"]!="Error":
                        wait_timeout = time.time() + 60*10

                        while True:
                            install_status=ckech_job_status(dvsn,install_jobid["Jobid"],ip_address,api_key)
                            if install_status=="FIN" or time.time() > wait_timeout:
                                break
                            else:
                                continue
                            time.sleep(60)

                        if install_status=="FIN":
                            response = {"retval": "Successfully committed both template and device group"}
                            module.exit_json(changed=False, meta=response)

                    else:
                        response = {"retval": install_jobid["errmsg"]}
                        module.exit_json(changed=False, meta=response)
                        #module.fail_json(msg='No matching rules found.')
            else:
                response = {"retval": jobid["errmsg"]}
                module.exit_json(changed=False, meta=response)
                #module.fail_json(msg='No matching rules found.')
    else:
        response = {"retval": jobid["errmsg"]}
        module.exit_json(changed=False, meta=response)
            #module.fail_json(msg='No matching rules found.')

if __name__ == '__main__':
    main()
