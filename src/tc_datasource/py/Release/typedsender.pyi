"""Type stubs for typedsender module."""

from typing import Callable, Dict, List, Tuple

class SchemaGenerator:
    """Schema generator for creating typed channel schemas."""

    def __init__(self) -> None:
        """Initialize a new schema generator."""
        ...

    def set_schema_info(
        self, name: str, desc: str, major: int, minor: int, patch: int
    ) -> None:
        """Set schema name, description and version.

        Args:
            name: Schema name
            desc: Schema description
            major: Major version number
            minor: Minor version number
            patch: Patch version number
        """
        ...

    def build_schema_buffer(self) -> Tuple[bytes, bytes]:
        """Build and return the schema buffer as bytes.

        Returns:
            Tuple containing (binary signautre, binary schema buffer).
        """
        ...

    def add_vector_def(
        self, id: int, name: str, desc: str, len: int, default_meta: List[float]
    ) -> str:
        """Add a vector definition to the schema.

        Args:
            id: Unique vector definition ID
            name: Vector type name
            desc: Vector type description
            len: Vector length (0 for dynamic length)
            default_meta: Default metadata values

        Returns:
            Empty string on success, error message on failure
        """
        ...

    def add_trimesh_def(
        self,
        id: int,
        name: str,
        desc: str,
        vertexes: List[Tuple[float, float, float]],
        triangles: List[Tuple[int, int, int]],
        properties: List[Tuple[str, str]],
    ) -> str:
        """Add a trimesh definition to the schema.

        Args:
            id: Unique trimesh definition ID
            name: TriMesh type name
            desc: TriMesh type description
            vertexes: Vertex coordinates (x, y, z)
            triangles: Triangle vertex indices (v0, v1, v2)
            properties: Property name/description pairs

        Returns:
            Empty string on success, error message on failure
        """
        ...

    def add_namedtuple_def(
        self,
        id: int,
        name: str,
        desc: str,
        field_names: List[Tuple[str, str]],
        default_meta: List[float],
    ) -> str:
        """Add a namedtuple definition to the schema.

        Args:
            id: Unique namedtuple definition ID
            name: Namedtuple type name
            desc: Namedtuple type description
            field_names: Field name/description pairs
            default_meta: Optional default values

        Returns:
            Empty string on success, error message on failure
        """
        ...

class ISenderTransport:
    """Base interface for sender transport."""

    def session_begin(self) -> None:
        """Begin a new session."""
        ...

    def session_end(self) -> None:
        """End the current session."""
        ...

class ZMQResTransport(ISenderTransport):
    """ZeroMQ response-based transport implementation."""

    def __init__(self, endpoint: str) -> None:
        """Initialize ZMQ transport.

        Args:
            endpoint: ZeroMQ endpoint address (e.g., 'tcp://*:5555')
        """
        ...

    def set_on_client_connected(self, callback: Callable[[], None]) -> None:
        """Set callback for client connection events.

        Args:
            callback: Function to call when a client connects
        """
        ...

    def stop(self) -> None:
        """Stop the transport."""
        ...

class SenderManager:
    """Manager for sending typed data over channels."""

    def __init__(self, schema_buffer: bytes) -> None:
        """Initialize sender manager with schema.

        Args:
            schema_buffer: Binary schema buffer

        Raises:
            RuntimeError: If schema loading fails
        """
        ...

    def set_transport(self, transport: ISenderTransport) -> None:
        """Set the transport layer.

        Args:
            transport: Transport implementation
        """
        ...

    def session_initializing(self, session_id: int) -> str:
        """Signal that session is initializing.

        Args:
            session_id: Unique session identifier

        Returns:
            Empty string on success, error message on failure
        """
        ...

    def session_initialized(self) -> str:
        """Signal that session has been initialized.

        Returns:
            Empty string on success, error message on failure
        """
        ...

    def session_terminated(self, total_time: float) -> str:
        """Signal that session has terminated.

        Args:
            total_time: Total session time in seconds

        Returns:
            Empty string on success, error message on failure
        """
        ...

    def get_vector_sender(self, id: int, len: int) -> "VectorSender":
        """Get a vector sender by id and length.

        Args:
            id: Vector definition ID
            len: Expected vector length (0 for dynamic length)

        Returns:
            Vector sender instance
        """
        ...

    def get_trimesh_sender(self, id: int) -> "TriMeshSender":
        """Get a trimesh sender by id.

        Args:
            id: TriMesh definition ID

        Returns:
            TriMesh sender instance
        """
        ...

    def get_namedtuple_sender(
        self, id: int, field_names: List[str]
    ) -> "NamedTupleSender":
        """Get a namedtuple sender by id and field names.

        Args:
            id: Namedtuple definition ID
            field_names: Field name list (empty for dynamic names)

        Returns:
            Namedtuple sender instance
        """
        ...

class VectorSender:
    """Sender for vector data."""

    def send_init(self, data: List[float]) -> str:
        """Initialize vector with initial data.

        Args:
            data: Initial vector data

        Returns:
            Empty string on success, error message on failure
        """
        ...

    def send_frame(self, time: float, data: List[float]) -> str:
        """Send a frame of vector data with timestamp.

        Args:
            time: Frame timestamp
            data: Vector data as list of floats

        Returns:
            Empty string on success, error message on failure
        """
        ...

    def error(self) -> str:
        """Check if sender is in error state.

        Returns:
            Empty string on success, error message on failure
        """
        ...

class TriMeshSender:
    """Sender for trimesh data."""

    def send_init(self, props: Dict[str, List[float]]) -> str:
        """Initialize trimesh properties.

        Args:
            props: Property values keyed by name

        Returns:
            Empty string on success, error message on failure
        """
        ...

    def send_frame(self, time: float, props: Dict[str, List[float]]) -> str:
        """Send a frame of trimesh property data with timestamp.

        Args:
            time: Frame timestamp
            props: Property values keyed by name

        Returns:
            Empty string on success, error message on failure
        """
        ...

    def error(self) -> str:
        """Check if sender is in error state.

        Returns:
            Empty string on success, error message on failure
        """
        ...

class NamedTupleSender:
    """Sender for namedtuple data."""

    def send_init(self, data: Dict[str, float]) -> str:
        """Initialize namedtuple with initial data.

        Args:
            data: Initial namedtuple data

        Returns:
            Empty string on success, error message on failure
        """
        ...

    def send_frame(self, time: float, data: Dict[str, float]) -> str:
        """Send a frame of namedtuple data with timestamp.

        Args:
            time: Frame timestamp
            data: Namedtuple data as dict of floats

        Returns:
            Empty string on success, error message on failure
        """
        ...

    def error(self) -> str:
        """Check if sender is in error state.

        Returns:
            Empty string on success, error message on failure
        """
        ...
