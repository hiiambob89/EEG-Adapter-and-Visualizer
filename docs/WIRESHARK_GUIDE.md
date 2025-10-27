# Wireshark Analysis Guide - Find BLE Activation Command

## Step 1: Apply Filter
In the filter bar at the top, type:
```
btatt
```
Press Enter. This shows only Bluetooth ATT (Attribute Protocol) packets.

## Step 2: Find Write Operations
Look for packets with "Write Request" or "Write Command" in the Info column.

You can also apply a more specific filter:
```
btatt.opcode == 0x12 || btatt.opcode == 0x52
```
- 0x12 = Write Request (with response)
- 0x52 = Write Command (no response)

## Step 3: Find the Write Characteristic Handle
First, we need to find what handle corresponds to UUID `8653000c` (write characteristic).

Filter for characteristic discovery:
```
btatt.uuid128 == 8653000c-43e6-47b7-9cb0-5fc21d4ae340
```

Or search for any UUID from the service:
```
btatt.uuid128 contains 43e6-47b7-9cb0
```

Look for "Read By Type Response" or "Find Information Response" packets.
Note the **handle** value (usually 0x00XX format).

## Step 4: Find Write to That Handle
Once you know the handle (let's say it's 0x001e), filter for writes to it:
```
btatt.opcode == 0x12 && btatt.handle == 0x001e
```

Replace `0x001e` with the actual handle you found.

## Step 5: Extract the Command
Click on a Write Request/Command packet.

In the packet details pane (bottom), expand:
```
Bluetooth Attribute Protocol
  └─ Opcode: Write Request (0x12) or Write Command (0x52)
  └─ Handle: 0x00XX
  └─ Value: XX XX XX...  ← THIS IS THE ACTIVATION COMMAND!
```

The **Value** field contains the bytes being written!

## Step 6: Export the Value
Right-click on the "Value" field → Copy → "...as a Hex Stream"

This gives you the activation command bytes!

## Quick Shortcuts

### Timeline View
Go to **Statistics** → **I/O Graph** to see when packets were sent

### Follow the Connection
1. Find the first packet after connection
2. Right-click → **Follow** → **Bluetooth Stream**
3. This shows the entire conversation chronologically

### Export Packet Details
Select a Write packet → File → Export Packet Dissections → As Plain Text

## What to Look For

The activation command will be one of the **earliest write operations** after:
1. Connection established
2. Service discovery completed
3. Notifications enabled (CCCD descriptor write to 0x2902)

Usually the sequence is:
1. Connect
2. Discover services
3. Enable notifications (write 0x0100 to CCCD)
4. **Write activation command** ← THIS IS WHAT WE NEED
5. Data starts flowing

## Common Issues

**Can't find the UUID?**
- Try filtering just: `btatt`
- Look for "Read By Group Type Response" packets
- These show service and characteristic UUIDs

**Too many packets?**
- Use Timeline: View → Time Display Format → Seconds Since Beginning of Capture
- Focus on packets in the first 5-10 seconds after connection

**Need help identifying the device?**
Look for device address F6:82:59:5D:CC:5D in the BD_ADDR field
