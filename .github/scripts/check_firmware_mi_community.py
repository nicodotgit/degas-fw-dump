#!/usr/bin/env python3
"""
Xiaomi Firmware Checker - Mi Community API Method
Gets FASTBOOT (.tgz) packages instead of OTA (.zip)
Based on XiaomiFirmwareUpdater's approach
"""

import json
import os
import sys
import re
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Device information
DEVICE_CODENAME = "degas"
DEVICE_NAME = "Xiaomi 14T"
DEVICE_MI_ID = "1903070"

# Region mapping (separate manifest per region)
REGIONS = {
    'global': {'code': 'global', 'name': 'Global'},
    'eea': {'code': 'eea', 'name': 'Europe'},
    'ru': {'code': 'ru', 'name': 'Russia'},
    'id': {'code': 'id', 'name': 'Indonesia'},
    'tw': {'code': 'tw', 'name': 'Taiwan'},
    'tr': {'code': 'tr', 'name': 'Turkey'}
}

# API endpoints
MI_COMMUNITY_API = "https://sgp-api.buy.mi.com/bbs/api/global"
FASTBOOT_API = "https://update.intl.miui.com/updates/v1/fullromdownload.php"
CDN_BASE = "https://bkt-sgp-miui-ota-update-alisgp.oss-ap-southeast-1.aliyuncs.com"

# Fastboot filename pattern
# Example: degas_eea_global_images_OS2.0.207.0.VNEEUXM_20251129.0000.00_16.0_eea_5afdce8b44.tgz
FASTBOOT_PATTERN = re.compile(
    r'(?P<codename>\w+)_(?P<region>\w+)(?:_global)?_images_(?P<version>[\w\d.]+)_(?P<date>\d+\.\d+\.\d+)_(?P<android>[\d.]+)_(?P<region_code>\w+)_(?P<md5_part>\w+)\.tgz'
)


def find_device_id(device_name=DEVICE_NAME, known_id=DEVICE_MI_ID):
    """Find device ID from Mi Community API"""
    # Use known ID if available
    if known_id:
        return known_id, device_name
    
    try:
        url = f"{MI_COMMUNITY_API}/phone/getphonelist"
        headers = {
            "Accept": "application/json",
            "Origin": "https://new.c.mi.com",
            "Referer": "https://new.c.mi.com/",
            "User-Agent": "Mozilla/5.0"
        }
        
        print(f"🔍 Searching for device: {device_name}")
        req = Request(url, headers=headers)
        
        with urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            if data.get('code') == 0 and data.get('data'):
                devices = data['data']['phone_data']['phone_list']
                
                # Search for matching device
                for device in devices:
                    if device_name.lower() in device['name'].lower() or 'degas' in device['name'].lower():
                        print(f"  ✅ Found: {device['name']} (ID: {device['id']})")
                        return device['id'], device['name']
                
                print(f"  ❌ Device not found, listing available:")
                for device in devices[:10]:
                    print(f"     - {device['name']} (ID: {device['id']})")
                return None, None
            else:
                print(f"  ❌ API Error: {data}")
                return None, None
                
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None, None


def get_all_fastboot_packages():
    """Get fastboot packages for all regions from Mi Community API"""
    try:
        url = f"{MI_COMMUNITY_API}/phone/getlinepackagelist"
        headers = {
            "Accept": "application/json",
            "Origin": "https://new.c.mi.com",
            "Referer": "https://new.c.mi.com/",
            "User-Agent": "Mozilla/5.0"
        }
        
        print("  Querying fastboot package list...")
        req = Request(url, headers=headers)
        
        with urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            if data.get('code') != 0 or not data.get('data'):
                print("    ❌ API error")
                return []
            
            packages = []
            
            # Filter for degas (Xiaomi 14T) fastboot packages
            for item in data['data']:
                key = item.get('key', '')
                
                # Match degas devices only (not rothko which is 14T Pro)
                if not key.startswith('degas_'):
                    continue
                
                # Parse key format: degas_{region}_global_{region}_F
                parts = key.split('_')
                if len(parts) < 3:
                    continue
                
                region_key = parts[1]  # e.g., 'global', 'eea', 'ru', etc.
                
                # Map region keys
                region_map = {
                    'global': 'global',
                    'eea': 'eea',
                    'ru': 'ru',
                    'id': 'id',
                    'tw': 'tw',
                    'tr': 'tr',
                    'dc': 'global_dc'
                }
                
                mapped_region = region_map.get(region_key)
                if not mapped_region or mapped_region not in REGIONS:
                    continue
                
                package_url = item.get('package_url', '')
                if not package_url:
                    continue
                
                filename = package_url.split('/')[-1].split('?')[0]
                
                print(f"    ✅ {REGIONS[mapped_region]['name']}: {filename[:70]}...")
                
                packages.append({
                    'region': mapped_region,
                    'url': package_url,
                    'filename': filename
                })
            
            return packages
            
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return []


