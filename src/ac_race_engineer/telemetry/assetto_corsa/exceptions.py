class AssettoCorsaSharedMemoryError(RuntimeError):
    """Base error for Assetto Corsa shared-memory access."""


class AssettoCorsaUnavailableError(
    AssettoCorsaSharedMemoryError
):
    """
    Raised when Assetto Corsa shared memory
    is not available.
    """


class AssettoCorsaReadError(
    AssettoCorsaSharedMemoryError
):
    """
    Raised when an Assetto Corsa shared-memory
    page cannot be read.
    """


class AssettoCorsaStaleDataError(
    AssettoCorsaSharedMemoryError
):
    """
    Raised when Assetto Corsa telemetry stops
    updating for too long.
    """