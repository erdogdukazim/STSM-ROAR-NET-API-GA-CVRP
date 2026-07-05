from __future__ import annotations

import math
import random
import time
from io import StringIO
from logging import getLogger
from typing import Optional, Protocol, Self, TextIO, TypeVar, final


from ..operations import (
    SupportsApplyCrossover,
    SupportsApplyMove,
    SupportsCopySolution,
    SupportsEmptySolution,
    SupportsObjectiveValue,
    SupportsObjectiveValueIncrement,
    SupportsRandomMove,
    SupportsRandomSolution,
    SupportsOrderedSolution,
)
from ..operations.mutation_move import SupportsMutationMove

log = getLogger(__name__)


# ------------------------------- Protocol Types ------------------------------

class _Solution(SupportsCopySolution, SupportsObjectiveValue, Protocol):
    ...


_TSolution = TypeVar("_TSolution", bound=_Solution)


class _MutationMove(
    SupportsApplyMove[_TSolution],
    SupportsRandomMove[_TSolution, "_MutationMove[_TSolution]"],
    Protocol,
):
    ...


class _CrossoverMove(
    SupportsApplyCrossover[_TSolution],
    Protocol,
):
    ...


class _Problem(
    SupportsMutationMove[_MutationMove[_TSolution]],
    SupportsEmptySolution[_TSolution],
    SupportsRandomSolution[_TSolution],
    SupportsOrderedSolution[_TSolution],
    Protocol,
):
    ...

# ------------------------------- DEFINITIONS ------------------------------

BINARY_TOURNAMENT_SELECTION = "binary_tournament"
ROULETTE_WHEEL_SELECTION = "roulette_wheel"
ALL_RANDOM = "all_random"
CW_AND_RANDOM = "cw_and_random"


# ----------------------------------- Moves ----------------------------------
@final
class InsertMove(SupportsApplyMove[_TSolution], SupportsObjectiveValueIncrement[_TSolution]):
    def __init__(self, vehicle_1_index: int, customer_from_index: int,
                 vehicle_2_index: int, customer_to_index: int):
        self.vehicle_1_index = vehicle_1_index
        self.customer_current_index = customer_from_index
        self.vehicle_2_index = vehicle_2_index
        self.customer_new_index = customer_to_index

    def objective_value_increment(self, solution: _TSolution) -> float:
        prob = solution.problem

        # If the same vehicle and same customer position, no change in objective value
        if (
            self.vehicle_1_index == self.vehicle_2_index
            and self.customer_current_index == self.customer_new_index
        ):
            return 0.0

        v1 = solution.vehicles[self.vehicle_1_index]
        v2 = solution.vehicles[self.vehicle_2_index]
        customer = v1.tour[self.customer_current_index]

        if (
            self.vehicle_1_index != self.vehicle_2_index
            and v2.load + prob.demand[customer] > prob.capacity
        ):
            return float("inf")

        prev_removed = v1.previous_customer(self.customer_current_index)
        next_removed = v1.next_customer(self.customer_current_index + 1)
        delta_remove = (
            prob.dist[prev_removed][next_removed]
            - prob.dist[prev_removed][customer]
            - prob.dist[customer][next_removed]
        )

        if self.vehicle_1_index == self.vehicle_2_index:
            removed_tour_length = len(v1.tour) - 1

            if self.customer_new_index < self.customer_current_index:
                prev_inserted = v1.previous_customer(self.customer_new_index)
            else:
                prev_inserted = v1.tour[self.customer_new_index]

            if self.customer_new_index == removed_tour_length:
                next_inserted = v1.next_customer(len(v1.tour))
            elif self.customer_new_index < self.customer_current_index:
                next_inserted = v1.tour[self.customer_new_index]
            else:
                next_inserted = v1.next_customer(self.customer_new_index + 1)
        else:
            prev_inserted = v2.previous_customer(self.customer_new_index)
            next_inserted = v2.next_customer(self.customer_new_index)

        delta_insert = (
            - prob.dist[prev_inserted][next_inserted]
            + prob.dist[prev_inserted][customer]
            + prob.dist[customer][next_inserted]
        )

        return float(delta_remove + delta_insert)

    def apply_move(self, solution: _TSolution) -> _TSolution:
        prob = solution.problem
        incr = self.objective_value_increment(solution)

        assert incr != float("inf")

        v1 = solution.vehicles[self.vehicle_1_index]
        v2 = solution.vehicles[self.vehicle_2_index]

        moved_customer = v1.tour[self.customer_current_index]
        v1.remove_customer_at_index(self.customer_current_index)
        if (self.vehicle_1_index == self.vehicle_2_index
            and self.customer_current_index < self.customer_new_index):
            self.customer_new_index -= 1

        v2.insert_customer(moved_customer, self.customer_new_index)

        solution.lb += incr
        solution.construct_giant_tour()

        return solution

