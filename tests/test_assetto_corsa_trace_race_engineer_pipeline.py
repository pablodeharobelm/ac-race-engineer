from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ac_race_engineer.telemetry.assetto_corsa.trace import (
    DrivingTraceSample,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_race_engineer_pipeline import (
    AssettoCorsaRaceEngineerPipeline,
)


def sample(
    *,
    progress: float,
    elapsed: float,
) -> DrivingTraceSample:
    return DrivingTraceSample(
        progress=progress,
        elapsed_seconds=elapsed,
        speed_kmh=100.0,
        throttle=0.5,
        brake=0.0,
        steering_angle_deg=0.0,
    )


def reference_trace() -> tuple[
    DrivingTraceSample,
    ...,
]:
    return (
        sample(
            progress=0.0,
            elapsed=0.0,
        ),
        sample(
            progress=1.0,
            elapsed=100.0,
        ),
    )


def target_trace() -> tuple[
    DrivingTraceSample,
    ...,
]:
    return (
        sample(
            progress=0.0,
            elapsed=0.0,
        ),
        sample(
            progress=1.0,
            elapsed=101.0,
        ),
    )


def services() -> dict[
    str,
    MagicMock,
]:
    return {
        "trace": MagicMock(),
        "braking_zone": MagicMock(),
        "braking_comparison": MagicMock(),
        "braking_diagnostic": MagicMock(),
        "entry": MagicMock(),
        "entry_comparison": MagicMock(),
        "entry_diagnostic": MagicMock(),
        "exit": MagicMock(),
        "exit_comparison": MagicMock(),
        "exit_diagnostic": MagicMock(),
        "segmentation": MagicMock(),
        "segmentation_comparison": MagicMock(),
        "driving_diagnostic": MagicMock(),
        "recommendation": MagicMock(),
        "coaching": MagicMock(),
        "report": MagicMock(),
        "explanation": MagicMock(),
    }


def configured_services() -> tuple[
    dict[str, MagicMock],
    dict[str, object],
]:
    values = services()

    outputs: dict[
        str,
        object,
    ] = {
        "trace_comparison": object(),
        "reference_zones": object(),
        "target_zones": object(),
        "braking_comparison": object(),
        "braking_report": object(),
        "reference_entries": object(),
        "target_entries": object(),
        "entry_comparison": object(),
        "entry_report": object(),
        "reference_exits": object(),
        "target_exits": object(),
        "exit_comparison": object(),
        "exit_report": object(),
        "segmentation_comparison": object(),
        "diagnosis": object(),
        "recommendations": object(),
        "coaching_plan": object(),
        "report": object(),
        "explanation": object(),
    }

    reference_segmentation = (
        SimpleNamespace(
            corners=(
                "reference-corner",
            )
        )
    )

    target_segmentation = (
        SimpleNamespace(
            corners=(
                "target-corner",
            )
        )
    )

    values[
        "trace"
    ].compare.return_value = (
        outputs[
            "trace_comparison"
        ]
    )

    values[
        "braking_zone"
    ].analyze.side_effect = (
        outputs["reference_zones"],
        outputs["target_zones"],
    )

    values[
        "braking_comparison"
    ].compare.return_value = (
        outputs[
            "braking_comparison"
        ]
    )

    values[
        "braking_diagnostic"
    ].analyze.return_value = (
        outputs[
            "braking_report"
        ]
    )

    values[
        "entry"
    ].analyze.side_effect = (
        outputs[
            "reference_entries"
        ],
        outputs[
            "target_entries"
        ],
    )

    values[
        "entry_comparison"
    ].compare.return_value = (
        outputs[
            "entry_comparison"
        ]
    )

    values[
        "entry_diagnostic"
    ].analyze.return_value = (
        outputs[
            "entry_report"
        ]
    )

    values[
        "exit"
    ].analyze.side_effect = (
        outputs[
            "reference_exits"
        ],
        outputs[
            "target_exits"
        ],
    )

    values[
        "exit_comparison"
    ].compare.return_value = (
        outputs[
            "exit_comparison"
        ]
    )

    values[
        "exit_diagnostic"
    ].analyze.return_value = (
        outputs[
            "exit_report"
        ]
    )

    values[
        "segmentation"
    ].segment.side_effect = (
        reference_segmentation,
        target_segmentation,
    )

    values[
        "segmentation_comparison"
    ].compare.return_value = (
        outputs[
            "segmentation_comparison"
        ]
    )

    values[
        "driving_diagnostic"
    ].analyze.return_value = (
        outputs[
            "diagnosis"
        ]
    )

    values[
        "recommendation"
    ].generate.return_value = (
        outputs[
            "recommendations"
        ]
    )

    values[
        "coaching"
    ].build_plan.return_value = (
        outputs[
            "coaching_plan"
        ]
    )

    values[
        "report"
    ].build.return_value = (
        outputs[
            "report"
        ]
    )

    values[
        "explanation"
    ].explain.return_value = (
        outputs[
            "explanation"
        ]
    )

    return (
        values,
        outputs,
    )


def pipeline(
    values: dict[
        str,
        MagicMock,
    ],
    *,
    with_explanation: bool = True,
) -> AssettoCorsaRaceEngineerPipeline:
    return AssettoCorsaRaceEngineerPipeline(
        trace_comparison_service=(
            values["trace"]
        ),
        braking_zone_service=(
            values["braking_zone"]
        ),
        braking_comparison_service=(
            values["braking_comparison"]
        ),
        braking_diagnostic_service=(
            values["braking_diagnostic"]
        ),
        corner_entry_service=(
            values["entry"]
        ),
        corner_entry_comparison_service=(
            values["entry_comparison"]
        ),
        corner_entry_diagnostic_service=(
            values["entry_diagnostic"]
        ),
        corner_exit_service=(
            values["exit"]
        ),
        corner_exit_comparison_service=(
            values["exit_comparison"]
        ),
        corner_exit_diagnostic_service=(
            values["exit_diagnostic"]
        ),
        segmentation_service=(
            values["segmentation"]
        ),
        segmentation_comparison_service=(
            values[
                "segmentation_comparison"
            ]
        ),
        driving_diagnostic_service=(
            values["driving_diagnostic"]
        ),
        recommendation_service=(
            values["recommendation"]
        ),
        coaching_service=(
            values["coaching"]
        ),
        report_service=(
            values["report"]
        ),
        explanation_service=(
            values["explanation"]
            if with_explanation
            else None
        ),
    )


def test_runs_complete_deterministic_pipeline() -> None:
    (
        values,
        outputs,
    ) = configured_services()

    result = pipeline(
        values
    ).run(
        reference_lap_number=1,
        target_lap_number=2,
        reference_trace=reference_trace(),
        target_trace=target_trace(),
    )

    assert (
        result.trace_comparison
        is outputs[
            "trace_comparison"
        ]
    )

    assert (
        result.diagnosis
        is outputs[
            "diagnosis"
        ]
    )

    assert (
        result.recommendations
        is outputs[
            "recommendations"
        ]
    )

    assert (
        result.coaching_plan
        is outputs[
            "coaching_plan"
        ]
    )

    assert (
        result.report
        is outputs[
            "report"
        ]
    )

    assert (
        result.explanation
        is None
    )


def test_compares_reference_and_target_traces() -> None:
    (
        values,
        _,
    ) = configured_services()

    reference = reference_trace()
    target = target_trace()

    pipeline(
        values
    ).run(
        reference_lap_number=3,
        target_lap_number=7,
        reference_trace=reference,
        target_trace=target,
        grid_points=301,
    )

    values[
        "trace"
    ].compare.assert_called_once_with(
        reference_lap_number=3,
        target_lap_number=7,
        reference_trace=reference,
        target_trace=target,
        grid_points=301,
    )


def test_analyzes_both_laps() -> None:
    (
        values,
        outputs,
    ) = configured_services()

    reference = reference_trace()
    target = target_trace()

    pipeline(
        values
    ).run(
        reference_lap_number=1,
        target_lap_number=2,
        reference_trace=reference,
        target_trace=target,
    )

    assert (
        values[
            "braking_zone"
        ].analyze.call_count
        == 2
    )

    values[
        "entry"
    ].analyze.assert_any_call(
        samples=reference,
        braking_zones=(
            outputs[
                "reference_zones"
            ]
        ),
    )

    values[
        "entry"
    ].analyze.assert_any_call(
        samples=target,
        braking_zones=(
            outputs[
                "target_zones"
            ]
        ),
    )

    values[
        "exit"
    ].analyze.assert_any_call(
        samples=reference,
        entries=(
            outputs[
                "reference_entries"
            ]
        ),
    )

    values[
        "exit"
    ].analyze.assert_any_call(
        samples=target,
        entries=(
            outputs[
                "target_entries"
            ]
        ),
    )


def test_builds_unified_diagnosis() -> None:
    (
        values,
        outputs,
    ) = configured_services()

    pipeline(
        values
    ).run(
        reference_lap_number=1,
        target_lap_number=2,
        reference_trace=reference_trace(),
        target_trace=target_trace(),
    )

    values[
        "driving_diagnostic"
    ].analyze.assert_called_once_with(
        segmentation=(
            outputs[
                "segmentation_comparison"
            ]
        ),
        braking_report=(
            outputs[
                "braking_report"
            ]
        ),
        entry_report=(
            outputs[
                "entry_report"
            ]
        ),
        exit_report=(
            outputs[
                "exit_report"
            ]
        ),
    )


def test_builds_recommendations_and_coaching() -> None:
    (
        values,
        outputs,
    ) = configured_services()

    pipeline(
        values
    ).run(
        reference_lap_number=1,
        target_lap_number=2,
        reference_trace=reference_trace(),
        target_trace=target_trace(),
    )

    values[
        "recommendation"
    ].generate.assert_called_once_with(
        outputs[
            "diagnosis"
        ]
    )

    values[
        "coaching"
    ].build_plan.assert_called_once_with(
        outputs[
            "recommendations"
        ]
    )


def test_builds_final_report() -> None:
    (
        values,
        outputs,
    ) = configured_services()

    pipeline(
        values
    ).run(
        reference_lap_number=1,
        target_lap_number=2,
        reference_trace=reference_trace(),
        target_trace=target_trace(),
    )

    values[
        "report"
    ].build.assert_called_once_with(
        diagnosis=(
            outputs[
                "diagnosis"
            ]
        ),
        recommendations=(
            outputs[
                "recommendations"
            ]
        ),
        coaching_plan=(
            outputs[
                "coaching_plan"
            ]
        ),
    )


def test_generates_optional_explanation() -> None:
    (
        values,
        outputs,
    ) = configured_services()

    result = pipeline(
        values
    ).run(
        reference_lap_number=1,
        target_lap_number=2,
        reference_trace=reference_trace(),
        target_trace=target_trace(),
        explain=True,
        language="es",
    )

    values[
        "explanation"
    ].explain.assert_called_once_with(
        outputs[
            "report"
        ],
        language="es",
    )

    assert (
        result.explanation
        is outputs[
            "explanation"
        ]
    )


def test_does_not_call_llm_by_default() -> None:
    (
        values,
        _,
    ) = configured_services()

    pipeline(
        values
    ).run(
        reference_lap_number=1,
        target_lap_number=2,
        reference_trace=reference_trace(),
        target_trace=target_trace(),
    )

    values[
        "explanation"
    ].explain.assert_not_called()


def test_requires_explanation_service_when_requested() -> None:
    (
        values,
        _,
    ) = configured_services()

    service = pipeline(
        values,
        with_explanation=False,
    )

    with pytest.raises(
        ValueError,
        match="explanation_service",
    ):
        service.run(
            reference_lap_number=1,
            target_lap_number=2,
            reference_trace=reference_trace(),
            target_trace=target_trace(),
            explain=True,
        )


def test_segments_reference_and_target_laps() -> None:
    (
        values,
        outputs,
    ) = configured_services()

    pipeline(
        values
    ).run(
        reference_lap_number=1,
        target_lap_number=2,
        reference_trace=reference_trace(),
        target_trace=target_trace(),
    )

    values[
        "segmentation"
    ].segment.assert_any_call(
        braking_zones=(
            outputs[
                "reference_zones"
            ]
        ),
        entries=(
            outputs[
                "reference_entries"
            ]
        ),
        exits=(
            outputs[
                "reference_exits"
            ]
        ),
    )

    values[
        "segmentation"
    ].segment.assert_any_call(
        braking_zones=(
            outputs[
                "target_zones"
            ]
        ),
        entries=(
            outputs[
                "target_entries"
            ]
        ),
        exits=(
            outputs[
                "target_exits"
            ]
        ),
    )