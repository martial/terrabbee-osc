
#!/usr/bin/env python3
###### TeraRanger Evo Example Code STD #######
#                                            #
# All rights reserved Terabee France (c) 2018#
#                                            #
############ www.terabee.com #################

import serial
import serial.tools.list_ports
import sys
import crcmod.predefined  # To install: pip install crcmod
from pythonosc import udp_client
import sys
import argparse
import math
import time

def findEvo():
    # Find Live Ports, return port name if found, NULL if not
    print('Scanning all live ports on this PC')
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        # print p # This causes each port's information to be printed out.
        if "5740" in p[2]:
            print('Evo found on port ' + p[0])
            return p[0]
    return 'NULL'


def openEvo(portname):
    print('Attempting to open port...')
    # Open the Evo and catch any exceptions thrown by the OS
    print(portname)
    evo = serial.Serial(portname, baudrate=115200, timeout=2)
    # Send the command "Binary mode"
    set_bin = (0x00, 0x11, 0x02, 0x4C)
    # Flush in the buffer
    evo.flushInput()
    # Write the binary command to the Evo
    evo.write(set_bin)
    # Flush out the buffer
    evo.flushOutput()
    print('Serial port opened')
    return evo


def get_evo_range(evo_serial):
    crc8_fn = crcmod.predefined.mkPredefinedCrcFun('crc-8')
    # Read one byte
    data = evo_serial.read(1)
    if data == b'T':
        # After T read 3 bytes
        frame = data + evo_serial.read(3)
        if frame[3] == crc8_fn(frame[0:3]):
            # Convert binary frame to decimal in shifting by 8 the frame
            rng = frame[1] << 8
            rng = rng | (frame[2] & 0xFF)
        else:
            return float('nan')
    # Check special cases (limit values)
    else:
        return float('nan')

    # Checking error codes
    if rng == 65535: # Sensor measuring above its maximum limit
        dec_out = -1
    elif rng == 1: # Sensor not able to measure
        dec_out = float('nan')
    elif rng == 0: # Sensor detecting object below minimum range
        dec_out = 0.5
    else:
        # Convert frame in meters
        dec_out = rng / 1000.0
    return dec_out

def run(args):

    port = findEvo()
    
    #start osc
    client = udp_client.SimpleUDPClient(args.ip, args.port)

    if port == 'NULL':
        print("Sorry couldn't find the Evo. Exiting.")
        sys.exit()
    else:
        evo = openEvo(port)
        blurRate = 0.95
        smoothed = 0.0
    
    running = True;
    while running:
        try:
            range = float(get_evo_range(evo))
            
            if range == -1:
                client.send_message("/"+args.address, range)
                print("sending to " + args.ip + " " + str(smoothed))

            else:
            
                if ( math.isnan(range)):
                    range = smoothed
           
                smoothed = blurRate * smoothed +  (1.0 - blurRate) * range;
                    
                client.send_message("/"+args.address, smoothed)
                print("sending to " + args.ip + " " + str(smoothed))
            
        except Exception as e:
            print(e)
            print("Error.. try to start again")
            time.sleep(1.0)
            print("Trying")
            run(args)
            
            break

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Captor sensor to OCC')
    parser.add_argument('--portname', type=str, help='If set, force the USB port for the sensor')
    parser.add_argument('--ip', default="127.0.0.1", type=str, help='OSC IP to send to')
    parser.add_argument('--port', default=5005, type=int, help='OSC port')
    parser.add_argument('--address', default="range", type=str, help='OSC address to send to')
    args = parser.parse_args()
    print(args.portname)
    print('Starting Evo data streaming')
    # Get the port the evo has been connected to
    
    run(args)

    evo.close()
    sys.exit()
