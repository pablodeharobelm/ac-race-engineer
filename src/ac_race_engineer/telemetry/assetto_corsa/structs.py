from ctypes import (
    Structure,
    c_float,
    c_int32,
    c_uint16,
)

Float2 = c_float * 2
Float3 = c_float * 3
Float4 = c_float * 4
Float5 = c_float * 5

Vector3ByWheel = Float3 * 4

Utf16_15 = c_uint16 * 15
Utf16_33 = c_uint16 * 33


class ACPhysicsPage(Structure):
    """
    Prefix of Assetto Corsa SPageFilePhysics.

    Field order and 4-byte packing must match Assetto Corsa.
    """

    _pack_ = 4

    _fields_ = [
        ("packetId", c_int32),
        ("gas", c_float),
        ("brake", c_float),
        ("fuel", c_float),
        ("gear", c_int32),
        ("rpms", c_int32),
        ("steerAngle", c_float),
        ("speedKmh", c_float),
        ("velocity", Float3),
        ("accG", Float3),
        ("wheelSlip", Float4),
        ("wheelLoad", Float4),
        ("wheelsPressure", Float4),
        ("wheelAngularSpeed", Float4),
        ("tyreWear", Float4),
        ("tyreDirtyLevel", Float4),
        ("tyreCoreTemperature", Float4),
        ("camberRAD", Float4),
        ("suspensionTravel", Float4),
        ("drs", c_float),
        ("tc", c_float),
        ("heading", c_float),
        ("pitch", c_float),
        ("roll", c_float),
        ("cgHeight", c_float),
        ("carDamage", Float5),
        ("numberOfTyresOut", c_int32),
        ("pitLimiterOn", c_int32),
        ("abs", c_float),
        ("kersCharge", c_float),
        ("kersInput", c_float),
        ("autoShifterOn", c_int32),
        ("rideHeight", Float2),
        ("turboBoost", c_float),
        ("ballast", c_float),
        ("airDensity", c_float),
        ("airTemp", c_float),
        ("roadTemp", c_float),
        ("localAngularVel", Float3),
        ("finalFF", c_float),
        ("performanceMeter", c_float),
        ("engineBrake", c_int32),
        ("ersRecoveryLevel", c_int32),
        ("ersPowerLevel", c_int32),
        ("ersHeatCharging", c_int32),
        ("ersIsCharging", c_int32),
        ("kersCurrentKJ", c_float),
        ("drsAvailable", c_int32),
        ("drsEnabled", c_int32),
        ("brakeTemp", Float4),
        ("clutch", c_float),
        ("tyreTempI", Float4),
        ("tyreTempM", Float4),
        ("tyreTempO", Float4),
        ("isAIControlled", c_int32),
        ("tyreContactPoint", Vector3ByWheel),
        ("tyreContactNormal", Vector3ByWheel),
        ("tyreContactHeading", Vector3ByWheel),
        ("brakeBias", c_float),
        ("localVelocity", Float3),
    ]


class ACGraphicsPage(Structure):
    """
    Prefix of Assetto Corsa SPageFileGraphic required by the app.
    """

    _pack_ = 4

    _fields_ = [
        ("packetId", c_int32),
        ("status", c_int32),
        ("session", c_int32),
        ("currentTime", Utf16_15),
        ("lastTime", Utf16_15),
        ("bestTime", Utf16_15),
        ("split", Utf16_15),
        ("completedLaps", c_int32),
        ("position", c_int32),
        ("iCurrentTime", c_int32),
        ("iLastTime", c_int32),
        ("iBestTime", c_int32),
        ("sessionTimeLeft", c_float),
        ("distanceTraveled", c_float),
        ("isInPit", c_int32),
        ("currentSectorIndex", c_int32),
        ("lastSectorTime", c_int32),
        ("numberOfLaps", c_int32),
        ("tyreCompound", Utf16_33),
        ("replayTimeMultiplier", c_float),
        ("normalizedCarPosition", c_float),
        ("carCoordinates", Float3),
        ("penaltyTime", c_float),
        ("flag", c_int32),
        ("idealLineOn", c_int32),
        ("isInPitLane", c_int32),
        ("surfaceGrip", c_float),
    ]


class ACStaticPage(Structure):
    """
    Prefix of Assetto Corsa SPageFileStatic required by the app.

    We intentionally stop after tyreRadius because fields after it are
    currently unnecessary for the canonical telemetry model.
    """

    _pack_ = 4

    _fields_ = [
        ("smVersion", Utf16_15),
        ("acVersion", Utf16_15),
        ("numberOfSessions", c_int32),
        ("numCars", c_int32),
        ("carModel", Utf16_33),
        ("track", Utf16_33),
        ("playerName", Utf16_33),
        ("playerSurname", Utf16_33),
        ("playerNick", Utf16_33),
        ("sectorCount", c_int32),
        ("maxTorque", c_float),
        ("maxPower", c_float),
        ("maxRpm", c_int32),
        ("maxFuel", c_float),
        ("suspensionMaxTravel", Float4),
        ("tyreRadius", Float4),
    ]


def decode_utf16(
    value: object,
) -> str:
    """
    Decode a fixed-size UTF-16LE array from Assetto Corsa.
    """

    raw = bytes(value)

    decoded = raw.decode(
        "utf-16-le",
        errors="ignore",
    )

    return decoded.split(
        "\x00",
        1,
    )[0]