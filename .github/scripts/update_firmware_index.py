#!/usr/bin/env python3
"""
Script to update README.md with an expandable firmware version index
"""

import os
import re
import json
from datetime import datetime
from subprocess import run, PIPE

def get_all_releases():
    """Fetch all releases from GitHub"""
    result = run(
        ['gh', 'release', 'list', '--limit', '1000', '--json', 'tagName,name,createdAt'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        # If gh fails (e.g., no releases yet), return empty list
        if 'no releases found' in result.stderr.lower() or 'not found' in result.stderr.lower():
            print("ℹ️  No releases found yet in repository")
            return []
        else:
            print(f"❌ gh CLI error: {result.stderr}")
            raise RuntimeError(f"Failed to fetch releases: {result.stderr}")
    
    return json.loads(result.stdout) if result.stdout.strip() else []

def parse_tag(tag):
    """Parse release tag to extract version and region"""
    # Format: vVERSION-region
    match = re.match(r'^v(.+)-(.+)$', tag)
    if match:
        return match.group(1), match.group(2)
    return None, None

def generate_firmware_index(releases):
    """Generate HTML expandable firmware index"""
    
    # Group releases by region
    by_region = {}
    for release in releases:
        version, region = parse_tag(release['tagName'])
        if not version or not region:
            continue
        
        if region not in by_region:
            by_region[region] = []
        
        by_region[region].append({
            'version': version,
            'tag': release['tagName'],
            'url': f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'nicodotgit/degas-fw-dump')}/releases/tag/{release['tagName']}",
            'date': release['createdAt'][:10],  # YYYY-MM-DD
            'name': release['name']
        })
    
    # Sort by version (newest first)
    for region in by_region:
        by_region[region].sort(key=lambda x: x['version'], reverse=True)
    
    # Region names mapping
    region_names = {
        'global': 'Global',
        'eea': 'Europe (EEA)',
        'ru': 'Russia',
        'id': 'Indonesia',
        'tw': 'Taiwan',
        'tr': 'Turkey',
        'global_dc': 'Global DC'
    }
    
    # Generate HTML
    html_parts = ['## 📱 Firmware Version Index\n\n']
    html_parts.append('Browse all available firmware versions by region. Click to expand each region.\n\n')
    
    for region in sorted(by_region.keys()):
        region_name = region_names.get(region, region.upper())
        versions = by_region[region]
        
        html_parts.append(f'<details>\n')
        html_parts.append(f'<summary><b>{region_name}</b> ({len(versions)} versions available)</summary>\n\n')
        html_parts.append('| Version | Release Date | Download |\n')
        html_parts.append('|---------|--------------|----------|\n')
        
        for v in versions:
            html_parts.append(f"| `{v['version']}` | {v['date']} | [📥 Download]({v['url']}) |\n")
        
        html_parts.append('\n</details>\n\n')
    
    return ''.join(html_parts)

def update_readme(index_content):
    """Update README.md with the firmware index"""
    readme_path = 'README.md'
    
    with open(readme_path, 'r') as f:
        content = f.read()
    
    # Find where to insert the index (before "About This Repository" section)
    marker_start = '<!-- FIRMWARE_INDEX_START -->'
    marker_end = '<!-- FIRMWARE_INDEX_END -->'
    
    if marker_start in content and marker_end in content:
        # Replace existing index
        pattern = f'{re.escape(marker_start)}.*?{re.escape(marker_end)}'
        new_content = re.sub(
            pattern,
            f'{marker_start}\n{index_content}{marker_end}',
            content,
            flags=re.DOTALL
        )
    else:
        # Insert before "About This Repository"
        about_section = '\n## About This Repository'
        if about_section in content:
            new_content = content.replace(
                about_section,
                f'\n{marker_start}\n{index_content}{marker_end}\n{about_section}'
            )
        else:
            # Append at the end
            new_content = content + f'\n\n{marker_start}\n{index_content}{marker_end}\n'
    
    with open(readme_path, 'w') as f:
        f.write(new_content)
    
    print("✅ README.md updated successfully!")

def main():
    try:
        print("Fetching releases from GitHub...")
        releases = get_all_releases()
        print(f"Found {len(releases)} releases")
        
        if len(releases) == 0:
            print("ℹ️  No releases found. Skipping README update.")
            print("   The index will be populated after the first release is created.")
            return
        
        print("Generating firmware index...")
        index_content = generate_firmware_index(releases)
        
        print("Updating README.md...")
        update_readme(index_content)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise

if __name__ == '__main__':
    main()
