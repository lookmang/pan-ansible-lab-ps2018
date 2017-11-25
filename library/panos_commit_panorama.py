

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


def panorma_api_request(req_url):
    #Send API request to the Panorama and return the response
    sslctx = ssl.create_default_context()
    sslctx.check_hostname = False
    sslctx.verify_mode = ssl.CERT_NONE
    url = req_url
    response = urllib2.urlopen(url, context=sslctx)
    return response

def get_panorama_api_key(panorama_ip, username, password):
    #Generate Panorama Api Key
    url='https://' + panorama_ip + '/api/?type=keygen&user='+username+'&password='+password+''
    parsedKey = minidom.parseString(panorma_api_request(url).read())
    nodes = parsedKey.getElementsByTagName('key')
    api_key = nodes[0].firstChild.nodeValue
    return api_key

def ckech_job_status(jobid,ip_address,api_key,username,password):

    if api_key is None:
        api_key = get_panorama_api_key(ip_address,username,password)

    cmd="<show><jobs><id>"+jobid+"</id></jobs></show>"
    device = base.PanDevice.create_from_device(ip_address,username,password,api_key=api_key)
    xmldoc=device.op(cmd=cmd,cmd_xml=False)
    status=xmldoc.find('./result/job/status')
    result=xmldoc.find('./result/job/result')
    return {"status":status.text,"result":result.text}


def panorama_commit_api(operation,admin):

    if operation =='admin':
        cmd = '/api/?type=commit&'
        parameters = {'cmd': '<commit><partial><admin><member>%s</member></admin></partial></commit>' % admin}

        return {"cmd":cmd,"parameters":parameters}
    else:
        cmd = '/api/?type=commit&'
        parameters = {'cmd': '<commit></commit>'}
        return {"cmd":cmd,"parameters":parameters}

def template_commit_api(template,device_serial):

    if device_serial is not None:
        tmpl_commit_xml=  [
                "<commit-all>",
                "<template>",
                "<name>%s</name>",
                "<merge-with-candidate-cfg>yes</merge-with-candidate-cfg>",
                "<force-template-values>yes</force-template-values>",
                "<device>",
                "<member>%s</member>",
                "</device>",
                "</template>",
                "</commit-all>"
        ]
        commit_cmd_tmpl= (''.join(tmpl_commit_xml)) % (template, device_serial)
    else:
        tmpl_commit_xml=  [
                "<commit-all>",
                "<template>",
                "<name>%s</name>",
                "<merge-with-candidate-cfg>yes</merge-with-candidate-cfg>",
                "<force-template-values>yes</force-template-values>",
                "</template>",
                "</commit-all>"
        ]
        commit_cmd_tmpl= (''.join(tmpl_commit_xml)) % (template)

    cmd = "/api/?type=commit&action=all&"
    parameters = {'cmd':commit_cmd_tmpl}
    return {"cmd":cmd,"parameters":parameters}


def template_stack_commit_api(template_stack,device_serial):

    if device_serial is not None:
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
        commit_cmd_tmpl= (''.join(tmpl_commit_xml)) % (template_stack, device_serial)
    else:
        tmpl_commit_xml=  [
                "<commit-all>",
                "<template-stack>",
                "<name>%s</name>",
                "<merge-with-candidate-cfg>yes</merge-with-candidate-cfg>",
                "<force-template-values>yes</force-template-values>",
                "</template-stack>",
                "</commit-all>"
        ]
        commit_cmd_tmpl= (''.join(tmpl_commit_xml)) % (template_stack)

    cmd = "/api/?type=commit&action=all&"
    parameters = {'cmd':commit_cmd_tmpl}
    return {"cmd":cmd,"parameters":parameters}


def devicegroup_commit_api(devicegroup,device_serial):

    if device_serial is not None:

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
        commit_cmd_dg= (''.join(dg_commit_xml)) % (devicegroup, device_serial)
    else:
        dg_commit_xml= [
                "<commit-all>",
                "<shared-policy>",
                "<merge-with-candidate-cfg>yes</merge-with-candidate-cfg>",
                "<include-template>yes</include-template>",
                "<force-template-values>yes</force-template-values>",
                "<device-group>",
                "<entry name=\"%s\"></entry>",
                "</device-group>",
                "</shared-policy>",
                "</commit-all>"
        ]
        commit_cmd_dg= (''.join(dg_commit_xml)) % (devicegroup)

    cmd = "/api/?type=commit&action=all&"
    parameters = {'cmd':commit_cmd_dg}
    return {"cmd":cmd,"parameters":parameters}


def commit(panorama_ip,api_key,username,password,cmd,parameters):

    try:

        if api_key is None:
            api_key = get_panorama_api_key(panorama_ip,username,password)

        #urlparameters = {'cmd':parameters}
        url = "https://"+panorama_ip+cmd+"Key="+api_key+"&"+urllib.urlencode(parameters)
        xmlstring = panorma_api_request(url).read()
        xmldoc= ET.fromstring(xmlstring)
        jobid=xmldoc.find('./result/job')

        return {"retval":"Jobid","Jobid":jobid.text}
    except Exception as ex:
        return {"retval":"Error","errmsg":ex.message}


