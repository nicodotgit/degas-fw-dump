#!/usr/bin/env python3
"""
Manual Firmware Manifest Creator
Add firmware versions manually to region-specific manifests
"""

import json
import os
import sys
import re

DEVICE_CODENAME = "degas"

REGIONS = {
    'global': 'Global',
    'eea': 'Europe',
    'ru': 'Russia',
    'id': 'Indonesia',
    'tw': 'Taiwan',
    'tr': 'Turkey',
    'global_dc': 'Global DC'
}

TEMPLATE = {
    "region": "",
    "versions": []
}

VERSION_TEMPLATE = {
    "version": "",
    "date": "",
    "hyperos_version": "",
    "android_version": "",
    "md5": "",
    "urls": []
}

def generate_mirror_urls(version, filename):
    """Generate mirror URLs for a fastboot package"""
    mirrors = [
        f"https://bn.d.miui.com/{version}/{filename}",
        f"https://bigota.d.miui.com/{version}/{filename}",
        f"https://hugeota.d.miui.com/{version}/{filename}",
        f"https://ultimateota.d.miui.com/{version}/{filename}"
    ]
    return mirrors


def auto_generate_filename(version, region, date_str, android_ver):
    """Auto-generate fastboot filename from version info"""
    # Pattern: degas_{region}_global_images_{VERSION}_{DATE}_15.0_{region}_xxxxx.tgz
    region_suffix = f"{region}_global" if region != 'global' else 'global'
    
    # Convert date YYYY-MM-DD to YYYYMMDD.0000.00
    date_compact = date_str.replace('-', '') + '.0000.00'
    
    # Generate placeholder MD5 (will be calculated during download)
    md5_placeholder = "xxxxxxxxxxxx"
    
    filename = f"{DEVICE_CODENAME}_{region_suffix}_images_{version}_{date_compact}_{android_ver}_{region}_{md5_placeholder}.tgz"
    return filename


def create_manifest(region):
    """Interactively create a manifest"""
    
    if region not in REGIONS:
        print(f"❌ Invalid region: {region}")
        print(f"Available regions: {', '.join(REGIONS.keys())}")
        return
    
    print(f"\n📝 Adding firmware for: {REGIONS[region]} ({region})")
    print("=" * 60)
    
    os.makedirs("firmware_updates", exist_ok=True)
    manifest_path = f"firmware_updates/{region}.json"
    
    # Load existing or create new
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        print(f"📦 Loaded existing manifest with {len(manifest['versions'])} version(s)")
    else:
        manifest = TEMPLATE.copy()
        manifest['region'] = region
        print("📦 Creating new manifest")
    
    print("\n💡 Tips:")
    print("  • Version format: OS2.0.206.0.VNEMIXM")
    print("  • Date format: YYYY-MM-DD (e.g., 2025-11-13)")
    print("  • Android version: 14.0, 15.0, 16.0, etc.")
    print("  • HyperOS version: 1.0, 2.0, etc.")
    print("  • MD5 will be calculated automatically during download")
    print("  • URLs will be auto-generated for all mirrors")
    print("\nPress Ctrl+C to finish and save\n")
    
    try:
        while True:
            version_info = VERSION_TEMPLATE.copy()
            
            print("\n" + "─" * 60)
            print("➕ New Version")
            print("─" * 60)
            
            version_info['version'] = input("Version: ").strip()
            if not version_info['version']:
                break
            
            # Check if version already exists
            existing = [v['version'] for v in manifest['versions']]
            if version_info['version'] in existing:
                print(f"⚠️  Version {version_info['version']} already exists!")
                continue
            
            version_info['date'] = input("Date (YYYY-MM-DD): ").strip()
            version_info['android_version'] = input("Android version (e.g., 15.0): ").strip()
            version_info['hyperos_version'] = input("HyperOS version (e.g., 2.0): ").strip()
            
            # Auto-generate filename and URLs
            filename = auto_generate_filename(
                version_info['version'],
                region,
                version_info['date'],
                version_info['android_version']
            )
            
            print(f"\n🔗 Generated filename:")
            print(f"   {filename}")
            
            use_custom = input("\nUse custom filename/URLs? (y/N): ").strip().lower()
            
            if use_custom == 'y':
                print("\nEnter download URLs (one per line, empty line to finish):")
                urls = []
                while True:
                    url = input("  URL: ").strip()
                    if not url:
                        break
                    urls.append(url)
                version_info['urls'] = urls
            else:
                # Auto-generate mirror URLs
                version_info['urls'] = generate_mirror_urls(version_info['version'], filename)
                print(f"✅ Auto-generated {len(version_info['urls'])} mirror URLs")
            
            version_info['md5'] = ""  # Will be filled during download
            
            manifest['versions'].append(version_info)
            print(f"\n✅ Added {version_info['version']}")
            
            more = input("\nAdd another version? (y/N): ").strip().lower()
            if more != 'y':
                break
                
    except KeyboardInterrupt:
        print("\n\n⏸️  Interrupted")
    
    # Sort versions by date (newest first for easier viewing, workflow processes oldest)
    try:
        manifest['versions'].sort(key=lambda x: x.get('date', '0000-00-00'), reverse=True)
        print("\n✅ Sorted versions by date (newest first)")
    except Exception as e:
        print(f"\n⚠️  Warning: Could not sort by date: {e}")
    
    # Save
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n✅ Saved {len(manifest['versions'])} version(s) to {manifest_path}")
    print("\n📋 Next steps:")
    print("  1. Review: cat firmware_updates/{}.json".format(region))
    print("  2. Commit: git add firmware_updates/ && git commit -m 'Add {} firmware versions'".format(region))
    print("  3. Push: git push")
    print("\n💡 The workflow will automatically:")
    print("  • Update manifests with latest versions from Xiaomi")
    print("  • Process oldest unprocessed version")
    print("  • Calculate MD5 and update manifest")
    print("  • Create GitHub release")

def main():
    if len(sys.argv) < 2:
        print("🛠️  Manual Firmware Manifest Creator")
        print("=" * 60)
        print("\nUsage: python3 manual_manifest_creator.py <region>")
        print("\nAvailable regions:")
        for code, name in REGIONS.items():
            print(f"  • {code:12} - {name}")
        print("\nExample:")
        print("  python3 scripts/manual_manifest_creator.py global")
        sys.exit(1)
    
    region = sys.argv[1]
    create_manifest(region)

if __name__ == '__main__':
    main()
