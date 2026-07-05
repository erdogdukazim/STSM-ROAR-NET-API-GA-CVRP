# Kazım Erdoğdu

from __future__ import annotations

import math
import random
from os import makedirs
from pathlib import Path
from typing import Optional, Self, TextIO, final, Protocol

from roar_net_api.operations import (
    SupportsObjectiveValue,
    SupportsLowerBound,
    SupportsApplyMove,
    SupportsCopySolution,
    SupportsEmptySolution,
    SupportsOrderedSolution,
    SupportsRandomMove,
    SupportsRandomSolution,
)

from roar_net_api import algorithms
from roar_net_api.algorithms.ga import (
    ALL_RANDOM as _GA_ALL_RANDOM,
    CW_AND_RANDOM as _GA_CW_AND_RANDOM,
    BINARY_TOURNAMENT_SELECTION,
    ROULETTE_WHEEL_SELECTION,
    InsertMutation,
    SwapMutation,
    NoMutation,
    PMXCrossover as _GAPMXCrossover,
    CXCrossover as _GACXCrossover,
    OXCrossover as _GAOXCrossover,
    NoCrossover as _GANoCrossover,
)
from roar_net_api.operations.mutation_move import SupportsMutationMove


__all__ = [
    "algorithms",
    "BINARY_TOURNAMENT_SELECTION",
    "ROULETTE_WHEEL_SELECTION",
    "InsertMutation",
    "SwapMutation",
    "NoMutation",
    "PMXCrossover",
    "CXCrossover",
    "OXCrossover",
    "NoCrossover",
    "Vehicle",
    "VehicleSplit",
    "Solution",
    "Problem",
    "DEFAULT_VEHICLE_CONSTRUCTION",
    "DEFAULT_CROSSOVER",
    "DEFAULT_MUTATION",
    "DEFAULT_INITIAL_POPULATION",
    "DEFAULT_MAX_ITERATIONS",
    "DEFAULT_POPULATION_SIZE",
    "DEFAULT_CROSSOVER_PROBABILITY",
    "DEFAULT_MUTATION_PROBABILITY",
    "DEFAULT_MUTATION_REPETITION_RATE",
    "DEFAULT_ELITISM_RATE",
    "DEFAULT_SELECTION_TYPE",
    "DEFAULT_RANDOM_INITIAL_SEED",
    "CROSSOVER_FACTORIES",
    "configure_problem",
    "create_crossover",
    "result_header",
    "prepend_result_header",
    "write_solution_file",
    "solve_ga",
]


# ---------------------------------- Vehicle ---------------------------------

@final
class Vehicle:
    """
    - depot is node 0
    - customer nodes are 1, 2, ..., n-1
    - vehicle.tour stores only customers, not the depot
    """

    def __init__(self, tour: Optional[list[int]] = None):
        self.load = 0
        self.distance = 0.0
        self.capacity = problem.capacity
        self.tour: list[int] = []

        if tour is not None:
            for customer in tour:
                self.add_customer(customer)

    def __str__(self) -> str:
        route = " ".join(str(x) for x in self.tour)
        return f"tour=[{route}], distance={self.distance:.2f}, load={self.load}/{self.capacity}; "

    @property
    def is_feasible(self) -> bool:
        return self.load <= self.capacity

    def copy_vehicle(self) -> Self:
        copied = self.__class__()
        copied.tour = self.tour.copy()
        copied.load = self.load
        copied.capacity = self.capacity
        copied.distance = self.distance
        return copied

    def previous_customer(self, current_index : int):
        if current_index <= 0:
            return 0
        return self.tour[current_index - 1]

    def next_customer(self, current_index : int):
        if current_index >= len(self.tour):
            return 0
        return self.tour[current_index]

    def insert_customer(self, customer: int, index: int):
        prev = self.previous_customer(index)
        next = self.next_customer(index)
        self.distance += (problem.dist[prev][customer]
                          + problem.dist[customer][next]
                          - problem.dist[prev][next])
        self.load += problem.demand[customer]
        self.tour.insert(index, customer)


    def add_customer(self, customer: int):
        self.insert_customer(customer, len(self.tour))

    def remove_customer_at_index(self, customer_index: int):
        customer = self.tour[customer_index]
        prev = self.previous_customer(customer_index)
        next = self.next_customer(customer_index)
        self.distance += (problem.dist[prev][next]
                          - problem.dist[prev][customer]
                          - problem.dist[customer][next])
        self.load -= problem.demand[customer]
        self.tour.pop(customer_index)

    def remove_customer(self, customer: int):
        self.remove_customer_at_index(self.tour.index(customer))

    def remove_last_customer(self):
        if self.tour:
            self.remove_customer_at_index(len(self.tour) - 1)