@final
class SwapMove(SupportsApplyMove[_TSolution], SupportsObjectiveValueIncrement[_TSolution]):
    def __init__(self, vehicle_1_index: int, customer_1_index: int,
        vehicle_2_index: int, customer_2_index: int):
        self.vehicle_1_index = vehicle_1_index
        self.customer_1_index = customer_1_index
        self.vehicle_2_index = vehicle_2_index
        self.customer_2_index = customer_2_index

    def objective_value_increment(self, solution: _TSolution) -> float:
        prob = solution.problem

        # If either vehicle is empty, no change in objective value
        if (not solution.vehicles[self.vehicle_1_index].tour
                or not solution.vehicles[self.vehicle_2_index].tour):
            return float("inf")

        # If the same vehicle and same customer position, no change in objective value
        if (
            self.vehicle_1_index == self.vehicle_2_index
            and self.customer_1_index == self.customer_2_index
        ):
            return 0.0

        v1 = solution.vehicles[self.vehicle_1_index]
        v2 = solution.vehicles[self.vehicle_2_index]
        customer_1 = v1.tour[self.customer_1_index]
        customer_2 = v2.tour[self.customer_2_index]
        demand_1 = prob.demand[customer_1]
        demand_2 = prob.demand[customer_2]

        # Check if the swap would exceed vehicle capacity
        if self.vehicle_1_index != self.vehicle_2_index:
            if (
                v1.load - demand_1 + demand_2 > prob.capacity
                or v2.load - demand_2 + demand_1 > prob.capacity
            ):
                return float("inf")

        prev_1_before_swap = v1.previous_customer(self.customer_1_index)
        next_1_before_swap = v1.next_customer(self.customer_1_index)
        prev_2_before_swap = v2.previous_customer(self.customer_2_index)
        next_2_before_swap = v2.next_customer(self.customer_2_index)

        delta_remove = (
                + prob.dist[prev_1_before_swap][customer_1]
                + prob.dist[customer_1][next_1_before_swap]
                + prob.dist[prev_2_before_swap][customer_2]
                + prob.dist[customer_2][next_2_before_swap]
        )

        prev_1_after_swap = prev_1_before_swap
        next_1_after_swap = next_1_before_swap
        prev_2_after_swap = prev_2_before_swap
        next_2_after_swap = next_2_before_swap

        # If both customers are in the same vehicle and adjacent
        if self.vehicle_1_index == self.vehicle_2_index:
            if self.customer_1_index == self.customer_2_index - 1:
                prev_1_after_swap = prev_1_before_swap
                next_1_after_swap = customer_1
                prev_2_after_swap = customer_2
                next_2_after_swap = next_2_before_swap
            elif self.customer_1_index - 1 == self.customer_2_index:
                prev_1_after_swap = customer_1
                next_1_after_swap = next_1_before_swap
                prev_2_after_swap = prev_2_before_swap
                next_2_after_swap = customer_2

        delta_add = (
                + prob.dist[prev_1_after_swap][customer_2]
                + prob.dist[customer_2][next_1_after_swap]
                + prob.dist[prev_2_after_swap][customer_1]
                + prob.dist[customer_1][next_2_after_swap]
        )

        return delta_add - delta_remove

    def apply_move(self, solution: _TSolution) -> _TSolution:
        prob = solution.problem
        incr = self.objective_value_increment(solution)

        assert incr != float("inf")

        v1 = solution.vehicles[self.vehicle_1_index]
        v2 = solution.vehicles[self.vehicle_2_index]
        customer_1 = v1.tour[self.customer_1_index]
        customer_2 = v2.tour[self.customer_2_index]

        v1.tour[self.customer_1_index] = customer_2
        v2.tour[self.customer_2_index] = customer_1

        if self.vehicle_1_index != self.vehicle_2_index:
            demand_1 = prob.demand[customer_1]
            demand_2 = prob.demand[customer_2]
            v1.load += demand_2 - demand_1
            v2.load += demand_1 - demand_2

        solution.lb += incr

        if (self.vehicle_1_index == self.vehicle_2_index
            and self.customer_1_index < self.customer_2_index):
            v2.remove_customer_at_index(self.customer_2_index)
            v1.remove_customer_at_index(self.customer_1_index)
            v1.insert_customer(customer_2, self.customer_1_index)
            v2.insert_customer(customer_1, self.customer_2_index)
        else:
            v1.remove_customer_at_index(self.customer_1_index)
            v2.remove_customer_at_index(self.customer_2_index)
            v2.insert_customer(customer_1, self.customer_2_index)
            v1.insert_customer(customer_2, self.customer_1_index)

        solution.construct_giant_tour()

        return solution

