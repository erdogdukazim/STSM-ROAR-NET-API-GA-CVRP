# SPDX-FileCopyrightText: © 2025 Authors of the roar-net-api-py project <https://github.com/roar-net/roar-net-api-py/blob/main/AUTHORS>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Protocol, TypeVar

Move = TypeVar("Move", covariant=True)


class SupportsMutationMove(Protocol[Move]):
    def mutation_move(self) -> Move: ...