# ---------------------------------- Vehicle Split  --------------------------------

@final
class VehicleSplit:
    STRAIGHT = "straight"
    BELLMAN_SPLIT = "bellman_split"

    def __init__(self, name: str):
        normalized_name = name.lower()

        if normalized_name not in {
            self.STRAIGHT,
            self.BELLMAN_SPLIT,
        }:
            raise ValueError(f"Unknown vehicle construction method: {name}")

        self.name = normalized_name

    def apply(self, giant_tour: list[int]) -> list[Vehicle]:
        if self.name == self.STRAIGHT:
            return self._straight_split(giant_tour)

        if self.name == self.BELLMAN_SPLIT:
            return self._bellman_split(giant_tour)

        raise ValueError(f"Unknown vehicle construction method: {self.name}")

    def _straight_split(self, giant_tour: list[int]) -> list[Vehicle]:
        vehicles: list[Vehicle] = []
        current_vehicle = Vehicle()

        for customer in giant_tour:
            demand = problem.demand[customer]

            if current_vehicle.load + demand > problem.capacity:
                vehicles.append(current_vehicle)
                current_vehicle = Vehicle()

            current_vehicle.add_customer(customer)

        if current_vehicle.tour:
            vehicles.append(current_vehicle)


        return vehicles

    def _bellman_split(self, giant_tour: list[int]) -> list[Vehicle]:
        number_of_customers = len(giant_tour)
        best_cost = [float("inf")] * (number_of_customers + 1)
        predecessor = [-1] * (number_of_customers + 1)
        best_cost[0] = 0.0

        for start in range(number_of_customers):
            if best_cost[start] == float("inf"):
                continue

            route_load = 0
            route_cost = 0.0

            for end in range(start + 1, number_of_customers + 1):
                customer = giant_tour[end - 1]
                route_load += problem.demand[customer]

                if route_load > problem.capacity:
                    break

                if end == start + 1:
                    route_cost = problem.dist[0][customer] + problem.dist[customer][0]
                else:
                    previous_customer = giant_tour[end - 2]
                    route_cost += (
                        - problem.dist[previous_customer][0]
                        + problem.dist[previous_customer][customer]
                        + problem.dist[customer][0]
                    )

                candidate_cost = best_cost[start] + route_cost

                if candidate_cost < best_cost[end]:
                    best_cost[end] = candidate_cost
                    predecessor[end] = start

        routes: list[list[int]] = []
        end = number_of_customers

        while end > 0:
            start = predecessor[end]

            if start < 0:
                raise ValueError("giant_tour cannot be split into feasible routes")

            routes.append(giant_tour[start:end])
            end = start

        routes.reverse()
        vehicles = list()

        for route in routes:
            vehicles.append(Vehicle(route))

        return vehicles


# ---------------------------------- Solution --------------------------------

