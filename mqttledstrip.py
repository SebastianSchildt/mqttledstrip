#!/usr/bin/env python3
from driver import apa102
import time

import json

import paho.mqtt.client as mqtt

import threading
import socket


UDP_BIND_ADDRESS = "0.0.0.0"
UDP_PORT = 6789

MQTT_BROKER = "192.168.178.43"
MQTT_LISTEN_TOPIC = "/robotstateled"

BRIGHTNESS=10
NUMLEDS=44



class StripWorker(threading.Thread):
    
    def __init__(self, numleds, mosi, clk):
      threading.Thread.__init__(self)
      self.numleds = numleds
      self.mosi = mosi
      self.clk = clk
      self.strip = apa102.APA102(num_led=self.numleds, global_brightness=BRIGHTNESS, mosi = self.mosi, sclk = self.clk, order='rgb')
      self.state="solid"
      self.speed=10
      self.color=0xff0000
      self.running=True
      self.waitForEvent=threading.Event()
      # Turn off all pixels (sometimes a few light up when the strip gets power)
      self.strip.clear_strip()

    def shutdown(self):
        print("Shutting down strip worker")
        self.running=False
        self.greenrunning=False
        self.waitForEvent.set()

    def changeState(self, newstate):
        self.state=newstate
        self.antrunning=False
        self.kittrunning=False
        self.waitForEvent.set()

    def solidState(self):
        print("Entering solid state")
        for i in range(0,self.numleds):
            self.strip.set_pixel_rgb(i, self.color, BRIGHTNESS)
        self.strip.show()
        self.waitForEvent.wait(3)

    def offState(self):
        print("Entering off state")
        self.strip.clear_strip()
        self.waitForEvent.wait(3)

    def kittState(self):
        print("Entering kitt state")
        #Build color 
        self.strip.clear_strip()

        sleep=1.0/self.speed
        tail=[  0x110000, 0x220000 ,0x440000  ,0x880000, 0xff0000  ]
        self.kittrunning=True
        while self.kittrunning:
            pos=0-len(tail)

            #Go forward
            while pos <= NUMLEDS:
                for clear in range(0,pos):
                    self.strip.set_pixel_rgb(clear, 0x000000, BRIGHTNESS)
                currPos=pos
                for point in tail:
                    self.strip.set_pixel_rgb(currPos, point,100)
                    currPos=currPos+1

                pos=pos+1
                self.strip.show()
                self.waitForEvent.wait(sleep)
                if not self.kittrunning:
                    break


            #Go backaward
            pos=NUMLEDS+1
            while pos >= 0-len(tail):
                for clear in range(pos, pos+len(tail)+1):
                    self.strip.set_pixel_rgb(clear, 0x000000, BRIGHTNESS)
                currPos=pos
                for point in reversed(tail):
                    self.strip.set_pixel_rgb(currPos, point,100)
                    currPos=currPos+1
                
                pos=pos-1
                self.strip.show()
                self.waitForEvent.wait(sleep)
                if not self.kittrunning:
                    break


    #ants
    def antState(self):
        print("Entering ant state")
        state=0

        self.antrunning=True

        while self.antrunning:
            pos=state-2
            while pos < NUMLEDS:
                self.strip.set_pixel_rgb(pos, 0x000000, BRIGHTNESS)
                self.strip.set_pixel_rgb(pos+1, self.color, BRIGHTNESS)
                self.strip.set_pixel_rgb(pos+2, 0x000000, BRIGHTNESS)
                pos=pos+3
    
            self.strip.show()
            state=(state+1)%3
            self.waitForEvent.wait(0.1)
    
    def run(self):
        while self.running:
            self.waitForEvent.clear()
            if self.state == "solid":
                self.solidState()
            elif self.state == "off":
                self.offState()
            elif self.state == "ants":
                self.antState()
            elif self.state == "kitt":
                self.kittState()
            else:
                print("Unknown state "+str(self.state+". Switching to solid"))
                self.state="solid"
        self.strip.clear_strip()
        print("StripWorker finished")

def setEffect(effectJSON):
    if not "type" in effectJSON:
        print("Unknown effect. Skipping")

    if "color" in effectJSON:
        try:
            stripThread.color=int(effectJSON["color"], 16)
        except e:
            print("Error parsing color: "+str(e))
    
    if effectJSON["type"] == "solid":
        stripThread.changeState("solid")
    elif effectJSON["type"] == "off":
        stripThread.changeState("off")
    elif effectJSON["type"] == "ants":
        stripThread.changeState("ants")
    elif effectJSON["type"] == "kitt":
        if "speed" in effectJSON:
            try:
                stripThread.speed=int(effectJSON["speed"], 10)
            except e:
                print("Error parsing speed: "+str(e))
        stripThread.changeState("kitt")

    else:
        print("Unknown effect "+str(effectJSON["type"]))


def parse_message(client, userdata, message):
    print("message received " ,str(message.payload.decode("utf-8")))
    try:
        command = json.loads(message.payload.decode("utf-8"))
        print("Received JSON "+str(command))
    except:
        print("Error decoding JSON")
    setEffect(command)

    #print("message topic=",message.topic)
    #print("message qos=",message.qos)
    #print("message retain flag=",message.retain)


serverSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serverSock.bind((UDP_BIND_ADDRESS, UDP_PORT))

stripThread = StripWorker(NUMLEDS,10,11)
stripThread.start()


client =mqtt.Client("robotled")
client.connect(MQTT_BROKER)
client.on_message=parse_message
client.subscribe(MQTT_LISTEN_TOPIC)
client.loop_start()


while True:
    data, addr = serverSock.recvfrom(1024)
    command = str(data,"utf-8").strip()
    if command == "leftfail":  
        stripThreadLeft.changeState("red")
    elif command == "rightfail":
        stripThreadLeft.changeState("green")
    elif command == "exit":
        stripThreadLeft.shutdown()
        break
    else:
        print("Unknown command "+str(command))

print("Done")






