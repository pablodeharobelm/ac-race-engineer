from dataclasses import dataclass
from typing import Protocol

from ac_race_engineer.telemetry.assetto_corsa.trace_race_engineer_report import (
    RaceEngineerReport,
)


class RaceEngineerLLMClient(Protocol):
    """
    Minimal interface required from an LLM provider.

    Implementations may later use:

    - OpenAI
    - Ollama
    - another hosted provider
    - a local model

    The race-engineer domain layer does not depend on
    any specific provider.
    """

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        ...


@dataclass(frozen=True)
class RaceEngineerLLMRequest:
    system_prompt: str
    user_prompt: str

    language: str

    reference_lap_number: int
    target_lap_number: int


@dataclass(frozen=True)
class RaceEngineerExplanation:
    reference_lap_number: int
    target_lap_number: int

    language: str

    text: str

    recommendation_count: int
    corner_count: int


class AssettoCorsaRaceEngineerPromptBuilder:
    """
    Convert RaceEngineerReport into a strictly grounded
    prompt for an LLM.

    The LLM receives only conclusions that have already
    been produced by deterministic services.

    It is explicitly forbidden from:

    - creating new diagnoses,
    - creating new recommendations,
    - inventing telemetry,
    - changing measured values,
    - claiming causes unsupported by the report.
    """

    SYSTEM_PROMPT = """
You are the explanation layer of a sim-racing race engineer.

Your job is ONLY to explain the structured engineering report
provided by the application.

STRICT RULES:

1. Do not create new diagnoses.
2. Do not create new recommendations.
3. Do not invent telemetry values.
4. Do not modify any measured value.
5. Do not infer vehicle behaviour that is not present in the report.
6. Do not claim certainty about causes beyond the supplied diagnostics.
7. Use only the facts and coaching actions supplied in the report.
8. Keep advice practical, concise and understandable for a driver.
9. Prioritize the supplied coaching focuses in their existing order.
10. If there are no coaching focuses, do not invent one.
11. Clearly distinguish measured evidence from coaching instructions.
12. Never suggest setup changes unless explicitly present in the report.

The deterministic application is the authority.
You are only responsible for communicating its results naturally.
""".strip()

    @staticmethod
    def _format_seconds(
        value: float,
    ) -> str:
        return f"{value:+.3f} s"

    @staticmethod
    def _format_speed_delta(
        value: float,
    ) -> str:
        return f"{value:+.1f} km/h"

    def _corner_section(
        self,
        report: RaceEngineerReport,
    ) -> str:
        if not report.corners:
            return "No corner-level data available."

        lines: list[str] = []

        for corner in report.corners:
            minimum_speed_delta = (
                self._format_speed_delta(
                    corner.minimum_speed_delta_kmh
                )
            )

            apex_speed_delta = (
                self._format_speed_delta(
                    corner.apex_speed_delta_kmh
                )
            )

            exit_speed_delta = (
                self._format_speed_delta(
                    corner.exit_speed_delta_kmh
                )
            )

            lines.extend(
                (
                    f"Corner {corner.corner_number}:",
                    (
                        "  Time lost: "
                        f"{corner.time_lost_seconds:.3f} s"
                    ),
                    (
                        "  Time gained: "
                        f"{corner.time_gained_seconds:.3f} s"
                    ),
                    (
                        "  Entry loss: "
                        f"{corner.entry_time_loss_seconds:.3f} s"
                    ),
                    (
                        "  Exit loss: "
                        f"{corner.exit_time_loss_seconds:.3f} s"
                    ),
                    (
                        "  Dominant phase: "
                        f"{corner.dominant_phase.value}"
                    ),
                    (
                        "  Minimum speed delta: "
                        f"{minimum_speed_delta}"
                    ),
                    (
                        "  Apex speed delta: "
                        f"{apex_speed_delta}"
                    ),
                    (
                        "  Exit speed delta: "
                        f"{exit_speed_delta}"
                    ),
                    (
                        "  Diagnostic issue count: "
                        f"{corner.issue_count}"
                    ),
                )
            )

        return "\n".join(
            lines
        )

    def _focus_section(
        self,
        report: RaceEngineerReport,
    ) -> str:
        if not report.focuses:
            return (
                "No coaching focuses were selected. "
                "Do not invent recommendations."
            )

        lines: list[str] = []

        for focus in report.focuses:
            minimum_speed_delta = (
                self._format_speed_delta(
                    focus.minimum_speed_delta_kmh
                )
            )

            apex_speed_delta = (
                self._format_speed_delta(
                    focus.apex_speed_delta_kmh
                )
            )

            exit_speed_delta = (
                self._format_speed_delta(
                    focus.exit_speed_delta_kmh
                )
            )

            lines.extend(
                (
                    (
                        f"Focus #{focus.rank} "
                        f"({focus.focus_level.value}):"
                    ),
                    (
                        "  Corner: "
                        f"{focus.corner_number}"
                    ),
                    (
                        "  Priority: "
                        f"{focus.priority.value}"
                    ),
                    (
                        "  Phase: "
                        f"{focus.phase.value}"
                    ),
                    (
                        "  Diagnostic code: "
                        f"{focus.diagnostic_code}"
                    ),
                    (
                        "  Recommendation type: "
                        f"{focus.recommendation_type.value}"
                    ),
                    (
                        "  Title: "
                        f"{focus.title}"
                    ),
                    (
                        "  Instruction: "
                        f"{focus.instruction}"
                    ),
                    (
                        "  Rationale: "
                        f"{focus.rationale}"
                    ),
                    (
                        "  Corner time loss: "
                        f"{focus.corner_time_loss_seconds:.3f} s"
                    ),
                    (
                        "  Minimum speed delta: "
                        f"{minimum_speed_delta}"
                    ),
                    (
                        "  Apex speed delta: "
                        f"{apex_speed_delta}"
                    ),
                    (
                        "  Exit speed delta: "
                        f"{exit_speed_delta}"
                    ),
                )
            )

        return "\n".join(
            lines
        )

    def build(
        self,
        report: RaceEngineerReport,
        *,
        language: str = "es",
    ) -> RaceEngineerLLMRequest:
        normalized_language = (
            language.strip()
        )

        if not normalized_language:
            raise ValueError(
                "language cannot be empty"
            )

        net_delta = (
            self._format_seconds(
                report.net_time_delta_seconds
            )
        )

        corner_section = (
            self._corner_section(
                report
            )
        )

        focus_section = (
            self._focus_section(
                report
            )
        )

        user_prompt = f"""
Explain the following deterministic race-engineer report.

OUTPUT LANGUAGE:
{normalized_language}

COMMUNICATION STYLE:
- concise
- technical but understandable
- driver-focused
- no invented information
- explain the most important focus first
- mention relevant measured evidence
- avoid repeating the same advice several times

LAP COMPARISON:
Reference lap: {report.reference_lap_number}
Target lap: {report.target_lap_number}
Trend: {report.trend.value}
Total time lost: {report.total_time_lost_seconds:.3f} s
Total time gained: {report.total_time_gained_seconds:.3f} s
Net delta: {net_delta}
Corners analyzed: {report.corners_analyzed}
Corners with time loss: {report.corners_with_time_loss}
Corners with issues: {report.corners_with_issues}
Primary problem corner: {report.primary_problem_corner}
Recommendations generated: {report.recommendations_generated}
Recommendations selected: {report.recommendations_selected}
Recommendations suppressed: {report.recommendations_suppressed}

CORNER EVIDENCE:
{corner_section}

APPROVED COACHING FOCUSES:
{focus_section}

Produce a short race-engineer briefing using only this information.
""".strip()

        return RaceEngineerLLMRequest(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            language=normalized_language,
            reference_lap_number=(
                report.reference_lap_number
            ),
            target_lap_number=(
                report.target_lap_number
            ),
        )