@final
class Solution(SupportsCopySolution, SupportsObjectiveValue, SupportsLowerBound):
    def __init__(self, problem: Problem, vehicles: list[Vehicle], unassigned: set[int], lb: float):
        self.problem = problem
        self.vehicles = vehicles
        self.unassigned = unassigned
        self.lb = float(lb)
        self.construct_giant_tour()


    def construct_giant_tour(self) -> None:
        self.giant_tour = [customer for vehicle in self.vehicles for customer in vehicle.tour]

    def __str__(self) -> str:
        routes = []
        for ix, vehicle in enumerate(self.vehicles):
            routes.append(f"Vehicle {ix}: {vehicle}")

        giant = " ".join(str(x) for x in self.giant_tour)
        return "\n".join(routes + [f"giant_tour=[{giant}]", f"cost={self.lb:.2f}"])

    @property
    def is_feasible(self) -> bool:
        if self.unassigned:
            return False

        if not all(vehicle.is_feasible for vehicle in self.vehicles):
            return False

        expected = set(range(1, self.problem.n))
        assigned = self.giant_tour

        return (
            len(assigned) == self.problem.number_of_customers
            and set(assigned) == expected
        )

    def to_textio(self, f: TextIO) -> None:
        f.write(f"NAME : {self.problem.name}.sol\n")
        f.write("TYPE : CVRP_SOLUTION\n")
        f.write(f"DIMENSION : {self.problem.n}\n")
        f.write(f"CAPACITY : {self.problem.capacity}\n")
        objective = self.objective_value()
        f.write(f"COST : {objective:.2f}\n" if objective is not None else "COST : None\n")
        if self.problem.lb is not None:
            f.write(f"LB : {self.problem.lb:.2f}\n")
        f.write("ROUTES_SECTION\n")

        for ix, vehicle in enumerate(self.vehicles, start=1):
            if vehicle.tour:
                route = " ".join(str(item + 1) for item in vehicle.tour)
                f.write(
                    f"Vehicle #{ix}: {route}, distance = {vehicle.distance:.2f}, "
                    f"load = {vehicle.load}/{vehicle.capacity}\n"
                )

        f.write("GIANT_TOUR_SECTION\n")
        f.write(" ".join(str(item + 1) for item in self.giant_tour))
        f.write("\nEOF\n")

    def copy_solution(self) -> Self:
        return self.__class__(
            self.problem,
            [vehicle.copy_vehicle() for vehicle in self.vehicles],
            self.unassigned.copy(),
            self.lb,
        )

    def objective_value(self) -> Optional[float]:
        if self.is_feasible:
            return self.lb
        return None

    def lower_bound(self) -> float:
        return self.lb


# ---------------------------------- Mutation ---------------------------------
class _MutationMove(SupportsApplyMove[Solution], Protocol): ...

class _MutationMoveProvider(SupportsRandomMove[Solution, _MutationMove], Protocol): ...



class _VehicleConstructionCrossover:
    def _decode_giant_tour(self, giant_tour: list[int]) -> Solution:
        return self.problem.solution_from_giant_tour(giant_tour)


@final
class PMXCrossover(_VehicleConstructionCrossover, _GAPMXCrossover):
    ...


@final
class CXCrossover(_VehicleConstructionCrossover, _GACXCrossover):
    ...


@final
class OXCrossover(_VehicleConstructionCrossover, _GAOXCrossover):
    ...


@final
class NoCrossover(_GANoCrossover):
    ...


# ---------------------------------- Problem ---------------------------------

