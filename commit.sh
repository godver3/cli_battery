#!/bin/bash

# Function to increment version
increment_version() {
    local version=$1
    IFS='.' read -ra ver_parts <<< "$version"
    
    ver_parts[2]=$((ver_parts[2] + 1))
    
    echo "${ver_parts[0]}.${ver_parts[1]}.${ver_parts[2]}"
}

# Check if commit message is provided
if [ $# -lt 1 ]; then
    echo "Error: Commit message is required."
    echo "Usage: $0 <commit_message>"
    exit 1
fi

commit_message="$1"

# Read current version
version=$(cat version.txt)

# Increment version
new_version=$(increment_version "$version")

# Update version file
echo "$new_version" > version.txt

# Git commands
git add -A
git commit -m "[$new_version] $commit_message"
git push

echo "Version updated to $new_version and changes pushed to remote repository."
