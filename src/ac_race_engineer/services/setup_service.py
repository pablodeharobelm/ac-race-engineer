from ac_race_engineer.domain.car import (
    CarDefinition,
)
from ac_race_engineer.domain.setup import (
    CarSetup,
    SetupChange,
    SetupComparison,
)


class SetupService:

    @staticmethod
    def validate_setup(
        car: CarDefinition,
        setup: CarSetup,
    ) -> None:

        if setup.car_id != car.car_id:
            raise ValueError(
                "Setup does not belong to this car"
            )

        for parameter, value in setup.values.items():

            definition = car.setup_parameters.get(
                parameter
            )

            if definition is None:
                raise ValueError(
                    f"Unsupported setup parameter: {parameter}"
                )

            if not (
                definition.minimum
                <= value
                <= definition.maximum
            ):
                raise ValueError(
                    f"{parameter}={value} is outside "
                    f"allowed range "
                    f"[{definition.minimum}, "
                    f"{definition.maximum}]"
                )

    @staticmethod
    def compare(
        setup_a: CarSetup,
        setup_b: CarSetup,
    ) -> SetupComparison:

        if setup_a.car_id != setup_b.car_id:
            raise ValueError(
                "Cannot compare setups from different cars"
            )

        parameters = (
            set(setup_a.values)
            | set(setup_b.values)
        )

        changes = []

        for parameter in sorted(
            parameters
        ):

            value_a = setup_a.values.get(
                parameter
            )

            value_b = setup_b.values.get(
                parameter
            )

            if (
                value_a is None
                or value_b is None
            ):
                continue

            if value_a == value_b:
                continue

            changes.append(
                SetupChange(
                    parameter=parameter,
                    previous_value=value_a,
                    new_value=value_b,
                    delta=(
                        value_b
                        - value_a
                    ),
                )
            )

        return SetupComparison(
            setup_a_id=setup_a.setup_id,
            setup_b_id=setup_b.setup_id,
            changes=changes,
        )

