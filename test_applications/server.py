import time
import math
import serial
import serial.tools.list_ports
import websockets
import asyncio
import functools
import struct


Commands = {
    "turn_wheel":        0,
    "turn_while_moving": 1,
    "turn_inplace":      2,
    "drive_straight":    3,
    "drive_m_meters":    4
} #Matches up with an enum in the arduino code



def turn_wheel_by_angle(ser, wheel_no, angle, speed):
    packet = struct.pack('<BBfff', Commands["turn_wheel"], wheel_no, angle, speed, 0)
    ser.write(packet)
    ser.flush()
def turn_inplace(ser, angle, speed):
    packet = struct.pack('<BBfff', Commands["turn_inplace"], 0, angle, speed, 0)
    ser.write(packet)
    ser.flush()
def turn_while_moving(ser, radius, speed):
    packet = struct.pack('<BBfff', Commands["turn_while_moving"], 0, radius, speed, 0)
    ser.write(packet)
    ser.flush()
def drive_straight(ser, speed):
    packet = struct.pack('<BBfff', Commands["drive_straight"], 0, speed, 0, 0)
    ser.write(packet)
    ser.flush()


async def handle(websocket, ser):
    async for message in websocket:
        if message == "stop":
            drive_straight(ser,0)
        elif message == "forward":
            drive_straight(ser,30)
        elif message == "backward":
            drive_straight(ser, -30)
        elif message == "left":
            turn_while_moving(ser, 0.5, 30)
        elif message == "right":
            turn_while_moving(ser, -0.5, 30)
async def main():
    with serial.Serial("/dev/ttyACM0", 9600, timeout=100) as ser:
        async with websockets.serve(functools.partial(handle, ser=ser), "0.0.0.0", 8765):
            print("Websocket server started on port 8765")
            await asyncio.Future()

asyncio.run(main())            
        
    
