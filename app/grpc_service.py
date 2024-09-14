import grpc
from concurrent import futures
import metadata_service_pb2
import metadata_service_pb2_grpc
from app.direct_api import DirectAPI
import logging
import json

class MetadataServicer(metadata_service_pb2_grpc.MetadataServiceServicer):
    def GetMovieMetadata(self, request, context):
        logging.info(f"Received request for movie metadata: {request.imdb_id}")
        metadata, source = DirectAPI.get_movie_metadata(request.imdb_id)
        logging.info(f"Retrieved metadata: {metadata}, source: {source}")
        
        # Convert all values in metadata to strings
        string_metadata = {}
        for k, v in metadata.items():
            if isinstance(v, (list, dict)):
                string_metadata[k] = json.dumps(v)
            else:
                string_metadata[k] = str(v)
        
        return metadata_service_pb2.MetadataResponse(
            metadata=string_metadata,
            source=source
        )

    def GetMovieReleaseDates(self, request, context):
        release_dates, source = DirectAPI.get_movie_release_dates(request.imdb_id)
        if release_dates is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Release dates not found for IMDB ID: {request.imdb_id}")
            return metadata_service_pb2.ReleaseDatesResponse()
        
        return metadata_service_pb2.ReleaseDatesResponse(
            release_dates=json.dumps(release_dates),
            source=source
        )

    def GetEpisodeMetadata(self, request, context):
        logging.info(f"Received request for episode metadata: {request.imdb_id}")
        try:
            metadata, source = DirectAPI.get_episode_metadata(request.imdb_id)
            logging.info(f"Retrieved metadata: {metadata}, source: {source}")
            
            if metadata is None:
                return metadata_service_pb2.MetadataResponse(
                    metadata={},
                    source="No data available"
                )
            
            # Convert all values in metadata to strings
            string_metadata = {}
            for k, v in metadata.items():
                if isinstance(v, (dict, list)):
                    string_metadata[k] = json.dumps(v)
                else:
                    string_metadata[k] = str(v)
            
            return metadata_service_pb2.MetadataResponse(
                metadata=string_metadata,
                source=source
            )
        except Exception as e:
            logging.exception("Error in GetEpisodeMetadata")
            context.abort(grpc.StatusCode.INTERNAL, f"Internal error: {str(e)}")

    def GetShowMetadata(self, request, context):
        metadata, source = DirectAPI.get_show_metadata(request.imdb_id)
        if metadata is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Show metadata not found for IMDb ID: {request.imdb_id}")
            return metadata_service_pb2.MetadataResponse()
        
        processed_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, (dict, list)):
                processed_metadata[key] = json.dumps(value)
            elif not isinstance(value, str):
                processed_metadata[key] = json.dumps(value)
            else:
                processed_metadata[key] = value
        return metadata_service_pb2.MetadataResponse(metadata=processed_metadata, source=source)

    def GetShowSeasons(self, request, context):
        seasons_data, source = DirectAPI.get_show_seasons(request.imdb_id)
        if seasons_data is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Seasons not found for IMDB ID: {request.imdb_id}")
            return metadata_service_pb2.ShowSeasonsResponse()

        seasons_response = {}
        for season_number, season_info in seasons_data.items():
            episodes = {}
            for episode_number, episode_info in season_info['episodes'].items():
                episodes[episode_number] = metadata_service_pb2.EpisodeInfo(
                    first_aired=episode_info.get('first_aired', ''),
                    runtime=episode_info.get('runtime', 0),
                    title=episode_info.get('title', '')
                )
            seasons_response[str(season_number)] = metadata_service_pb2.SeasonInfo(
                episode_count=season_info['episode_count'],
                episodes=episodes
            )

        return metadata_service_pb2.ShowSeasonsResponse(seasons=seasons_response, source=source)

    def TMDbToIMDb(self, request, context):
        imdb_id = DirectAPI.tmdb_to_imdb(request.tmdb_id)
        return metadata_service_pb2.IMDbResponse(imdb_id=imdb_id)

    def BatchGetMetadata(self, request, context):
        results = DirectAPI.batch_get_metadata(request.imdb_ids)
        batch_response = {}
        for imdb_id, metadata in results.items():
            string_metadata = {}
            for k, v in metadata.items():
                if isinstance(v, (dict, list)):
                    string_metadata[k] = json.dumps(v)
                else:
                    string_metadata[k] = str(v)
            batch_response[imdb_id] = metadata_service_pb2.MetadataResponse(metadata=string_metadata, source='')
        
        return metadata_service_pb2.BatchMetadataResponse(results=batch_response)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    metadata_service_pb2_grpc.add_MetadataServiceServicer_to_server(MetadataServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()