@final
class Problem(
    SupportsMutationMove[_MutationMoveProvider],
    SupportsEmptySolution[Solution],
    SupportsRandomSolution[Solution],
    SupportsOrderedSolution[Solution],
):

    # Mutations
    INSERT_MUTATION = "InsertMutation"
    SWAP_MUTATION = "SwapMutation"
    NO_MUTATION = "no_mutation"

    # Initial population modes
    ALL_RANDOM = _GA_ALL_RANDOM
    CW_and_RANDOM = _GA_CW_AND_RANDOM

    # Vehicle construction methods
    STRAIGHT = VehicleSplit.STRAIGHT
    BELLMAN_SPLIT = VehicleSplit.BELLMAN_SPLIT

    # Crossovers
    PMX_CROSSOVER = "PMXCrossover"
    CX_CROSSOVER = "CXCrossover"
    OX_CROSSOVER = "OXCrossover"
    NO_CROSSOVER = "no_crossover"

    n: Optional[int] = None
    number_of_customers: Optional[int] = None
    capacity: Optional[int] = None
    edge_weight_type: Optional[str] = None
    name = "unnamed"
    lb: Optional[float] = None
    demand: Optional[tuple[int, ...]] = None
    dist: Optional[tuple[tuple[float, ...], ...]] = None
    depot: Optional[int] = None

    def __init__(self, capacity: int, dist: tuple[tuple[float, ...], ...], demand: tuple[int, ...],
        name: str, lb: Optional[float] = None):
        self.capacity = int(capacity)
        self.dist = tuple(tuple(float(value) for value in row) for row in dist)
        self.demand = tuple(int(x) for x in demand)
        self.name = name
        self.lb = None if lb is None else float(lb)

        self.n = len(self.dist)              # includes depot
        self.number_of_customers = self.n - 1    # excludes depot
        self.mutation_repetition_rate = 0.10

        assert len(self.demand) == self.n

    def __str__(self) -> str:
        return (
            f"{self.name}: n={self.n}, "
            f"capacity={self.capacity}, "
            f"customers={self.number_of_customers}"
        )

    def route_cost(self, tour: list[int]) -> float:
        if not tour:
            return 0.0

        cost = self.dist[0][tour[0]]

        for ix in range(1, len(tour)):
            cost += self.dist[tour[ix - 1]][tour[ix]]

        cost += self.dist[tour[-1]][0]

        return cost

    def construct_vehicle_by_permutation(self, tour: list[int], load: int, capacity: int, distance: float) -> Vehicle:
        vehicle = Vehicle()
        vehicle.tour = tour.copy()
        vehicle.distance = distance
        vehicle.load = load
        vehicle.capacity = capacity
        return vehicle

    def construct_solution(self, vehicles: list[Vehicle], unassigned: set[int], lb: float) -> Solution:
        s = Solution(self, vehicles, unassigned, lb)
        return s

    def set_construction_nbhood_name(self, name: str):
        self.c_nbhood_name = name

    def set_mutation_name(self, name: str, repetition_rate: float = 0.10):
        self.mutation_name = name
        self.mutation_repetition_rate = float(repetition_rate)

    def set_selection_type(self, name: str) -> None:
        if name not in {
            BINARY_TOURNAMENT_SELECTION,
            ROULETTE_WHEEL_SELECTION,
        }:
            raise ValueError(f"Unknown selection type: {name}")

        self.selection_type = name

    def set_initial_population(self, name: str) -> None:
        if name not in {
            self.ALL_RANDOM,
            self.CW_and_RANDOM,
        }:
            raise ValueError(f"Unknown initial population mode: {name}")

        self.initial_population = name

    def set_vehicle_split_method(self, name: str) -> None:
        self.vehicle_split_method = VehicleSplit(name)

    def mutation_move(self) -> _MutationMoveProvider:
        if self.mutation_name == self.INSERT_MUTATION:
            return InsertMutation(self, self.mutation_repetition_rate)

        if self.mutation_name == self.SWAP_MUTATION:
            return SwapMutation(self, self.mutation_repetition_rate)

        if self.mutation_name == self.NO_MUTATION:
            return NoMutation(self, self.mutation_repetition_rate)

        raise ValueError(f"Unknown mutation: {self.mutation_name}")

    def construct_vehicles_from_giant_tour(self, giant_tour: list[int]) -> list[Vehicle]:
        return self.vehicle_split_method.apply(giant_tour)

    def validate_giant_tour(self, giant_tour: list[int]) -> bool:
        expected = set(range(1, self.n))

        if len(giant_tour) != len(expected) or set(giant_tour) != expected:
            raise ValueError("giant_tour must contain each customer exactly once")

        if any(self.demand[customer] > self.capacity for customer in giant_tour):
            raise ValueError("customer demand exceeds vehicle capacity")

        return True

    def solution_from_giant_tour(self, giant_tour: list[int]) -> Solution:
        vehicles = self.construct_vehicles_from_giant_tour(giant_tour)
        obj = sum(vehicle.distance for vehicle in vehicles)
        return self.construct_solution(vehicles, set(), obj)

    def solution_from_routes(self, routes: list[list[int]]) -> Solution:
        vehicles = list()
        for route in routes:
            vehicles.append(Vehicle(route))

        obj = sum(vehicle.distance for vehicle in vehicles)

        return self.construct_solution(vehicles, set(), obj)


    @classmethod
    def file_reader(cls, filePath: str) -> Self:
        with open(filePath, encoding="utf-8") as f:
            return cls.from_textio(f)

    @classmethod
    def from_textio(cls, f: TextIO) -> Self:
        """
        Create a CVRP problem from a TSPLIB-style CVRP file.

        Supported format:
        - TYPE : CVRP
        - EDGE_WEIGHT_TYPE : EUC_2D
        - NODE_COORD_SECTION
        - DEMAND_SECTION
        - DEPOT_SECTION with depot 1
        """

        s = f.readline().strip()

        while s != "NODE_COORD_SECTION" and s != "":
            line = s.split(":", 1)

            if len(line) == 2:
                k = line[0].strip()
                v = line[1].strip()

                if k == "NAME":
                    cls.name = v
                elif k == "COMMENT":
                    try:
                        cls.lb = float(v)
                    except ValueError:
                        cls.lb = None
                elif k == "DIMENSION":
                    cls.n = int(v)
                elif k == "EDGE_WEIGHT_TYPE":
                    cls.edge_weight_type = v
                elif k == "CAPACITY":
                    cls.capacity = int(v)

            s = f.readline().strip()

        if cls.n is None:
            raise Exception("DIMENSION is missing")

        if cls.capacity is None:
            raise Exception("CAPACITY is missing")

        if cls.edge_weight_type != "EUC_2D":
            raise Exception(f"Instance format {cls.edge_weight_type} not supported")

        if s != "NODE_COORD_SECTION":
            raise Exception("NODE_COORD_SECTION is missing")

        coords_raw: list[tuple[float, float, float]] = []

        for _ in range(cls.n):
            parts = f.readline().split()

            if len(parts) < 3:
                raise Exception("Invalid NODE_COORD_SECTION")

            coords_raw.append((float(parts[0]), float(parts[1]), float(parts[2])))

        coords_raw = sorted(coords_raw, key=lambda row: row[0])

        for ix, row in enumerate(coords_raw, start=1):
            if int(row[0]) != ix:
                raise Exception("Invalid node numbering")

        s = f.readline().strip()

        while s != "DEMAND_SECTION" and s != "":
            s = f.readline().strip()

        if s != "DEMAND_SECTION":
            raise Exception("DEMAND_SECTION is missing")

        demand_raw: list[tuple[int, int]] = []

        for _ in range(cls.n):
            parts = f.readline().split()

            if len(parts) < 2:
                raise Exception("Invalid DEMAND_SECTION")

            demand_raw.append((int(parts[0]), int(parts[1])))

        demand_raw = sorted(demand_raw, key=lambda row: row[0])

        for ix, row in enumerate(demand_raw, start=1):
            if row[0] != ix:
                raise Exception("Invalid demand numbering")

        cls.demand = tuple(int(row[1]) for row in demand_raw)

        s = f.readline().strip()

        while s != "DEPOT_SECTION" and s != "":
            s = f.readline().strip()

        if s != "DEPOT_SECTION":
            raise Exception("DEPOT_SECTION is missing")

        cls.depot = None

        while True:
            s = f.readline().strip()

            if s in {"-1", "EOF", ""}:
                break

            cls.depot = int(s)

        if cls.depot != 1:
            raise Exception("Only depot node 1 is supported")

        if cls.demand[0] != 0:
            raise Exception("Depot demand must be 0")

        cls.dist: list[tuple[float, ...]] = []

        for i in range(cls.n):
            row: list[float] = []

            for j in range(cls.n):
                dx = coords_raw[i][1] - coords_raw[j][1]
                dy = coords_raw[i][2] - coords_raw[j][2]

                row.append(math.sqrt(dx * dx + dy * dy))

            cls.dist.append(tuple(row))

        return cls(cls.capacity, tuple(cls.dist), cls.demand, cls.name, cls.lb)

    # Constructing solutions
    def empty_solution(self) -> Solution:
        return Solution(self, [], set(range(1, self.n)), 0.0)

    def random_solution(self) -> Solution:
        customers = list(range(1, self.n))
        random.shuffle(customers)
        return self.solution_from_giant_tour(customers)

    def ordered_solution(self) -> Solution:
        customers = list(range(1, self.n))
        return self.solution_from_giant_tour(customers)


