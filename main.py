#!/usr/bin/env python3
"""
Tailscale Device Status Monitor with Apprise Notifications
"""

import os
import time
import json
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import apprise

# Load environment variables
load_dotenv()

TAILSCALE_API_KEY = os.getenv('TAILSCALE_API_KEY')
TAILSCALE_TAILNET = os.getenv('TAILSCALE_TAILNET')
APPRISE_URLS = os.getenv('APPRISE_URLS', '').split(',')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))  # seconds
STATE_FILE = os.getenv('STATE_FILE', '/data/device_state.json')
ONLINE_THRESHOLD_SECONDS = int(os.getenv('ONLINE_THRESHOLD_SECONDS', '60'))  # Consider online if seen within X seconds

def load_previous_state():
    """Load the previous device state from file"""
    state_path = Path(STATE_FILE)
    if state_path.exists():
        try:
            with open(state_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading state file: {e}")
    return {}

def save_current_state(state):
    """Save the current device state to file"""
    state_path = Path(STATE_FILE)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(state_path, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Error saving state file: {e}")

def get_tailscale_devices():
    """Fetch current device status from Tailscale API"""
    url = f"https://api.tailscale.com/api/v2/tailnet/{TAILSCALE_TAILNET}/devices"
    headers = {
        'Authorization': f'Bearer {TAILSCALE_API_KEY}'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Debug: Print raw device data
        if os.getenv('DEBUG') == 'true':
            print("\n=== DEBUG: Raw API Response ===")
            for device in data.get('devices', [])[:3]:  # Print first 3 devices as sample
                print(f"Device: {device.get('name', device.get('hostname'))}")
                print(f"  - id: {device.get('id')}")
                print(f"  - online: {device.get('online')}")
                print(f"  - lastSeen: {device.get('lastSeen')}")
                print(f"  - expires: {device.get('expires')}")
            print("================================\n")
        
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Tailscale devices: {e}")
        return None

def is_device_online(device):
    """Determine if a device is actually online based on lastSeen timestamp"""
    last_seen = device.get('lastSeen')
    if not last_seen:
        return False
    
    try:
        # Parse the lastSeen timestamp
        last_seen_time = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        # Calculate time difference
        time_diff = now - last_seen_time
        
        # Consider online if seen within threshold
        is_online = time_diff < timedelta(seconds=ONLINE_THRESHOLD_SECONDS)
        
        if os.getenv('DEBUG') == 'true':
            print(f"  {device.get('name')}: last seen {time_diff.total_seconds():.1f}s ago -> {'ONLINE' if is_online else 'OFFLINE'}")
        
        return is_online
    except Exception as e:
        print(f"Error parsing lastSeen for {device.get('name')}: {e}")
        return False

def send_notification(title, body):
    """Send notification via Apprise"""
    apobj = apprise.Apprise()
    
    # Add all configured notification services
    for url in APPRISE_URLS:
        url = url.strip()
        if url:
            apobj.add(url)
    
    if len(apobj) == 0:
        print("No Apprise URLs configured!")
        return
    
    try:
        apobj.notify(
            title=title,
            body=body,
        )
        print(f"✓ Notification sent: {title}")
        if os.getenv('DEBUG') == 'true':
            print(f"  Body preview: {body[:100]}...")
    except Exception as e:
        print(f"✗ Error sending notification: {e}")

def send_initial_status():
    """Send initial status report of all devices"""
    print("Fetching initial device status...")
    data = get_tailscale_devices()
    if not data:
        print("Failed to fetch initial device status")
        return
    
    online_devices = []
    offline_devices = []
    
    if os.getenv('DEBUG') == 'true':
        print("\n=== Checking device online status ===")
    
    for device in data.get('devices', []):
        device_name = device.get('name') or device.get('hostname', 'Unknown')
        is_online = is_device_online(device)
        
        if is_online:
            online_devices.append(device_name)
        else:
            offline_devices.append(device_name)
    
    if os.getenv('DEBUG') == 'true':
        print("=====================================\n")
    
    # Build status message
    total_devices = len(online_devices) + len(offline_devices)
    
    title = "📊 Tailscale Initial Status Report"
    body_parts = [
        f"Total Devices: {total_devices}",
        f"",
        f"🟢 Online ({len(online_devices)}):",
    ]
    
    if online_devices:
        for device in sorted(online_devices):
            body_parts.append(f"  • {device}")
    else:
        body_parts.append("  (none)")
    
    body_parts.append("")
    body_parts.append(f"🔴 Offline ({len(offline_devices)}):")
    
    if offline_devices:
        for device in sorted(offline_devices):
            body_parts.append(f"  • {device}")
    else:
        body_parts.append("  (none)")
    
    body_parts.append("")
    body_parts.append(f"🔍 Now monitoring for changes (checking every {CHECK_INTERVAL}s)...")
    
    body = "\n".join(body_parts)
    
    send_notification(title, body)
    print(f"Initial status: {len(online_devices)} online, {len(offline_devices)} offline")
    
    # Save initial state
    current_devices = {}
    for device in data.get('devices', []):
        device_id = device['id']
        current_devices[device_id] = {
            'name': device.get('name') or device.get('hostname', 'Unknown'),
            'online': is_device_online(device),
            'lastSeen': device.get('lastSeen', ''),
        }
    save_current_state(current_devices)

def check_devices():
    """Check for device status changes and send notifications"""
    data = get_tailscale_devices()
    if not data:
        return
    
    current_devices = {}
    
    # Build current state map
    for device in data.get('devices', []):
        device_id = device['id']
        current_devices[device_id] = {
            'name': device.get('name') or device.get('hostname', 'Unknown'),
            'online': is_device_online(device),
            'lastSeen': device.get('lastSeen', ''),
        }
    
    # Load previous state
    previous_state = load_previous_state()
    
    # Check for changes
    changes = []
    
    # Check for new devices or status changes
    for device_id, device in current_devices.items():
        prev = previous_state.get(device_id)
        
        if not prev:
            # New device detected
            changes.append({
                'device': device['name'],
                'status': 'online' if device['online'] else 'offline',
                'type': 'new'
            })
        elif prev['online'] != device['online']:
            # Status changed
            changes.append({
                'device': device['name'],
                'status': 'online' if device['online'] else 'offline',
                'type': 'changed'
            })
    
    # Check for removed devices
    for device_id, device in previous_state.items():
        if device_id not in current_devices:
            changes.append({
                'device': device['name'],
                'status': 'removed',
                'type': 'removed'
            })
    
    # Send notifications for changes
    for change in changes:
        if change['type'] == 'new':
            emoji = '🟢' if change['status'] == 'online' else '🔴'
            title = f"🆕 New Tailscale Device"
            body = f"{change['device']} is {change['status']}"
        elif change['type'] == 'removed':
            title = "🗑️ Tailscale Device Removed"
            body = f"{change['device']} was removed from the network"
        else:
            emoji = '🟢' if change['status'] == 'online' else '🔴'
            title = f"{emoji} Device {change['status'].title()}"
            body = f"{change['device']} is now {change['status']}"
        
        send_notification(title, body)
    
    # Save current state
    save_current_state(current_devices)
    
    if changes:
        print(f"✓ Processed {len(changes)} device change(s)")
    else:
        print(f"✓ No changes detected (checked {len(current_devices)} devices)")

def main():
    """Main monitoring loop"""
    print("=" * 50)
    print("Tailscale Device Monitor Starting...")
    print("=" * 50)
    print(f"Monitoring tailnet: {TAILSCALE_TAILNET}")
    print(f"Check interval: {CHECK_INTERVAL} seconds")
    print(f"Online threshold: {ONLINE_THRESHOLD_SECONDS} seconds")
    print(f"Apprise URLs configured: {len([u for u in APPRISE_URLS if u.strip()])}")
    print(f"Debug mode: {os.getenv('DEBUG', 'false')}")
    print("=" * 50)
    
    if not TAILSCALE_API_KEY or not TAILSCALE_TAILNET:
        print("ERROR: TAILSCALE_API_KEY and TAILSCALE_TAILNET must be set!")
        return
    
    # Send initial status report
    send_initial_status()
    
    # Wait before starting monitoring loop
    print(f"\nWaiting {CHECK_INTERVAL} seconds before first check...")
    time.sleep(CHECK_INTERVAL)
    
    print("\n🔍 Starting monitoring loop...\n")
    
    while True:
        try:
            check_devices()
        except Exception as e:
            print(f"✗ Error in monitoring loop: {e}")
            send_notification("⚠️ Tailscale Monitor Error", str(e))
        
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
