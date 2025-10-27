# Manual nRF Connect Testing Guide

Since automated HCI capture is difficult, test these commands manually in nRF Connect:

## Setup
1. Power cycle the headband (off/on)
2. Open nRF Connect
3. Connect to TH21A_F682595DCC5D
4. Find characteristic `8653000c` (the write characteristic)
5. Enable notifications on `8653000b` first
6. Then try writing these commands to `8653000c`:

## Commands to Test (in order)

### Single Bytes
1. `01` (hex)
2. `02` (hex)
3. `03` (hex)
4. `04` (hex)
5. `FF` (hex)

### Two Bytes
6. `01 00` (hex)
7. `00 01` (hex)
8. `02 00` (hex)
9. `00 02` (hex)

### Four Bytes  
10. `01 00 00 00` (hex)
11. `02 00 00 00` (hex)

### Text Commands (use String type in nRF)
12. `START`
13. `STREAM`
14. `ON`

### "DATA" prefix (hex)
15. `44 41 54 41 01` (DATA + 0x01)
16. `44 41 54 41 02` (DATA + 0x02)

## What to Look For
- After writing each command, check if notifications start arriving on `8653000b`
- If data starts flowing, **that's the activation command!**
- Note which command worked

## If Nothing Works
The device might:
1. Auto-stream after first app pairing (persistent state)
2. Require multi-step sequence
3. Need physical button press
4. Activate only when app's encryption/authentication succeeds