#------------------------------------------ MAIN VRP ------------------------------------------

# DEFAULT PARAMETER VALUES

DEFAULT_VEHICLE_CONSTRUCTION = Problem.BELLMAN_SPLIT
DEFAULT_CROSSOVER = Problem.OX_CROSSOVER
DEFAULT_MUTATION = Problem.SWAP_MUTATION
DEFAULT_INITIAL_POPULATION = Problem.ALL_RANDOM
DEFAULT_MAX_ITERATIONS = 100
DEFAULT_POPULATION_SIZE = 100
DEFAULT_CROSSOVER_PROBABILITY = 0.75
DEFAULT_MUTATION_PROBABILITY = 0.05
DEFAULT_MUTATION_REPETITION_RATE = 0.1
DEFAULT_ELITISM_RATE = 0.2
DEFAULT_SELECTION_TYPE = BINARY_TOURNAMENT_SELECTION
DEFAULT_RANDOM_INITIAL_SEED = 0

CROSSOVER_FACTORIES = {
    Problem.PMX_CROSSOVER: PMXCrossover,
    Problem.CX_CROSSOVER: CXCrossover,
    Problem.OX_CROSSOVER: OXCrossover,
    Problem.NO_CROSSOVER: NoCrossover,
}

def configure_problem(
    problem: Problem,
    mutation_name: str = DEFAULT_MUTATION,
    vehicle_construction: str = DEFAULT_VEHICLE_CONSTRUCTION,
    mutation_repetition_rate: float = 0.10,
    selection_type: str = DEFAULT_SELECTION_TYPE,
    initial_population: str = DEFAULT_INITIAL_POPULATION,
) -> Problem:

    globals()["problem"] = problem
    problem.set_mutation_name(mutation_name, mutation_repetition_rate)
    problem.set_selection_type(selection_type)
    problem.set_initial_population(initial_population)
    problem.set_vehicle_split_method(vehicle_construction)
    return problem


