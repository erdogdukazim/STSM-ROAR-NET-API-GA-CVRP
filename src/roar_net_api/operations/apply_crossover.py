# SPDX-FileCopyrightText: © 2025 Authors of the roar-net-api-py project <https://github.com/roar-net/roar-net-api-py/blob/main/AUTHORS>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Protocol, TypeVar

Solution = TypeVar("Solution")


class SupportsApplyCrossover(Protocol[Solution]):
    def apply_crossover(self, parents: list[Solution]) -> list[Solution]: ...