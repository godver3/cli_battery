#!/bin/bash

PLEX_TOKEN="2rJ8yc5bgSYFgeRxyU1S"
LIBRARY_ID="30"

# Function to fetch data from Plex
fetch_plex_data() {
    curl -s -X GET "$1" \
        -H "X-Plex-Token: $PLEX_TOKEN" \
        -H 'Accept: application/json'
}

# Get one TV show
tv_show=$(fetch_plex_data "http://localhost:32400/library/sections/$LIBRARY_ID/all?type=2&includeGuids=1&limit=1")

# Extract the rating key of the show
show_key=$(echo "$tv_show" | jq -r '.MediaContainer.Metadata[0].ratingKey')

# Fetch all details for this show, including seasons and episodes
show_details=$(fetch_plex_data "http://localhost:32400/library/metadata/$show_key?includeGuids=1&includeChildren=1")

# Process and output the details, including file paths
echo "$show_details" | jq '
.MediaContainer.Metadata[0] | {
  title,
  year,
  guid,
  seasons: .Children.Metadata | map({
    seasonNumber: .index,
    episodes: .Children.Metadata | map({
      episodeNumber: .index,
      title,
      guid,
      filePath: .Media[0].Part[0].file
    })
  })
}'
