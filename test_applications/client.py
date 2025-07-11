import asyncio
import websockets
from evdev import InputDevice, categorize, ecodes, list_devices


# Map key codes to commands
KEY_MAP = {
    'KEY_W': 'forward',
    'KEY_A': 'left',
    'KEY_S': 'backward',
    'KEY_D': 'right'
}

# Find a keyboard input device
def find_keyboard():
    devices = [InputDevice(path) for path in list_devices()]
    for dev in devices:
        if 'keyboard' in dev.name.lower() or 'kbd' in dev.name.lower():
            print(f"Using input device: {dev.path} ({dev.name})")
            return dev
    raise RuntimeError("No keyboard input device found. Try running with sudo.")

async def handle_keys(dev, websocket):
    async for event in dev.async_read_loop():
        if event.type == ecodes.EV_KEY:
            key_event = categorize(event)
            if key_event.keystate == key_event.key_down:  # Only trigger on key press
                key_code = key_event.keycode
                if isinstance(key_code, list):  # Sometimes it's a list
                    key_code = key_code[0]
                command = KEY_MAP.get(key_code)
                if command:
                    print(f"Sending command: {command}")
                    await websocket.send(command)
            elif key_event.keystate == key_event.key_up:  # Only trigger on key release
               await websocket.send("stop")


async def main():
    dev = find_keyboard()
    async with websockets.connect("ws://10.93.0.72:8765") as websocket:
        await handle_keys(dev, websocket)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExited cleanly.")