# --------------------------------- Selection --------------------------------

class _Selection:
    def select(
        self,
        population: list[_TSolution],
        selection_pool: Optional[list[_TSolution]] = None,
    ) -> _TSolution:
        raise NotImplementedError


@final
class BinaryTournamentSelection(_Selection):
    def select(
        self,
        population: list[_TSolution],
        selection_pool: Optional[list[_TSolution]] = None,
    ) -> _TSolution:
        candidates = population if selection_pool is None else selection_pool

        if len(candidates) == 1:
            winner = candidates[0]
        else:
            a, b = random.sample(candidates, 2)
            winner = a if a.objective_value() <= b.objective_value() else b

        if selection_pool is not None:
            selection_pool.remove(winner)

        return winner


@final
class RouletteWheelSelection(_Selection):
    def select(
        self,
        population: list[_TSolution],
        selection_pool: Optional[list[_TSolution]] = None,
    ) -> _TSolution:
        candidates = population if selection_pool is None else selection_pool

        if len(candidates) == 1:
            winner = candidates[0]
        else:
            objective_values = [
                solution.objective_value()
                for solution in candidates
            ]
            finite_values = [
                value
                for value in objective_values
                if value is not None and value != float("inf")
            ]

            if not finite_values:
                winner = random.choice(candidates)
            else:
                worst = max(finite_values)
                weights = [
                    0.0
                    if value is None or value == float("inf")
                    else worst - value + 1.0
                    for value in objective_values
                ]
                winner = (
                    random.choice(candidates)
                    if sum(weights) <= 0.0
                    else random.choices(candidates, weights=weights, k=1)[0]
                )

        if selection_pool is not None:
            selection_pool.remove(winner)

        return winner


def _create_selection(name: str) -> _Selection:
    if name == BINARY_TOURNAMENT_SELECTION:
        return BinaryTournamentSelection()

    if name == ROULETTE_WHEEL_SELECTION:
        return RouletteWheelSelection()

    raise ValueError(f"Unknown selection type: {name}")


# --------------------------------- Mutations --------------------------------

class _Mutation(SupportsApplyMove[_TSolution], SupportsRandomMove[_TSolution, Self]):
    def __init__(self, problem: _Problem, repetition_rate: float = 0.10):
        self.problem = problem
        self.repetition_rate = float(repetition_rate)

    @property
    def repetition_count(self) -> int:
        if self.problem.n == 0 or self.repetition_rate <= 0.0:
            return 0

        return max(1, math.ceil(self.repetition_rate * self.problem.n))

    def random_move(self, solution: _TSolution) -> Optional[Self]:
        assert solution.problem == self.problem

        if not solution.vehicles:
            return None

        return self


@final
class InsertMutation(_Mutation):
    def apply_move(self, solution: _TSolution) -> _TSolution:
        for _ in range(self.repetition_count):
            move = self._random_insert_move(solution)

            if move is not None:
                move.apply_move(solution)

        return solution

    def _random_insert_move(self, solution: _TSolution) -> Optional[InsertMove]:
        source_candidates = [
            ix
            for ix, vehicle in enumerate(solution.vehicles)
            if vehicle.tour
        ]

        if not source_candidates:
            return None

        # Forcing a maximum number of attempts to find a valid insert move to avoid infinite loops
        for _ in range(100):
            vehicle_1_index = random.choice(source_candidates)
            vehicle_2_index = random.randrange(len(solution.vehicles))

            v1 = solution.vehicles[vehicle_1_index]
            v2 = solution.vehicles[vehicle_2_index]

            customer_from_index = random.randrange(len(v1.tour))

            if vehicle_1_index == vehicle_2_index:
                if len(v1.tour) <= 1:
                    continue

                customer_to_index = random.randrange(len(v1.tour))

                if customer_to_index == customer_from_index:
                    continue
            else:
                customer_to_index = random.randrange(len(v2.tour) + 1)

            move = InsertMove(
                vehicle_1_index,
                customer_from_index,
                vehicle_2_index,
                customer_to_index,
            )

            if move.objective_value_increment(solution) != float("inf"):
                return move

        return None


