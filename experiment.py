#! /usr/bin/python

import os
import json
import time
import paramiko
import subprocess
from datetime import datetime

FNULL = open(os.devnull, 'w')

ROUND = 1
INTERVAL = 0.5

XOSUSER = "xosadmin@opencord.org"
XOSPASS = "RTd2izDrJ8MjKHsQJtIx"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.121.44", username="vagrant")

CLEAN = "cd ~/cord/build/; make xos-teardown; make clean-openstack;"
BUILD = "cd ~/cord/build/; make -j4 build; make compute-node-refresh"
TEST = "cd ~/cord/build/; make pod-test"
TEST = 'curl -H "xos-username: %s" -H "xos-password: %s" ' % (XOSUSER, XOSPASS)
VSG = TEST + "-X POST http://xos-tosca//xos-tosca/run --data-binary @/opt/cord_profile/test-subscriber.yaml"

OPENRC = "source /opt/cord_profile/admin-openrc.sh; "
NOVA = OPENRC + "nova list --all-tenants"
NEUTRON = OPENRC + "neutron net-list"
XOSAPI = 'curl -H "xos-username: %s" -H "xos-password: %s" http://xos-tosca/xos-tosca/run' % (XOSUSER, XOSPASS)
ELINEAPI = 'curl -H "xos-username: %s" -H "xos-password: %s" http://localhost/xosapi/v1/elineservice/elineserviceinstances' % (XOSUSER, XOSPASS)
VSGAPI = 'curl -H "xos-username: %s" -H "xos-password: %s" http://localhost/xosapi/v1/vsg/vsgserviceinstances' % (XOSUSER, XOSPASS)

def exec_head(command):
    global client
    _, stdout, stderr = client.exec_command(command)
    stdout = [x for x in stdout if x != ""]
    count = len(stdout) - 4
    stdout = "".join(stdout)
    return stdout, count

def exec_local(command):
    """ Used in: CLEAN & BUILD, because we need command to be done """
    subprocess.call(command, shell=True, stdout=FNULL, stderr=FNULL)

def Popen_local(command):
    """ Used in: TEST, after we ran test, then watch how much time we need """
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    return stdout

def now():
    return datetime.strftime(datetime.now(), "%H:%M:%S.%f")

def log(x, title):
    print("[%s] %d time evaluate: %s" % (now(), x, title))

results = []

for x in range(1, ROUND + 1):
    # Clean Previous Status
    log(x, "Clean Environment")
    #exec_local(CLEAN)
    # Build M-CORD Machine
    log(x, "Build Environment")
    #exec_local(BUILD)

    # Time for start test
    start = time.time()
    log(x, "Start vSG")
    #stdout = Popen_local(TEST)
    stdout,_ = exec_head(VSG)
    print(stdout)

    # Routine check network up
    log(x, "Routine Check Network")
    while True:
        stdout, count = exec_head(NEUTRON)
        if count >= 3:
            log(x, "Routine Check Network: DONE")
            neutron_time = time.time()
            break

    # Routine check VM up
    log(x, "Routine Check Virtual Netowrking Function VM")
    while True:
        stdout, count = exec_head(NOVA)
        if stdout.count("ACTIVE") >= 2:
            log(x, "Routine Check Virtual Networking Function VM: DONE")
            nova_time = time.time()
            break

    # Routing check synchronizer done
    log(x, "Routine Check Synchronizer is done or not")
    while True:
        stdout, _ = exec_head(VSGAPI)
        j = json.loads(stdout)
        if "items" not in j:
            continue
        if len(j["items"]) == 0:
            continue
        if "backend_status" not in j["items"][0]:
            continue
        if j["items"][0]["backend_status"] == "OK":
            log(x, "Routine Check Synchronizer is don or not: DONE")
            synced_time = time.time()
            break

    results.append([x, neutron_time - start, nova_time - start, synced_time - start])

with open("result_modify_accerlatedvsg2.log", "w") as f:
    for x in results:
        f.write(", ".join(str(x)))
