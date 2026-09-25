try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        @staticmethod
        def _generate_next_value_(
            name: str,
            start: int,
            count: int,
            last_values: list[str],
        ) -> str:
            return name.lower()

        def __str__(self) -> str:
            return str(self.value)


__all__ = [
    "StrEnum",
]