def create_crossover(problem: Problem, name: str = DEFAULT_CROSSOVER):
    try:
        factory = CROSSOVER_FACTORIES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown crossover: {name}") from exc

    return factory(problem)


def result_header(
    problem: Problem,
    cost: float | None,
    crossover_name: str = DEFAULT_CROSSOVER,
    mutation_name: str = DEFAULT_MUTATION,
    crossover_probability: float = DEFAULT_CROSSOVER_PROBABILITY,
    mutation_probability: float = DEFAULT_MUTATION_PROBABILITY,
    population_size: int = DEFAULT_POPULATION_SIZE,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    elitism_rate: float = DEFAULT_ELITISM_RATE,
    selection_type: str = DEFAULT_SELECTION_TYPE,
    initial_population: str = DEFAULT_INITIAL_POPULATION,
    vehicle_construction: str = DEFAULT_VEHICLE_CONSTRUCTION,
    running_time_seconds: Optional[float] = None,
    include_running_time: bool = False,
    random_initial_seed: Optional[int] = None,
) -> str:
    formatted_cost = f"{cost:.2f}" if cost is not None else "None"
    running_time_line = (
        f"RUNNING TIME: {running_time_seconds:.2f} seconds"
        if running_time_seconds is not None
        else "RUNNING TIME: None"
    )
    lines = [
        f"NAME : {problem.name}.sol",
        "TYPE : CVRP_SOLUTION",
        f"DIMENSION : {problem.n}",
        f"CAPACITY : {problem.capacity}",
        f"COST : {formatted_cost}",
    ]

    if problem.lb is not None:
        lines.append(f"LB : {problem.lb:.2f}")

    lines.extend([
        f"CROSSOVER: {crossover_name}",
        f"MUTATION: {mutation_name}",
        f"CROSSOVER RATE: {crossover_probability}",
        f"MUTATION RATE: {mutation_probability}",
        f"POPULATION SIZE: {population_size}",
        f"ITERATION NUMBER: {max_iterations}",
        f"ELITISM RATE: {elitism_rate}",
        f"SELECTION TYPE: {selection_type}",
        f"INITIAL POPULATION: {initial_population}",
        f"VEHICLE CONSTRUCTION: {vehicle_construction}",
    ])

    if random_initial_seed is not None:
        lines.append(f"RANDOM INITIAL SEED: {random_initial_seed}")

    if include_running_time:
        lines.append(running_time_line)

    lines.extend(["", ""])

    return "\n".join(lines)


