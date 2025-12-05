#!/usr/bin/env python3
"""
Find the next (oldest unprocessed) firmware version to process
"""
import json
import os
import sys
from subprocess import run

def main():
    region = os.environ.get('REGION')
    if not region:
        print("Error: REGION environment variable not set")
        sys.exit(1)
    
    manifest_path = f"firmware_updates/{region}.json"
    
    # Load manifest
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
    except Exception as e:
        print(f"Error loading manifest: {e}")
        sys.exit(0)
    
    versions = manifest.get('versions', [])
    if not versions:
        print("No versions in manifest")
        sys.exit(0)
    
    # Get existing releases
    result = run(['gh', 'release', 'list', '--limit', '1000', '--json', 'tagName'],
                 capture_output=True, text=True)
    
    existing_tags = set()
    if result.returncode == 0 and result.stdout.strip():
        try:
            releases = json.loads(result.stdout)
            existing_tags = {r['tagName'] for r in releases}
            print(f"Found {len(existing_tags)} existing releases for comparison")
        except Exception as e:
            print(f"Warning: Could not parse releases: {e}")
    
    # Find oldest unprocessed version by date
    unprocessed = []
    for version_info in versions:
        tag = f"v{version_info['version']}-{region}"
        if tag not in existing_tags:
            unprocessed.append(version_info)
        else:
            print(f"  ⏭️  Skipping {version_info['version']} (already released as {tag})")
    
    if not unprocessed:
        print(f"✅ All versions already released for {region}")
        sys.exit(0)
    
    # Sort unprocessed by date (oldest first)
    try:
        unprocessed.sort(key=lambda x: x.get('date', '9999-99-99'))
    except Exception as e:
        print(f"⚠️  Warning: Could not sort by date: {e}")
        print("Processing first unprocessed version found")
    
    # Get oldest unprocessed (first after sorting by date)
    next_version = unprocessed[0]
    print(f"📦 Found {len(unprocessed)} unprocessed version(s)")
    print(f"🎯 Will process oldest: {next_version['version']} ({next_version.get('date', 'unknown date')})")
    
    # Select fastest URL by testing all mirrors
    urls = next_version['urls']
    fastest_url = urls[0]
    
    if len(urls) > 1:
        print("Testing mirror speeds (10MB sample)...")
        mirror_speeds = []
        
        for url in urls:
            mirror_name = url.split('/')[2]  # Extract domain
            result = run(['curl', '-L', '--connect-timeout', '5', '--max-time', '10',
                         '--range', '0-10485759', '-s', '-o', '/dev/null', 
                         '-w', '%{speed_download}', url],
                        capture_output=True, text=True)
            try:
                speed = float(result.stdout.strip())
                speed_mbps = (speed / 1024 / 1024)
                mirror_speeds.append((url, speed_mbps, mirror_name))
                print(f"  {mirror_name}: {speed_mbps:.2f} MB/s")
            except:
                print(f"  {mirror_name}: Failed")
                mirror_speeds.append((url, 0, mirror_name))
        
        # Sort by speed (fastest first)
        mirror_speeds.sort(key=lambda x: x[1], reverse=True)
        
        if mirror_speeds[0][1] > 0:
            fastest_url = mirror_speeds[0][0]
            print(f"✅ Selected: {mirror_speeds[0][2]} ({mirror_speeds[0][1]:.2f} MB/s)")
        else:
            print("⚠️  All mirrors failed speed test, using first URL")
            fastest_url = urls[0]
    
    filename = fastest_url.split('/')[-1]
    
    # Output to GitHub Actions
    github_output = os.environ.get('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a') as f:
            f.write(f"VERSION={next_version['version']}\n")
            f.write(f"FILENAME={filename}\n")
            f.write(f"DOWNLOAD_URL={fastest_url}\n")
            f.write(f"HYPEROS_VERSION={next_version.get('hyperos_version', 'Unknown')}\n")
            f.write(f"ANDROID_VERSION={next_version.get('android_version', 'Unknown')}\n")
            f.write(f"RELEASE_DATE={next_version.get('date', 'Unknown')}\n")
            f.write(f"MD5_HASH={next_version.get('md5', 'Unknown')}\n")
            f.write(f"DATA_FOUND=true\n")
    
    print(f"✅ Will process: {next_version['version']}")

if __name__ == '__main__':
    main()