def parse_fastboot_filename(filename):
    """Extract metadata from fastboot .tgz filename"""
    match = FASTBOOT_PATTERN.search(filename)
    if match:
        groups = match.groupdict()
        return {
            'codename': groups['codename'],
            'region': groups['region'],
            'version': groups['version'],
            'android': groups['android'],
            'date': groups['date'],
            'md5_part': groups['md5_part']
        }
    return None


def update_manifest(region, version_info):
    """Add version to region-specific manifest if not exists"""
    os.makedirs("firmware_updates", exist_ok=True)
    manifest_path = f"firmware_updates/{region}.json"
    
    # Load or create manifest
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
    else:
        manifest = {
            'region': region,
            'versions': []
        }
    
    # Check if version already exists
    existing_versions = [v['version'] for v in manifest['versions']]
    if version_info['version'] in existing_versions:
        return False
    
    # Add new version
    manifest['versions'].append(version_info)
    
    # Sort by date (newest first)
    manifest['versions'].sort(key=lambda x: x.get('date', '0000-00-00'), reverse=True)
    
    # Save
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    return True


def main():
    regions_to_check = sys.argv[1:] if len(sys.argv) > 1 else REGIONS.keys()
    
    print("🔍 Xiaomi Firmware Checker (Fastboot Packages)")
    print("=" * 60)
    print(f"📱 Device: {DEVICE_NAME} ({DEVICE_CODENAME})\n")
    
    # Get fastboot packages for all regions
    packages = get_all_fastboot_packages()
    
    if not packages:
        print("\n❌ No fastboot packages found")
        print("\nAlternative: Use manual_manifest_creator.py to add firmware manually")
        return
    
    print(f"\n✅ Found {len(packages)} fastboot packages")
    
    # Process each package
    updates_added = 0
    for package in packages:
        region = package['region']
        filename = package['filename']
        url = package['url']
        
        # Skip if not in requested regions
        if region not in regions_to_check:
            continue
        
        # Parse filename
        info = parse_fastboot_filename(filename)
        if not info:
            print(f"  ⚠️  Could not parse: {filename}")
            continue
        
        # Extract HyperOS version
        hyperos_version = "Unknown"
        if info['version'].startswith('OS1.'):
            hyperos_version = "1.0"
        elif info['version'].startswith('OS2.'):
            hyperos_version = "2.0"
        elif info['version'].startswith('V'):
            hyperos_version = "MIUI"
        
        # Generate mirror URLs for fastboot package
        version = info['version']
        mirror_urls = [
            f"https://bn.d.miui.com/{version}/{filename}",
            f"https://bigota.d.miui.com/{version}/{filename}",
            f"https://hugeota.d.miui.com/{version}/{filename}",
            url  # Original URL
        ]
        
        # Build version info (NO changelog field)
        # Convert date from 20251117.0000.00 to 2025-11-17
        date_str = info['date'].split('.')[0]  # Get 20251117
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"  # 2025-11-17
        
        version_info = {
            'version': version,
            'date': formatted_date,
            'hyperos_version': hyperos_version,
            'android_version': info['android'],
            'md5': '',  # Will be calculated after download
            'urls': mirror_urls
        }
        
        # Update region-specific manifest
        if update_manifest(region, version_info):
            print(f"  ✅ {REGIONS[region]['name']}: {version}")
            updates_added += 1
        else:
            print(f"  ⏭️  {REGIONS[region]['name']}: {version} (exists)")
    
    print(f"\n✅ Added {updates_added} new firmware versions to region-specific manifests")
    
    if updates_added > 0:
        print("\nNext: git add firmware_updates/ && git commit -m 'Update manifests' && git push")


if __name__ == '__main__':
    main()