def prepend_result_header(path: str, header: str) -> None:
    try:
        with open(path, encoding="utf-8") as f:
            existing_text = f.read()
    except FileNotFoundError:
        existing_text = ""

    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(existing_text)


def remove_repeated_problem_header(path: str) -> None:
    skipped_prefixes = (
        "NAME :",
        "TYPE :",
        "DIMENSION :",
        "CAPACITY :",
    )

    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return

    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            if line.startswith(skipped_prefixes):
                continue

            f.write(line)


def _ensure_parent_directory(path: str) -> None:
    parent = Path(path).parent

    if str(parent) not in {"", "."}:
        parent.mkdir(parents=True, exist_ok=True)


def write_solution_file(
    file_path: str,
    solution: Solution,
    crossover_name: str = DEFAULT_CROSSOVER,
    mutation_name: str = DEFAULT_MUTATION,
    crossover_probability: float = DEFAULT_CROSSOVER_PROBABILITY,
    mutation_probability: float = DEFAULT_MUTATION_PROBABILITY,
    population_size: int = DEFAULT_POPULATION_SIZE,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    elitism_rate: float = DEFAULT_ELITISM_RATE,
    selection_type: str = DEFAULT_SELECTION_TYPE,
    initial_population: str = DEFAULT_INITIAL_POPULATION,
    vehicle_construction: str = DEFAULT_VEHICLE_CONSTRUCTION,
    running_time_seconds: Optional[float] = None,
    random_initial_seed: Optional[int] = None,
) -> None:
    _ensure_parent_directory(file_path)
    if running_time_seconds is None:
        running_time_seconds = getattr(solution, "running_time_seconds", None)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(
            result_header(
                solution.problem,
                solution.objective_value(),
                crossover_name=crossover_name,
                mutation_name=mutation_name,
                crossover_probability=crossover_probability,
                mutation_probability=mutation_probability,
                population_size=population_size,
                max_iterations=max_iterations,
                elitism_rate=elitism_rate,
                selection_type=selection_type,
                initial_population=initial_population,
                vehicle_construction=vehicle_construction,
                running_time_seconds=running_time_seconds,
                include_running_time=True,
                random_initial_seed=random_initial_seed,
            )
        )
        f.write("ROUTES_SECTION\n")

        for ix, vehicle in enumerate(solution.vehicles, start=1):
            if vehicle.tour:
                route = " ".join(str(item + 1) for item in vehicle.tour)
                f.write(
                    f"Vehicle #{ix}: {route}, distance = {vehicle.distance:.2f}, "
                    f"load = {vehicle.load}/{vehicle.capacity}\n"
                )

        f.write("GIANT_TOUR_SECTION\n")
        f.write(" ".join(str(item + 1) for item in solution.giant_tour))
        f.write("\nEOF\n")


