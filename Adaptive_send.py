#!/usr/bin/env python3


import logging
import asyncio
import threading
import subprocess
import time
from aiocoap import *
import paho.mqtt.client as mqtt
import socket
from datetime import datetime, timezone


IP_receiver="192.168.0.140"
IP_broker="192.168.0.102"
packets_sent = 0
packets_lost = 0
packet_loss = 0
mode="Adaptive"




logging.basicConfig(level=logging.ERROR)
Times = [0]
Threads=[]
client=""
protocol=""
async def sendmsg_CoAP(payload): #inspired by https://github.com/chrysn/aiocoap/blob/master/clientGET.py
    try:
        protocol = await Context.create_client_context()
        request = Message(code=POST, uri='coap://'+IP_receiver+'/time', payload=payload.encode('utf-8'))
        response = await asyncio.wait_for(protocol.request(request).response, timeout=30)

        print("Message sent with CoAP")
    except Exception as e:
        #await protocol.shutdown()
        pass
    finally:
        await protocol.shutdown()



def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

def on_publish(client, userdata, mid):
    print("Message "+str(mid)+" published.")

def on_subscribe(client, userdata, mid, granted_qos):
    print("Subscribed: "+str(mid)+" "+str(granted_qos))

def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))


def sendmsg_MQTT(payload, qos):
    global client
    client.publish("python/mqtt", payload, qos)

async def sendmsg():
    global packet_loss, mode
    payload = str(round(datetime.now(timezone.utc).timestamp(),6)).ljust(17,'0')
    if mode== "MQTT" or (mode == "Adaptive" and packet_loss<0.3):
        sendmsg_MQTT(payload, 1)
    else:
         asyncio.create_task(sendmsg_CoAP(payload))

async def setup_coap():
    global protocol
    protocol = await Context.create_client_context()

def setup_mqtt():
    global client
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.connect(IP_broker, 1883)
    client.socket().setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
    thread1=threading.Thread(target=client.loop_forever)
    thread1.start()
    qos=1

def set_mode(m):
    global mode
    mode = m

def calculate_packet_loss(target_ip):
    global packet_loss
    while True:
        go_ping = f"ping -c 20 -i 0.5 {target_ip}"
        result = subprocess.run(go_ping, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in result.stdout.split('\n'):
            if 'packet loss' in line:
                packet_loss = float(line.split('%')[0].split()[-1]) / 100
                print(f"The packet loss is: {packet_loss}")

def upldate_packet_loss():
    global IP_receiver
    packet_loss_thread = threading.Thread(target=calculate_packet_loss, args=(IP_receiver,))
    packet_loss_thread.start()

async def main():
    set_mode("MQTT") #Modes are MQTT, CoAP, Adaptive
    await setup_coap()
    setup_mqtt()
    upldate_packet_loss()
    i=0
    while i<1000:
        try:
            await sendmsg()
        except Exception as e:
            print('Failed to send resource:')
            print(e)
            exit()
        await asyncio.sleep(0.1)
        i+=1
    await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