def main():
    argument_spec = dict(
        ip_address=dict(required=True),
        username=dict(default='admin'),
        password=dict(no_log=True),
        api_key=dict(no_log=True),
        admin=dict(default=None),
        devicegroup=dict(default=None),
        template=dict(default=None),
        template_stack=dict(default=None),
        device_serial=dict(default=None),
        operation=dict(required=True, choices=['admin','devicegroup','template','template_stack','all'])
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
    admin=module.params['admin']
    devicegroup=module.params['devicegroup']
    template=module.params['template']
    template_stack=module.params['template_stack']
    operation=module.params['operation']
    device_serial=module.params['device_serial']

    if operation=="admin" or operation=="all":

        #Commit to Panorama
        panorama_api_req=panorama_commit_api(operation,admin)
        jobid=commit(ip_address,api_key,username,password,panorama_api_req["cmd"],panorama_api_req["parameters"])

        if jobid["retval"]!="Error":
            wait_timeout = time.time() + 60*10
            time.sleep(60)
            while True:
                job_status=ckech_job_status(jobid["Jobid"],ip_address,api_key,username,password)
                if job_status["status"]=="FIN" and job_status["result"]=="OK":
                    module.exit_json(changed=True, msg='Commit successful')
                    break
                elif job_status["status"]=="FIN" and job_status["result"]=="FAIL":
                    module.fail_json(changed=False, msg='Commit failed')
                    break
                elif time.time() > wait_timeout:
                    module.fail_json(changed=False, msg='Commit time out')
                    break
                else:
                    continue

                time.sleep(60)
        else:
            module.fail_json(changed=False, msg='Commit failed - '+jobid['errmsg'])

    elif operation=="template":
        # Commit Template
        template_api_req=template_commit_api(template,device_serial)
        jobid= commit(ip_address,api_key,username,password,template_api_req["cmd"],template_api_req["parameters"])

        if jobid["retval"]!="Error":
            wait_timeout = time.time() + 60*10
            time.sleep(60)
            while True:
                job_status=ckech_job_status(jobid["Jobid"],ip_address,api_key,username,password)
                if job_status["status"]=="FIN" and job_status["result"]=="OK":
                    module.exit_json(changed=True, msg='Commit successful')
                    break
                elif fail_json["status"]=="FIN" and job_status["result"]=="FAIL":
                    module.exit_json(changed=False, msg='Commit failed')
                    break
                elif time.time() > wait_timeout:
                    module.fail_json(changed=False, msg='Commit time out')
                    break
                else:
                    continue

                time.sleep(60)
        else:
            module.fail_json(changed=False, msg='Commit failed - '+jobid['errmsg'])

    elif operation=="template_stack":
        # Commit Template
        template_stack_api_req=template_stack_commit_api(template_stack,device_serial)
        jobid= commit(ip_address,api_key,username,password,template_stack_api_req["cmd"],template_stack_api_req["parameters"])

        if jobid["retval"]!="Error":
            wait_timeout = time.time() + 60*10
            time.sleep(60)
            while True:
                job_status=ckech_job_status(jobid["Jobid"],ip_address,api_key,username,password)
                if job_status["status"]=="FIN" and job_status["result"]=="OK":
                    module.exit_json(changed=True, msg='Commit successful')
                    break
                elif job_status["status"]=="FIN" and job_status["result"]=="FAIL":
                    module.fail_json(changed=False, msg='Commit failed')
                    break
                elif time.time() > wait_timeout:
                    module.fail_json(changed=False, msg='Commit time out')
                    break
                else:
                    continue

                time.sleep(60)
        else:
            module.fail_json(changed=False, msg='Commit failed - '+jobid['errmsg'])

    elif operation=="devicegroup":
        # Commit Template
        devicegroup_api_req=devicegroup_commit_api(devicegroup,device_serial)
        jobid= commit(ip_address,api_key,username,password,devicegroup_api_req["cmd"],devicegroup_api_req["parameters"])

        if jobid["retval"]!="Error":
            wait_timeout = time.time() + 60*10
            time.sleep(90)
            while True:
                job_status=ckech_job_status(jobid["Jobid"],ip_address,api_key,username,password)
                if job_status["status"]=="FIN" and job_status["result"]=="OK":
                    module.exit_json(changed=True, msg='Commit successful')
                    break
                elif job_status["status"]=="FIN" and job_status["result"]=="FAIL":
                    module.fail_json(changed=False, msg='Commit failed')
                    break
                elif time.time() > wait_timeout:
                    module.fail_json(changed=False, msg='Commit time out')
                    break
                else:
                    continue

                time.sleep(60)
        else:
            module.fail_json(changed=False, msg='Commit failed - '+jobid['errmsg'])

if __name__ == '__main__':
    main()