@final
class SwapMutation(_Mutation):
    def apply_move(self, solution: _TSolution) -> _TSolution:
        for _ in range(self.repetition_count):
            move = self._random_swap_move(solution)

            if move is not None:
                move.apply_move(solution)

        return solution

    def _random_swap_move(self, solution: _TSolution) -> Optional[SwapMove]:
        vehicle_candidates = [
            ix
            for ix, vehicle in enumerate(solution.vehicles)
            if vehicle.tour
        ]

        if len(vehicle_candidates) < 2 and not any(
            len(solution.vehicles[ix].tour) > 1
            for ix in vehicle_candidates
        ):
            return None

        # Forcing a maximum number of attempts to find a valid swap move to avoid infinite loops
        for _ in range(100):
            vehicle_1_index = random.choice(vehicle_candidates)
            vehicle_2_index = random.choice(vehicle_candidates)

            v1 = solution.vehicles[vehicle_1_index]
            v2 = solution.vehicles[vehicle_2_index]

            customer_1_index = random.randrange(len(v1.tour))
            customer_2_index = random.randrange(len(v2.tour))

            if (
                vehicle_1_index == vehicle_2_index
                and customer_1_index == customer_2_index
            ):
                continue

            move = SwapMove(
                vehicle_1_index,
                customer_1_index,
                vehicle_2_index,
                customer_2_index,
            )

            if move.objective_value_increment(solution) != float("inf"):
                return move

        return None


@final
class NoMutation(_Mutation):
    def random_move(self, solution: _TSolution) -> Optional[Self]:
        assert solution.problem == self.problem
        return None

    def apply_move(self, solution: _TSolution) -> _TSolution:
        return solution


# --------------------------------- Crossovers -------------------------------

class _Crossover(SupportsApplyCrossover[_TSolution]):
    def __init__(self, problem: _Problem):
        self.problem = problem

    def _decode_giant_tour(self, giant_tour: list[int]) -> _TSolution:

        return self.problem.solution_from_giant_tour(giant_tour)


@final
class PMXCrossover(_Crossover):
    def apply_crossover(self, parents: list[_TSolution]) -> list[_TSolution]:
        parent_1 = parents[0]
        parent_2 = parents[1]

        assert parent_1.problem == self.problem
        assert parent_2.problem == self.problem

        p1 = parent_1.giant_tour.copy()
        p2 = parent_2.giant_tour.copy()

        n = len(p1)
        cut_1 = random.randint(0, n - 2)
        cut_2 = random.randint(cut_1 + 1, n - 1)

        child_1_tour = self._pmx(p1, p2, cut_1, cut_2, n)
        child_2_tour = self._pmx(p2, p1, cut_1, cut_2, n)

        return [
            self._decode_giant_tour(child_1_tour),
            self._decode_giant_tour(child_2_tour),
        ]

    def _pmx(self, parent_a: list[int], parent_b: list[int], cut_1: int, cut_2: int, n: int) -> list[int]:
        child: list[Optional[int]] = [None] * n

        for ix in range(cut_1, cut_2 + 1):
            child[ix] = parent_a[ix]

        for ix in range(cut_1, cut_2 + 1):
            item = parent_b[ix]

            if item in child:
                continue

            pos = ix

            while True:
                mapped_item = parent_a[pos]
                pos = parent_b.index(mapped_item)

                if child[pos] is None:
                    child[pos] = item
                    break

        for ix in range(n):
            if child[ix] is None:
                child[ix] = parent_b[ix]

        return [item for item in child if item is not None]


