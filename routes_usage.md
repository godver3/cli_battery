# Metadata gRPC Service Guide for LLMs

This guide outlines how to use the Metadata gRPC Service to retrieve information about movies, TV shows, and episodes. As an LLM, you can use this information to enhance your responses when discussing or analyzing media content.

## Available Methods

### 1. GetMovieMetadata(imdb_id: str) -> MetadataResponse

Use this to fetch detailed information about a movie.

Example usage:
```python
movie_data = stub.GetMovieMetadata(metadata_service_pb2.IMDbRequest(imdb_id="tt0111161")).metadata
title = movie_data['title']
year = movie_data['year']
```

### 2. GetMovieReleaseDates(imdb_id: str) -> ReleaseDatesResponse

Retrieve release dates for a movie across different countries.

Example usage:
```python
release_dates = json.loads(stub.GetMovieReleaseDates(metadata_service_pb2.IMDbRequest(imdb_id="tt0111161")).release_dates)
us_release = release_dates.get('US', 'Unknown')
```

### 3. GetEpisodeMetadata(imdb_id: str) -> MetadataResponse

Fetch metadata for a specific TV episode.

Example usage:
```python
episode_data = stub.GetEpisodeMetadata(metadata_service_pb2.IMDbRequest(imdb_id="tt0582910")).metadata
episode_title = episode_data['title']
air_date = episode_data['air_date']
```

### 4. GetShowMetadata(imdb_id: str) -> MetadataResponse

Retrieve overall information about a TV series.

Example usage:
```python
show_data = stub.GetShowMetadata(metadata_service_pb2.IMDbRequest(imdb_id="tt0944947")).metadata
show_title = show_data['title']
num_seasons = show_data['number_of_seasons']
```

### 5. GetShowSeasons(imdb_id: str) -> ShowSeasonsResponse

Get detailed information about all seasons and episodes of a TV show.

Example usage:
```python
seasons_data = stub.GetShowSeasons(metadata_service_pb2.IMDbRequest(imdb_id="tt0944947")).seasons
for season_num, season_info in seasons_data.items():
    episode_count = season_info.episode_count
    first_episode_title = season_info.episodes['1'].title
```

### 6. TMDbToIMDb(tmdb_id: str) -> IMDbResponse

Convert a TMDb ID to its corresponding IMDb ID.

Example usage:
```python
imdb_id = stub.TMDbToIMDb(metadata_service_pb2.TMDbRequest(tmdb_id="550")).imdb_id
```

### 7. BatchGetMetadata(imdb_ids: List[str]) -> BatchMetadataResponse

Efficiently retrieve metadata for multiple items in a single request.

Example usage:
```python
batch_results = stub.BatchGetMetadata(metadata_service_pb2.BatchMetadataRequest(imdb_ids=["tt0111161", "tt0068646"])).results
for imdb_id, metadata in batch_results.items():
    title = metadata.metadata['title']
    year = metadata.metadata['year']
```

## Best Practices for LLMs

1. **Context Enhancement**: Use this service to add factual details about movies or TV shows mentioned in user queries.

2. **Temporal Awareness**: Utilize release dates to provide time-relevant information or comparisons.

3. **Cross-referencing**: When discussing related media, use the batch request to efficiently gather information about multiple titles.

4. **Fact Checking**: Verify user-provided information about movies or shows against the metadata from this service.

5. **Detailed Analysis**: For TV shows, use the season and episode data to provide in-depth commentary on series structure or evolution.

6. **Error Handling**: Always be prepared for the possibility that metadata might not be available for a given ID.

7. **Source Attribution**: When using this data in responses, you can mention that the information comes from a reliable metadata service.

By leveraging this gRPC service, you can enhance your responses with accurate and detailed information about various media, providing users with rich, informative content in discussions about movies and TV shows.