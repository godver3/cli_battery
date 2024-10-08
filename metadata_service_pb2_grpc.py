# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings

import metadata_service_pb2 as metadata__service__pb2

GRPC_GENERATED_VERSION = '1.66.1'
GRPC_VERSION = grpc.__version__
_version_not_supported = False

try:
    from grpc._utilities import first_version_is_lower
    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True

if _version_not_supported:
    raise RuntimeError(
        f'The grpc package installed is at version {GRPC_VERSION},'
        + f' but the generated code in metadata_service_pb2_grpc.py depends on'
        + f' grpcio>={GRPC_GENERATED_VERSION}.'
        + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}'
        + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.'
    )


class MetadataServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.GetMovieReleaseDates = channel.unary_unary(
                '/metadata.MetadataService/GetMovieReleaseDates',
                request_serializer=metadata__service__pb2.IMDbRequest.SerializeToString,
                response_deserializer=metadata__service__pb2.ReleaseDatesResponse.FromString,
                _registered_method=True)
        self.GetMovieMetadata = channel.unary_unary(
                '/metadata.MetadataService/GetMovieMetadata',
                request_serializer=metadata__service__pb2.IMDbRequest.SerializeToString,
                response_deserializer=metadata__service__pb2.MetadataResponse.FromString,
                _registered_method=True)
        self.GetEpisodeMetadata = channel.unary_unary(
                '/metadata.MetadataService/GetEpisodeMetadata',
                request_serializer=metadata__service__pb2.IMDbRequest.SerializeToString,
                response_deserializer=metadata__service__pb2.MetadataResponse.FromString,
                _registered_method=True)
        self.GetShowMetadata = channel.unary_unary(
                '/metadata.MetadataService/GetShowMetadata',
                request_serializer=metadata__service__pb2.IMDbRequest.SerializeToString,
                response_deserializer=metadata__service__pb2.MetadataResponse.FromString,
                _registered_method=True)
        self.GetShowSeasons = channel.unary_unary(
                '/metadata.MetadataService/GetShowSeasons',
                request_serializer=metadata__service__pb2.IMDbRequest.SerializeToString,
                response_deserializer=metadata__service__pb2.ShowSeasonsResponse.FromString,
                _registered_method=True)
        self.TMDbToIMDb = channel.unary_unary(
                '/metadata.MetadataService/TMDbToIMDb',
                request_serializer=metadata__service__pb2.TMDbRequest.SerializeToString,
                response_deserializer=metadata__service__pb2.IMDbResponse.FromString,
                _registered_method=True)
        self.BatchGetMetadata = channel.unary_unary(
                '/metadata.MetadataService/BatchGetMetadata',
                request_serializer=metadata__service__pb2.BatchIMDbRequest.SerializeToString,
                response_deserializer=metadata__service__pb2.BatchMetadataResponse.FromString,
                _registered_method=True)


class MetadataServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def GetMovieReleaseDates(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetMovieMetadata(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetEpisodeMetadata(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetShowMetadata(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetShowSeasons(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def TMDbToIMDb(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def BatchGetMetadata(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_MetadataServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'GetMovieReleaseDates': grpc.unary_unary_rpc_method_handler(
                    servicer.GetMovieReleaseDates,
                    request_deserializer=metadata__service__pb2.IMDbRequest.FromString,
                    response_serializer=metadata__service__pb2.ReleaseDatesResponse.SerializeToString,
            ),
            'GetMovieMetadata': grpc.unary_unary_rpc_method_handler(
                    servicer.GetMovieMetadata,
                    request_deserializer=metadata__service__pb2.IMDbRequest.FromString,
                    response_serializer=metadata__service__pb2.MetadataResponse.SerializeToString,
            ),
            'GetEpisodeMetadata': grpc.unary_unary_rpc_method_handler(
                    servicer.GetEpisodeMetadata,
                    request_deserializer=metadata__service__pb2.IMDbRequest.FromString,
                    response_serializer=metadata__service__pb2.MetadataResponse.SerializeToString,
            ),
            'GetShowMetadata': grpc.unary_unary_rpc_method_handler(
                    servicer.GetShowMetadata,
                    request_deserializer=metadata__service__pb2.IMDbRequest.FromString,
                    response_serializer=metadata__service__pb2.MetadataResponse.SerializeToString,
            ),
            'GetShowSeasons': grpc.unary_unary_rpc_method_handler(
                    servicer.GetShowSeasons,
                    request_deserializer=metadata__service__pb2.IMDbRequest.FromString,
                    response_serializer=metadata__service__pb2.ShowSeasonsResponse.SerializeToString,
            ),
            'TMDbToIMDb': grpc.unary_unary_rpc_method_handler(
                    servicer.TMDbToIMDb,
                    request_deserializer=metadata__service__pb2.TMDbRequest.FromString,
                    response_serializer=metadata__service__pb2.IMDbResponse.SerializeToString,
            ),
            'BatchGetMetadata': grpc.unary_unary_rpc_method_handler(
                    servicer.BatchGetMetadata,
                    request_deserializer=metadata__service__pb2.BatchIMDbRequest.FromString,
                    response_serializer=metadata__service__pb2.BatchMetadataResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'metadata.MetadataService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('metadata.MetadataService', rpc_method_handlers)


 # This class is part of an EXPERIMENTAL API.
class MetadataService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def GetMovieReleaseDates(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/metadata.MetadataService/GetMovieReleaseDates',
            metadata__service__pb2.IMDbRequest.SerializeToString,
            metadata__service__pb2.ReleaseDatesResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def GetMovieMetadata(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/metadata.MetadataService/GetMovieMetadata',
            metadata__service__pb2.IMDbRequest.SerializeToString,
            metadata__service__pb2.MetadataResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def GetEpisodeMetadata(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/metadata.MetadataService/GetEpisodeMetadata',
            metadata__service__pb2.IMDbRequest.SerializeToString,
            metadata__service__pb2.MetadataResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def GetShowMetadata(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/metadata.MetadataService/GetShowMetadata',
            metadata__service__pb2.IMDbRequest.SerializeToString,
            metadata__service__pb2.MetadataResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def GetShowSeasons(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/metadata.MetadataService/GetShowSeasons',
            metadata__service__pb2.IMDbRequest.SerializeToString,
            metadata__service__pb2.ShowSeasonsResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def TMDbToIMDb(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/metadata.MetadataService/TMDbToIMDb',
            metadata__service__pb2.TMDbRequest.SerializeToString,
            metadata__service__pb2.IMDbResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def BatchGetMetadata(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/metadata.MetadataService/BatchGetMetadata',
            metadata__service__pb2.BatchIMDbRequest.SerializeToString,
            metadata__service__pb2.BatchMetadataResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)
