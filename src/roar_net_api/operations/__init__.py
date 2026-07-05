# SPDX-FileCopyrightText: © 2025 Authors of the roar-net-api-py project <https://github.com/roar-net/roar-net-api-py/blob/main/AUTHORS>
#
# SPDX-License-Identifier: Apache-2.0

from .apply_move import SupportsApplyMove
from .copy_solution import SupportsCopySolution
from .empty_solution import SupportsEmptySolution
from .lower_bound_increment import SupportsLowerBoundIncrement
from .lower_bound import SupportsLowerBound
from .moves import SupportsMoves
from .objective_value_increment import SupportsObjectiveValueIncrement
from .objective_value import SupportsObjectiveValue
from .ordered_solution import SupportsOrderedSolution
from .random_move import SupportsRandomMove
from .random_moves_without_replacement import SupportsRandomMovesWithoutReplacement
from .random_solution import SupportsRandomSolution
from .apply_crossover import SupportsApplyCrossover

__all__ = [
    "SupportsApplyMove",
    "SupportsCopySolution",
    "SupportsEmptySolution",
    "SupportsLowerBoundIncrement",
    "SupportsLowerBound",
    "SupportsMoves",
    "SupportsObjectiveValueIncrement",
    "SupportsObjectiveValue",
    "SupportsRandomMove",
    "SupportsRandomMovesWithoutReplacement",
    "SupportsRandomSolution",
    "SupportsOrderedSolution",
    "SupportsApplyCrossover",
]