def solve_ga(
    problem: Problem,
    vehicle_construction: str = DEFAULT_VEHICLE_CONSTRUCTION,
    crossover_name: str = DEFAULT_CROSSOVER,
    mutation_name: str = DEFAULT_MUTATION,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    population_size: int = DEFAULT_POPULATION_SIZE,
    crossover_probability: float = DEFAULT_CROSSOVER_PROBABILITY,
    mutation_probability: float = DEFAULT_MUTATION_PROBABILITY,
    elitism_rate: float = DEFAULT_ELITISM_RATE,
    selection_type: str = DEFAULT_SELECTION_TYPE,
    initial_population: str = DEFAULT_INITIAL_POPULATION,
    mutation_repetition_rate: float = DEFAULT_MUTATION_REPETITION_RATE,
    random_initial_seed: Optional[int] = DEFAULT_RANDOM_INITIAL_SEED,
    write_files: bool = False,
    best_file_path: str = "ga_detailed_best_each_iteration.txt",
    population_file_path: str = "ga_population.txt",
    convergence_file_path: str = "ga_convergence.txt",
) -> Solution:

    configure_problem(
        problem,
        mutation_name=mutation_name,
        vehicle_construction=vehicle_construction,
        mutation_repetition_rate=mutation_repetition_rate,
        selection_type=selection_type,
        initial_population=initial_population,
    )

    crossover = create_crossover(problem, crossover_name)

    if write_files:
        _ensure_parent_directory(best_file_path)
        _ensure_parent_directory(population_file_path)
        _ensure_parent_directory(convergence_file_path)

    if random_initial_seed is not None:
        random.seed(random_initial_seed)

    solution = algorithms.ga(
        problem,
        crossover=crossover,
        max_iterations=max_iterations,
        population_size=population_size,
        crossover_probability=crossover_probability,
        mutation_probability=mutation_probability,
        elitism_rate=elitism_rate,
        selection_type=selection_type,
        initial_population=initial_population,
        write_files=write_files,
        best_file_path=best_file_path,
        population_file_path=population_file_path,
        convergence_file_path=convergence_file_path,
    )

    if write_files:
        remove_repeated_problem_header(best_file_path)
        header = result_header(
            problem,
            solution.objective_value(),
            crossover_name=crossover_name,
            mutation_name=mutation_name,
            crossover_probability=crossover_probability,
            mutation_probability=mutation_probability,
            population_size=population_size,
            max_iterations=max_iterations,
            elitism_rate=elitism_rate,
            selection_type=selection_type,
            initial_population=initial_population,
            vehicle_construction=vehicle_construction,
            random_initial_seed=random_initial_seed,
            include_running_time=False,
        )
        prepend_result_header(best_file_path, header)
        prepend_result_header(population_file_path, header)
        prepend_result_header(convergence_file_path, header)

    return solution

from roar_net_api.algorithms.ga import InsertMove, SwapMove

if __name__ == "__main__":
    example_dir = Path(__file__).resolve().parent
    instance_name = "CMT1"
    problem_file_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "roar_net_api"
        / "problem_instances"
        / f"{instance_name}.vrp"
    )
    results_folder_path = example_dir / f"Results_{instance_name}"
    makedirs(results_folder_path, exist_ok=True)

    problem = Problem.file_reader(str(problem_file_path))

    solution = solve_ga(
        problem,
        vehicle_construction=DEFAULT_VEHICLE_CONSTRUCTION,
        crossover_name=DEFAULT_CROSSOVER,
        mutation_name=DEFAULT_MUTATION,
        max_iterations=DEFAULT_MAX_ITERATIONS,
        population_size=DEFAULT_POPULATION_SIZE,
        crossover_probability=DEFAULT_CROSSOVER_PROBABILITY,
        mutation_probability=DEFAULT_MUTATION_PROBABILITY,
        elitism_rate=DEFAULT_ELITISM_RATE,
        selection_type=DEFAULT_SELECTION_TYPE,
        initial_population=DEFAULT_INITIAL_POPULATION,
        random_initial_seed=DEFAULT_RANDOM_INITIAL_SEED,
        write_files=True,
        best_file_path=f"{results_folder_path}/ga_detailed_best_each_iteration.txt",
        population_file_path=f"{results_folder_path}/ga_population.txt",
        convergence_file_path=f"{results_folder_path}/ga_convergence.txt",
    )

    write_solution_file(
        f"{results_folder_path}/ga_best.txt",
        solution,
        crossover_name=DEFAULT_CROSSOVER,
        mutation_name=DEFAULT_MUTATION,
        crossover_probability=DEFAULT_CROSSOVER_PROBABILITY,
        mutation_probability=DEFAULT_MUTATION_PROBABILITY,
        population_size=DEFAULT_POPULATION_SIZE,
        max_iterations=DEFAULT_MAX_ITERATIONS,
        elitism_rate=DEFAULT_ELITISM_RATE,
        selection_type=DEFAULT_SELECTION_TYPE,
        initial_population=DEFAULT_INITIAL_POPULATION,
        vehicle_construction=DEFAULT_VEHICLE_CONSTRUCTION,
        random_initial_seed=DEFAULT_RANDOM_INITIAL_SEED,
    )

