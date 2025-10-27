# Serenibrain Stream Control Commands - DISCOVERED! ✓

## Summary
- **Total packets analyzed**: 7,865
- **Write commands found**: 158
- **EEG data notifications**: 4,010
- **Streaming sessions detected**: 2

## KEY DISCOVERY: Stream Control Protocol

### Command Format
All control commands use this format:
```
"CTRL" + 0x00 + <command_id> + 0x00 + <parameter>
```

### Critical Commands

#### 1. START STREAMING
**Command sent before streaming begins:**
```python
# Handle 0x0014
bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x03, 0x00, 0x05])
# ASCII: "CTRL" + 0x00 + 0x03 + 0x00 + 0x05
```

Also appears before Session 1:
```python
bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x04, 0x00, 0x01])
# ASCII: "CTRL" + 0x00 + 0x04 + 0x00 + 0x01
```

#### 2. STOP STREAMING
**Command sent AFTER streaming ends:**
```python
# Handle 0x0014
bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x03, 0x00, 0x03])
# ASCII: "CTRL" + 0x00 + 0x03 + 0x00 + 0x03
```

#### 3. KEEP-ALIVE / STATUS
**Sent every 1 second during streaming (149 times):**
```python
# Handle 0x0014
bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x05, 0x00, 0x02])
# ASCII: "CTRL" + 0x00 + 0x05 + 0x00 + 0x02
```

#### 4. NOTIFICATION ENABLE
**Enable BLE notifications (sent first):**
```python
# Handle 0x0017 (CCCD - Client Characteristic Configuration Descriptor)
bytearray([0x01, 0x00])
```

#### 5. OTHER COMMANDS
```python
# CTRL command 0x05, param 0x01 (appears at start)
bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x05, 0x00, 0x01])

# CTRL command 0x05, param 0x03
bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x05, 0x00, 0x03])

# CTRL command 0x05, param 0x04 (sent once during session)
bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x05, 0x00, 0x04])
```

## Command Sequence Analysis

### Session 1 (Short - 0.063s, 2 packets)
**Before streaming:**
1. `Handle 0x0017`: `01 00` (Enable notifications) - 0.371s before
2. `Handle 0x0014`: `CTRL 00 03 00 05` (Start?) - 0.056s before

**After streaming:**
3. `Handle 0x0014`: `CTRL 00 03 00 03` (Stop) - 1.007s after

### Session 2 (Main - 160s, 4008 packets @ 25 pkts/s)
**Before streaming:**
1. `Handle 0x0017`: `01 00` (Enable notifications) - 2.569s before
2. `Handle 0x0014`: `CTRL 00 03 00 05` - 2.254s before
3. `Handle 0x0014`: `CTRL 00 04 00 01` - 2.195s before
4. `Handle 0x0014`: `CTRL 00 03 00 03` - 1.128s before

**During streaming:**
- `Handle 0x0014`: `CTRL 00 05 00 02` sent **every 1 second** (keep-alive)
- One `CTRL 00 05 00 03` at 1145.9s
- One `CTRL 00 05 00 04` at 1155.8s

## Data Format

### EEG Data Notifications
- **Handle**: Unknown (notification characteristic)
- **Packet preview**: `44 41 54 41...` (ASCII: "DATA"...)
- **Rate**: ~25 packets/second
- **Total received**: 4,010 packets over 160 seconds

### Packet Headers
```
Session 1: 44 41 54 41 00 01 00 03 20 00 00 00 54 48 32 31
           D  A  T  A  ??       ??          T  H  2  1

Session 2: 44 41 54 41 00 02 00 03 50 00 00 00 C0 6E FC 00
           D  A  T  A  ??       ??          ??
```

## Recommended Implementation

### Python (Bleak)
```python
WRITE_CHAR_HANDLE = 0x0014  # Control characteristic
NOTIFY_CCCD_HANDLE = 0x0017  # CCCD descriptor

# 1. Enable notifications
await client.write_gatt_descriptor(NOTIFY_CCCD_HANDLE, bytearray([0x01, 0x00]))

# 2. Start streaming
await client.write_gatt_char(WRITE_CHAR_HANDLE, bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x03, 0x00, 0x05]))

# Or try this variant:
await client.write_gatt_char(WRITE_CHAR_HANDLE, bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x04, 0x00, 0x01]))

# 3. Send keep-alive every 1 second (optional, but app does this)
async def keep_alive_loop():
    while streaming:
        await client.write_gatt_char(WRITE_CHAR_HANDLE, bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x05, 0x00, 0x02]))
        await asyncio.sleep(1.0)

# 4. Stop streaming
await client.write_gatt_char(WRITE_CHAR_HANDLE, bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x03, 0x00, 0x03]))
```

### Node.js (Noble)
```javascript
const WRITE_CHAR_HANDLE = '0x0014';
const NOTIFY_CCCD = '0x0017';

// Enable notifications
await writeChar.writeValue(Buffer.from([0x01, 0x00]));

// Start streaming
await writeChar.writeValue(Buffer.from([0x43, 0x54, 0x52, 0x4C, 0x00, 0x03, 0x00, 0x05]));

// Keep-alive (every 1s)
setInterval(() => {
  writeChar.writeValue(Buffer.from([0x43, 0x54, 0x52, 0x4C, 0x00, 0x05, 0x00, 0x02]));
}, 1000);

// Stop streaming
await writeChar.writeValue(Buffer.from([0x43, 0x54, 0x52, 0x4C, 0x00, 0x03, 0x00, 0x03]));
```

## Command Breakdown

| Command | Format | Purpose | When |
|---------|--------|---------|------|
| Enable Notify | `01 00` | Enable BLE notifications on CCCD | First, before anything |
| Start Stream? | `CTRL 00 03 00 05` | Start streaming | Before data starts |
| Alt Start? | `CTRL 00 04 00 01` | Alternative start command | Session 1 only |
| Keep-Alive | `CTRL 00 05 00 02` | Status/heartbeat | Every 1s during stream |
| Stop Stream | `CTRL 00 03 00 03` | Stop streaming | After streaming ends |
| Unknown 1 | `CTRL 00 05 00 01` | Unknown | Occasionally |
| Unknown 2 | `CTRL 00 05 00 03` | Unknown | Once during session |
| Unknown 3 | `CTRL 00 05 00 04` | Unknown | Once during session |

## Next Steps

1. **Test the start command** in your live streaming code
2. **Verify** which command actually triggers streaming (0x03 vs 0x04)
3. **Implement keep-alive** if needed (may not be required)
4. **Test stop command** to cleanly terminate streaming
5. **Decode the "DATA" packets** to extract EEG samples

## Notes

- Commands use **Handle 0x0014** (write characteristic)
- Notifications use **Handle 0x0017** for CCCD
- Data packets start with ASCII `"DATA"`
- Keep-alive might not be mandatory, test without it first
- Session 2 shows stable 25 pkt/s rate over 160 seconds