class AssettoCorsaRaceEngineerExplanationService:
    """
    Execute the LLM explanation step.

    This service deliberately receives an already-built
    RaceEngineerReport rather than raw telemetry.
    """

    def __init__(
        self,
        *,
        client: RaceEngineerLLMClient,
        prompt_builder: (
            AssettoCorsaRaceEngineerPromptBuilder
            | None
        ) = None,
    ) -> None:
        self.client = client

        self.prompt_builder = (
            prompt_builder
            or AssettoCorsaRaceEngineerPromptBuilder()
        )

    def explain(
        self,
        report: RaceEngineerReport,
        *,
        language: str = "es",
    ) -> RaceEngineerExplanation:
        request = self.prompt_builder.build(
            report,
            language=language,
        )

        text = self.client.generate(
            system_prompt=(
                request.system_prompt
            ),
            user_prompt=(
                request.user_prompt
            ),
        )

        normalized_text = (
            text.strip()
        )

        if not normalized_text:
            raise ValueError(
                "LLM returned an empty explanation"
            )

        return RaceEngineerExplanation(
            reference_lap_number=(
                report.reference_lap_number
            ),
            target_lap_number=(
                report.target_lap_number
            ),
            language=request.language,
            text=normalized_text,
            recommendation_count=(
                report.recommendations_selected
            ),
            corner_count=(
                report.corners_analyzed
            ),
        )