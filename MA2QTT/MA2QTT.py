#!/usr/bin/python3
import telnetlib
import threading
import random
from time import sleep
from paho.mqtt import client as mqtt_client

#############################
# Almost never tested
#
# Github: https://github.com/kinglevel/MA2_k_plugins/MA2QTT
# Please commit or post updates for the community.


"""
                      /mMNh-
                      NM33My
                      -ydds`
                        /.
                        ho
         +yy/          `Md           +yy/
        .N33N`         +MM.         -N33N`
         -+o/          hMMo          o++-
            d:        `MMMm         oy
-:.         yNo`      +MMMM-       yM+        .:-`
d33N:       /MMh.     dMMMMs     -dMM.       :N33d
+ddd:       `MMMm:   .MMMMMN    /NMMd        :hdd+
  ``hh+.     hMMMN+  +MMMMMM: `sMMMMo     -ody `
    -NMNh+.  +MMMMMy`d_SUM_My.hMMMMM-  -odNMm`
     /MMMMNh+:MMMMMMmMMMMMMMNmMMMMMN-odNMMMN-
      oMMMMMMNMMMMMMMMMMMMMMMMMMMMMMNMMMMMM/
       hMMMMMMMMM---LEDvard---MMMMMMMMMMMMo
       `mMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMh
        .NMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMm`
         :mmmmmmmmmmmmmmmmmmmmmmmmmmmmmm-
        `://////////////////////////////.
    -+ymMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMNho/.
"Vision will blind. Severance ties. Median am I. True are all lies"
"""


# --------------------------------------------------------------------------------------------------


##########################################
# This script bridges all messages from a MQTT broker with a specific topic to
# an MA2 telnet remote session.
#
# sloppy made, use with caution, no support given.
#
# At some point it will try to reconnect if the connection is lost, but it is not 100% failsafe.
#
# An example setup is:
# * Have a laptop on FOH, with internetz and MA2 network access.
# * Use the App "EasyMQTT" on ios and a paired watch.
# * Have an offsite MQTT Broker with your own login details and security.
# * Send any command you like from iphone or watch os, with the built in shortcuts app, to the offsite MQTT broker.
#
# The software will pick up the messages from the broker and relay it to the MA2 telnet session locally.
#
# The purpose of this is that it works on cellular network, when properly set up.
# So for example, when focusing lights, it will be easier to press next instead of relying on wifi,
# bad networks for remote desktops or running back to the consoles. Just a small piece of data payload is needed..
#
# Any normal MA2 command can be sent.
#
# Setup your details below before running



# --------------------------------------------------------------------------------------------------


#!!!-Quick and dirty install instructions-!!!
#
# --------------------------------------------------------------------------------
# If you do not have a MQTT broker, here are a small checklist on how to do it on Arch.
#
#
# * Install Mosquitto server (arch example: yay mqtt, choose Mosquitto)
# * Mosquitto server conf settings to look out for (/etc/mosquitto/mosquitto.conf):
# - allow_anonymous false
# - password_file /xxx/xxx/pswfile
# - listener 1883 xxx.xxx.xxx.xxx (local ip)
#
# * Generate password file with mosquitto_passwd.
# * enable and start mosquitto.service in systemctl.
# * reboot server and check if it autostarts etc...
#
# * Open port 1883 to the server as needed to the internetz
#
# --------------------------------------------------------------------------------
# Checklist for this script
#
# * Check requirements.txt, install with pip -r requirements.txt if needed
# * Check conf settings below and adjust
# * Add folder to $PATH if you want quick access from cmd line
# * check executable permissions...
#
# * In MA2, check, Setup -> Console -> Global settings
# * Enable Remotes and Telnet
#
# * Run this script with ./MA2QTT.py
#
# --------------------------------------------------------------------------------
# Send message/command with ios app "EasyMQTT" or with cmd mosquitto_pub:
#
# * mosquitto_pub -h <DNS ADRESS OR IP TO SERVER> -t LX/grandMA2 -m "clearall" -u <USERNAME> -P <PASSWORD>
#



################################
# MA locally FOH Telnet config

MAip = 'xxx.xxx.xxx.xxx'
MAport = 30000
MAuser = "administrator"
MApassword = "admin"
MAtimeout = 5
MApingtime = 5

################################
# MQTT offsite broker config

MQTTip = 'xxx.xxx.xxx.xxx'
MQTTport = 1883
MQTTtopic = "LX/grandMA2"
MQTTuser = 'xxxx'
MQTTpass = 'xxxx'




######################################################################################
################################
# TELNET client

def MAtelnetsession():

    global session
    global TelConStatus
    global TelConInp

    TelConAnswDis = b'\nRemote commandline disabled\n\r'
    TelConAnsLogin = b'Please login !\r\n\r [Channel]>\x1b[K'
    TelConStatus = False
    TelConInp = False

    #################
    # Try connection
    while True:
        try:

            session = telnetlib.Telnet(MAip, MAport, timeout=MAtimeout)
            session.set_debuglevel(0)
            response = session.read_until(TelConAnsLogin)
            TelConStatus = True
            TelConInp = False
        except EOFError:
            print("Connection closed")
            TelConStatus = False
        except TimeoutError:
            print("No response from server")
            TelConStatus = False

        ################
        # Responses
        if TelConStatus == True:
            if TelConAnsLogin in response:
                print("Login Screen")
                session.write(b"login " + str.encode(MAuser) + b" " + str.encode(MApassword))
                session.write(b'\r')
                session.write(b'chat \"MQTT bridge connected\"')
                session.write(b'\r')
                while True:
                    ##########
                    # Keeping the session alive
                    try:
                        session.write(b"chat \"MQTT bridge ping...\"")
                        session.write(b'\r')
                        print("MQTT bridge ping...")
                        TelConInp = True
                        sleep(MApingtime)
                    except BrokenPipeError:
                        print("MA down")
                        sleep(1)
                        break
            if TelConAnswDis in response:
                print("Remote Commandline Disabled")
                sleep(1)


def MAsendCmd(cmd, session):
    while True:
        try:
            session.write(str.encode(cmd))
            session.write(b'\r')
            print("sending command: " + cmd)
            sleep(1)
        except BrokenPipeError:
            sleep(2)
            print("Connection closed...")
            break



################################################################################
# MQTT Client

def connect_mqtt() -> mqtt_client:
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(f'python-mqtt-{random.randint(0, 100)}')
    client.username_pw_set(MQTTuser, MQTTpass)
    client.on_connect = on_connect
    client.connect(MQTTip, MQTTport)
    return client


def subscribe(client: mqtt_client):
    def on_message(client, userdata, msg):
        print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        MQTTtelnet(msg.payload.decode())

    client.subscribe(MQTTtopic)
    client.on_message = on_message



def MQTTclient():
    try:
        client = connect_mqtt()
        subscribe(client)
        client.loop_forever()
    except ConnectionRefusedError:
        print("Connection was refused")

#############################################
# Bridge magic

def MQTTtelnet(cmd):
    print("Sending message to telnet")
    session.write(str.encode(cmd))
    session.write(b'\r')

##########################################################
# Main

def main():
    print("started...")

    conInit = threading.Thread(target=MAtelnetsession)
    print("Starting telnet thread...")
    conInit.start()


    while True:
        try:
            if TelConInp == True:
                happypuppy = threading.Thread(target=MQTTclient)
                happypuppy.start()
                break
        except NameError:
            print("waiting for telnet session to start...")
            sleep(1)
            continue
        except BrokenPipeError:
            continue

    print("Script is running...")





############
# Breakup gobo magic...
main()