@final
class CXCrossover(_Crossover):
    def apply_crossover(self, parents: list[_TSolution]) -> list[_TSolution]:
        parent_1 = parents[0]
        parent_2 = parents[1]

        assert parent_1.problem == self.problem
        assert parent_2.problem == self.problem

        p1 = parent_1.giant_tour.copy()
        p2 = parent_2.giant_tour.copy()

        n = len(p1)

        child_1_tour = self._cx(p1, p2, n, True)
        child_2_tour = self._cx(p1, p2, n, False)

        return [
            self._decode_giant_tour(child_1_tour),
            self._decode_giant_tour(child_2_tour),
        ]

    def _cx(self, parent_a: list[int], parent_b: list[int], n: int, start_from_a: bool) -> list[int]:
        child: list[Optional[int]] = [None] * n
        visited = [False] * n
        take_from_a = start_from_a

        for start_ix in range(n):
            if visited[start_ix]:
                continue

            cycle_indices: list[int] = []
            ix = start_ix

            while not visited[ix]:
                visited[ix] = True
                cycle_indices.append(ix)
                ix = parent_b.index(parent_a[ix])

            source = parent_a if take_from_a else parent_b

            for cycle_ix in cycle_indices:
                child[cycle_ix] = source[cycle_ix]

            take_from_a = not take_from_a

        return [item for item in child if item is not None]


@final
class OXCrossover(_Crossover):
    def apply_crossover(self, parents: list[_TSolution]) -> list[_TSolution]:
        parent_1 = parents[0]
        parent_2 = parents[1]

        assert parent_1.problem == self.problem
        assert parent_2.problem == self.problem

        p1 = parent_1.giant_tour.copy()
        p2 = parent_2.giant_tour.copy()

        n = len(p1)
        cut_1 = random.randint(0, n - 2)
        cut_2 = random.randint(cut_1 + 1, n - 1)

        child_1_tour = self._ox(p1, p2, cut_1, cut_2, n)
        child_2_tour = self._ox(p2, p1, cut_1, cut_2, n)

        return [
            self._decode_giant_tour(child_1_tour),
            self._decode_giant_tour(child_2_tour),
        ]

    def _ox(self, parent_a: list[int], parent_b: list[int], cut_1: int, cut_2: int, n: int) -> list[int]:
        child: list[Optional[int]] = [None] * n
        child[cut_1:cut_2 + 1] = parent_a[cut_1:cut_2 + 1]

        index = (cut_2 + 1) % n
        i = index

        while True:
            customer = parent_b[i]

            if customer not in child:
                child[index] = customer
                index = (index + 1) % n

            if i == cut_2:
                break

            i = (i + 1) % n

        return [item for item in child if item is not None]


@final
class NoCrossover(_Crossover):
    def apply_crossover(self, parents: list[_TSolution]) -> list[_TSolution]:
        return [parent.copy_solution() for parent in parents]



def _write_solution_detail(f: TextIO, solution: _TSolution) -> None:
    if hasattr(solution, "to_textio"):
        buffer = StringIO()
        solution.to_textio(buffer)
        running_time_seconds = getattr(solution, "running_time_seconds", None)

        if running_time_seconds is None:
            f.write(buffer.getvalue())
            return

        for line in buffer.getvalue().splitlines(keepends=True):
            f.write(line)

            if line.startswith("COST :"):
                f.write(f"RUNNING TIME: {running_time_seconds:.2f} seconds\n")
    else:
        f.write(str(solution))
        f.write("\n")


def _format_objective(value: object) -> str:
    if isinstance(value, int | float):
        return f"{value:.2f}"
    return str(value)


def _format_population_solution_record(solution: _TSolution) -> str:
    route_records = [
        str(vehicle.tour)
        for vehicle in solution.vehicles
    ]
    return f"[{', '.join([*route_records, _format_objective(solution.objective_value())])}]"


def _write_iteration_files(
    iteration: int,
    best: _TSolution,
    population: list[_TSolution],
    best_file_path: str,
    population_file_path: str,
    convergence_file_path: str,
) -> None:
    mode = "w" if iteration == 0 else "a"
    best_obj = _format_objective(best.objective_value())

    with open(best_file_path, mode, encoding="utf-8") as f:
        f.write(f"ITERATION {iteration}\n")
        f.write(f"BEST_OBJECTIVE : {best_obj}\n")
        _write_solution_detail(f, best)
        f.write("\n")

    with open(population_file_path, mode, encoding="utf-8") as f:
        population_records = [
            _format_population_solution_record(solution)
            for solution in population
        ]
        f.write(",".join([str(iteration), *population_records]))
        f.write("\n")

    with open(convergence_file_path, mode, encoding="utf-8") as f:
        f.write(f"{iteration},{best_obj}\n")


