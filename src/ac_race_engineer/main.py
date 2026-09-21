from ac_race_engineer.storage.recorder import SessionRecorder
from ac_race_engineer.telemetry.simulator import SimulatorSource


def main():

    hz = 20
    duration_seconds = 60

    simulator = SimulatorSource(
        hz=hz,
    )

    recorder = SessionRecorder(
        source=simulator,
    )

    sample_count = (
        hz
        * duration_seconds
    )

    output_file = recorder.record_samples(
        sample_count=sample_count,
    )

    print()
    print("Session recorded successfully")
    print(f"Source: {simulator.source_name}")
    print(f"Duration: {duration_seconds} seconds")
    print(f"Samples: {sample_count}")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()