
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

def ckech_job_status(dvsn,jobid,panorama_ip,api_key):
    cmd="<show><jobs><id>"+jobid+"</id></jobs></show>"
    parameters = {'target':dvsn}
    device = base.PanDevice.create_from_device(panorama_ip, api_key=api_key)
    xmldoc=device.op(cmd=cmd,cmd_xml=False,extra_qs=parameters)
    status=xmldoc.find('./result/job/status')
    return status.text

def download_contents(dvsn,panorama_ip,api_key):
    try:
        cmd="<request><anti-virus><upgrade><download><latest></latest></download></upgrade></anti-virus></request>"
        parameters = {'target':dvsn}
        device = base.PanDevice.create_from_device(panorama_ip, api_key=api_key)
        xmldoc=device.op(cmd=cmd,cmd_xml=False,extra_qs=parameters)
        jobid=xmldoc.find('./result/job')
        return {"retval":"Jobid","Jobid":jobid.text}
    except Exception as ex:
        return {"retval":"Error","errmsg":ex.message}

def check_contents(dvsn,panorama_ip,api_key):
    try:
        cmd="<request><anti-virus><upgrade><check></check></upgrade></anti-virus></request>"
        parameters = {'target':dvsn}
        device = base.PanDevice.create_from_device(panorama_ip, api_key=api_key)
        xmldoc=device.op(cmd=cmd,cmd_xml=False,extra_qs=parameters)
        jobid=xmldoc.find('./result/job')
        return {"retval":"Jobid","Jobid":jobid.text}
    except Exception as ex:
        return {"retval":"Error","errmsg":ex.message}

def install_contents(dvsn,panorama_ip,api_key):
    try:
        cmd="<request><anti-virus><upgrade><install><version>latest</version></install></upgrade></anti-virus></request>"
        parameters = {'target':dvsn}
        device = base.PanDevice.create_from_device(panorama_ip, api_key=api_key)
        xmldoc=device.op(cmd=cmd,cmd_xml=False,extra_qs=parameters)
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
        version=dict(default=None)
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
    version=module.params['version']

    #Check AV Contents
    chk_status=check_contents(dvsn,ip_address,api_key)

    #Download AV Contents
    jobid= download_contents(dvsn,ip_address,api_key)
    if jobid["retval"]!="Error":

        wait_timeout = time.time() + 60*10

        while True:
            #Check Download status
            job_status=ckech_job_status(dvsn,jobid["Jobid"],ip_address,api_key)
            if job_status=="FIN" or time.time() > wait_timeout:
                break
            else:
                continue
            time.sleep(60)

        if job_status=="FIN":

            #Install AV Contents
            install_jobid=install_contents(dvsn,ip_address,api_key)

            if install_jobid["retval"]!="Error":
                wait_timeout = time.time() + 60*10

                while True:
                    #Check Install status
                    install_status=ckech_job_status(dvsn,install_jobid["Jobid"],ip_address,api_key)
                    if install_status=="FIN" or time.time() > wait_timeout:
                        break
                    else:
                        continue
                    time.sleep(60)

                if install_status=="FIN":
                    response = {"retval": "Contents installed successfully"}
                    module.exit_json(changed=False, meta=response)

            else:
                response = {"retval": install_jobid["errmsg"]}
                module.exit_json(changed=False, meta=response)

    else:
        response = {"retval": jobid["errmsg"]}
        module.exit_json(changed=False, meta=response)
        #module.fail_json(msg='No matching rules found.')


if __name__ == '__main__':
    main()