# ------------------------------------- GA -------------------------------------


def ga(
    problem: _Problem[_TSolution],
    crossover: _CrossoverMove[_TSolution],
    max_iterations: int,
    population_size: int,
    crossover_probability: float,
    mutation_probability: float,
    elitism_rate: float,
    selection_type: str,
    initial_population: str,
    write_files: bool = True,
    best_file_path: str = "ga_detailed_best_each_iteration.txt",
    population_file_path: str = "ga_population.txt",
    convergence_file_path: str = "ga_convergence.txt",
) -> _TSolution:

    # Initial population:
    selection = _create_selection(selection_type)
    mutation = problem.mutation_move()
    start_time = time.perf_counter()

    population: list[_TSolution] = []

    if initial_population == ALL_RANDOM:
        pass
    elif initial_population == CW_AND_RANDOM:
        if len(population) < population_size:
            customers = range(1, problem.n)
            population.append(problem.clarke_and_wright_savings(customers))
    else:
        raise ValueError(f"Unknown initial population mode: {initial_population}")

    while len(population) < population_size:
        population.append(problem.random_solution())

    best = min(population, key=lambda solution: solution.objective_value()).copy_solution()
    best_obj = best.objective_value()
    best.running_time_seconds = time.perf_counter() - start_time

    if write_files:
        _write_iteration_files(
            0,
            best,
            population,
            best_file_path,
            population_file_path,
            convergence_file_path,
        )

    print(f"Iteration 0: best = {_format_objective(best_obj)}")
    log.info(f"Iteration 0: best = {_format_objective(best_obj)}")

    elite_count = int(population_size * elitism_rate)


    # Main GA loop.
    for iteration in range(1, max_iterations + 1):
        offspring_population: list[_TSolution] = []
        parent_selection_pool = population.copy()

        # Parent selection + crossover + mutation.
        while len(offspring_population) < population_size:
            if not parent_selection_pool:
                parent_selection_pool = population.copy()

            parent_1 = selection.select(population, parent_selection_pool)

            if not parent_selection_pool:
                parent_selection_pool = [
                    solution
                    for solution in population
                    if solution is not parent_1
                ]

            parent_2 = selection.select(population, parent_selection_pool)

            if random.random() < crossover_probability:
                children = crossover.apply_crossover(
                    [
                        parent_1.copy_solution(),
                        parent_2.copy_solution(),
                    ]
                )
            else:
                children = [
                    parent_1.copy_solution(),
                    parent_2.copy_solution(),
                ]

            for child in children:
                if len(offspring_population) >= population_size:
                    break

                if random.random() < mutation_probability:
                    mutation_move = mutation.random_move(child)
                    if mutation_move is not None:
                        child = mutation_move.apply_move(child)

                offspring_population.append(child)


        # Survival selection: elitism + selection
        combined_population = population + offspring_population
        combined_population.sort(key=lambda solution: solution.objective_value())

        next_population: list[_TSolution] = [
            solution.copy_solution()
            for solution in combined_population[:elite_count]
        ]
        survivor_selection_pool = combined_population[elite_count:].copy()

        while len(next_population) < population_size:
            survivor = selection.select(combined_population, survivor_selection_pool)
            next_population.append(survivor.copy_solution())

        population = next_population

        # Update global best.
        iteration_best = min(population, key=lambda solution: solution.objective_value())
        iteration_best_obj = iteration_best.objective_value()

        if (
            best_obj is None
            or (
                iteration_best_obj is not None
                and iteration_best_obj < best_obj
            )
        ):
            best = iteration_best.copy_solution()
            best_obj = iteration_best_obj
            best.running_time_seconds = time.perf_counter() - start_time

        print(f"Iteration {iteration}: best = {_format_objective(best_obj)}")
        log.info(f"Iteration {iteration}: best = {_format_objective(best_obj)}")

        if write_files:
            _write_iteration_files(
                iteration,
                best,
                population,
                best_file_path,
                population_file_path,
                convergence_file_path,
            )

    return best
