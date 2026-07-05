# SPDX-FileCopyrightText: © 2025 Authors of the roar-net-api-py project <https://github.com/roar-net/roar-net-api-py/blob/main/AUTHORS>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Protocol, TypeVar

from ..operations import (
    SupportsEmptySolution,
    SupportsRandomSolution,
    SupportsOrderedSolution,
)

_TSolution = TypeVar("_TSolution", covariant=True)


class Problem(
    SupportsEmptySolution[_TSolution],
    SupportsRandomSolution[_TSolution],
    SupportsOrderedSolution[_TSolution],
    Protocol,
): ...
