#!/usr/bin/env python3
"""
Update manifest with MD5 hash after firmware download
"""
import json
import os
import sys

def main():
    region = os.environ.get('REGION')
    version = os.environ.get('VERSION')
    md5 = os.environ.get('MD5')
    
    if not all([region, version, md5]):
        print("Error: REGION, VERSION, and MD5 environment variables must be set")
        sys.exit(1)
    
    manifest_path = f"firmware_updates/{region}.json"
    
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
    except Exception as e:
        print(f"Error loading manifest: {e}")
        sys.exit(1)
    
    # Find and update version with MD5
    found = False
    for v in manifest['versions']:
        if v['version'] == version:
            v['md5'] = md5
            found = True
            break
    
    if not found:
        print(f"Warning: Version {version} not found in manifest")
        sys.exit(1)
    
    # Save updated manifest
    try:
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        print(f"✅ Updated manifest with MD5: {md5}")
    except Exception as e:
        print(f"Error saving manifest: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
