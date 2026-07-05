---
title: "ROAR-NET API CVRP Genetic Algorithm Extension"
subtitle: "Specification and Implementation Guide"
author: "Prepared from the supplied Python implementation"
date: "30 June 2026"
lang: en
---

# ROAR-NET API CVRP Genetic Algorithm Components Extension

## About this document

This document specifies a Python implementation of a Capacitated Vehicle Routing Problem (CVRP) model and a configurable Genetic Algorithm (GA) built on ROAR-NET-style abstractions.

The structure follows the style of the ROAR-NET API Specification: types and operations are documented separately, and operation entries use recurring sections such as **Signature**, **Description**, **Pre-requisites**, **Use cases**, and **See also**.

The implementation is divided into four conceptual layers:

1. generic protocol types (`Problem`, `Solution`, and `Move`),
2. operation protocols such as `random_solution`, `copy_solution`, and `apply_move`,
3. generic GA components such as selection, crossover, mutation, and the generational loop,
4. a CVRP model containing `Vehicle`, `VehicleSplit`, `Problem`, and `Solution`.

> **Scope note:** This specification reflects the supplied source snapshot. The final section records code-state constraints and inconsistencies that should be checked against the active development branch.

## Reference basis

- ROAR-NET API Specification: <https://roar-net.github.io/roar-net-api-spec/>
- ROAR-NET API Specification source: <https://github.com/roar-net/roar-net-api-spec>
- ROAR-NET Python implementation source referenced by the file headers: <https://github.com/roar-net/roar-net-api-py>

# Conceptualisation

## Separation of concerns

The implementation keeps the optimisation algorithm and the problem model conceptually separate.

The generic GA receives a problem object through protocol requirements rather than through a concrete CVRP class. The GA assumes that the problem can generate random solutions, provide a mutation operator, and work with solution objects that can be copied and evaluated.

The CVRP model is responsible for:

- reading a problem instance,
- representing routes and vehicles,
- checking capacity and assignment feasibility,
- encoding and decoding giant tours,
- computing route distances,
- producing initial solutions,
- writing result files.

The GA is responsible for:

- creating the initial population,
- choosing parents,
- applying crossover probabilistically,
- applying mutation probabilistically,
- performing elitist survival selection,
- tracking the global best solution,
- optionally writing iteration-level output files.

## Supported optimisation setting

The supplied implementation targets a single-objective minimisation problem. The objective is total travel distance across all vehicle routes.

The principal decision representation is a **giant tour**, which is a permutation of all customer indices. A vehicle-construction procedure splits that permutation into capacity-feasible routes.

The implementation supports:

- permutation-based candidate solutions,
- CVRP capacity constraints,
- Euclidean distance matrices generated from TSPLIB-style coordinates,
- straight and Bellman-based route splitting,
- PMX, CX, OX, and no-crossover modes,
- insert, swap, and no-mutation modes,
- binary tournament and roulette-wheel selection,
- all-random population initialisation,
- an optional Clarke-Wright-plus-random initialisation mode at the generic GA level,
- elitist generational replacement,
- reproducible pseudo-random execution through an initial seed.

# Package and file structure

## Generic type protocols

| File | Main protocol | Purpose |
|---|---|---|
| `problem.py` | `Problem` | Declares solution-construction capabilities required from a problem model. |
| `solution.py` | `Solution` | Declares copying, lower-bound, and objective-value capabilities. |
| `move.py` | `Move` | Combines move application and incremental evaluation protocols. |

## Operation protocols

| File | Protocol | Method |
|---|---|---|
| `empty_solution.py` | `SupportsEmptySolution` | `empty_solution()` |
| `random_solution.py` | `SupportsRandomSolution` | `random_solution()` |
| `ordered_solution.py` | `SupportsOrderedSolution` | `ordered_solution()` |
| `copy_solution.py` | `SupportsCopySolution` | `copy_solution()` |
| `lower_bound.py` | `SupportsLowerBound` | `lower_bound()` |
| `objective_value.py` | `SupportsObjectiveValue` | `objective_value()` |
| `apply_move.py` | `SupportsApplyMove` | `apply_move(solution)` |
| `moves.py` | `SupportsMoves` | `moves(solution)` |
| `random_move.py` | `SupportsRandomMove` | `random_move(solution)` |
| `random_moves_without_replacement.py` | `SupportsRandomMovesWithoutReplacement` | `random_moves_without_replacement(solution)` |
| `lower_bound_increment.py` | `SupportsLowerBoundIncrement` | `lower_bound_increment(solution)` |
| `objective_value_increment.py` | `SupportsObjectiveValueIncrement` | `objective_value_increment(solution)` |
| `apply_crossover.py` | `SupportsApplyCrossover` | `apply_crossover(parents)` |
| `mutation_move.py` | `SupportsMutationMove` | `mutation_move()` |

## Algorithm and model files

| File | Responsibility |
|---|---|
| `ga.py` | Generic GA loop, selection operators, crossover operators, mutation operators, move implementations, and iteration output. |
| `vrp.py` | CVRP problem reader, vehicle and solution representation, giant-tour decoding, configuration defaults, result output, and the GA wrapper. |

# Types

# Generic Problem

## Signature

```text
Problem[Solution]
```

## Python protocol

```python
class Problem(
    SupportsEmptySolution[Solution],
    SupportsRandomSolution[Solution],
    SupportsOrderedSolution[Solution],
    Protocol,
): ...
```

## Description

The generic `Problem` protocol declares the solution-construction operations expected from a compatible optimisation problem.

A concrete problem instance stores instance-specific data. In the CVRP model this includes capacity, customer demands, a distance matrix, instance name, node count, and an optional known lower bound.

## Use cases

The generic GA calls `random_solution()` to populate its initial population. Other algorithms can also use `empty_solution()` or `ordered_solution()` when they require deterministic or constructive starting points.

## See also

[CVRP Problem](#cvrp-problem), [Empty solution](#empty-solution), [Random solution](#random-solution), [Ordered solution](#ordered-solution).

# Generic Solution

## Signature

```text
Solution
```

## Python protocol

```python
class Solution(
    SupportsCopySolution,
    SupportsLowerBound,
    SupportsObjectiveValue,
    Protocol,
): ...
```

## Description

A `Solution` is a candidate point in the decision space. It must support independent copying and numerical evaluation.

The CVRP implementation stores both a phenotype-like route representation (`vehicles`) and a permutation representation (`giant_tour`). It also stores an incremental objective field named `lb`.

## Use cases

GA operators copy parents before variation, evaluate individuals during selection, and preserve the best solution independently of later population changes.

## See also

[CVRP Solution](#cvrp-solution), [Copy solution](#copy-solution), [Objective value](#objective-value), [Lower bound](#lower-bound).

# Generic Move

## Signature

```text
Move[Solution]
```

## Python protocol

```python
class Move(
    SupportsApplyMove[Solution],
    SupportsLowerBoundIncrement[Solution],
    SupportsObjectiveValueIncrement[Solution],
    Protocol,
): ...
```

## Description

A `Move` identifies a transformation between neighbouring solutions. The protocol combines:

- application of the move,
- calculation of the lower-bound increment,
- calculation of the objective-value increment.

The concrete GA currently provides `InsertMove` and `SwapMove`. These moves calculate objective-value increments before changing the solution.

## See also

[Insert move](#insert-move), [Swap move](#swap-move), [Apply move](#apply-move), [Objective-value increment](#objective-value-increment).

# Vehicle

## Signature

```text
Vehicle(tour: list[int] = [])
```

## Description

`Vehicle` represents one CVRP route. The depot is represented by node `0`, but the depot is not stored in `vehicle.tour`. Customer nodes use indices `1` through `n - 1`.

The principal fields are:

| Field | Type | Meaning |
|---|---|---|
| `tour` | `list[int]` | Ordered customer indices assigned to the vehicle. |
| `load` | `int` | Sum of customer demands on the route. |
| `capacity` | `int` | Maximum allowed load. |
| `distance` | `float` | Depot-to-depot route distance. |

## Feasibility

```text
vehicle.is_feasible = (vehicle.load <= vehicle.capacity)
```

Vehicle feasibility checks only the capacity constraint. Global customer assignment is checked by `Solution.is_feasible`.

## Route boundary helpers

```python
previous_customer(current_index)
next_customer(current_index)
```

Both methods return depot index `0` at a route boundary. This allows insertion and removal delta formulas to use the same structure for internal and boundary positions.

## Insert customer

### Signature

```text
insert_customer(customer, index) : None
```

### Description

Inserts a customer at a specified route position and updates distance and load incrementally.

For previous node `p`, inserted customer `c`, and next node `q`, the distance increment is:

```text
delta = d[p][c] + d[c][q] - d[p][q]
```

## Remove customer

### Signature

```text
remove_customer_at_index(customer_index) : None
```

### Description

Removes the selected customer and updates distance and load incrementally.

For removed customer `c` between `p` and `q`, the distance increment is:

```text
delta = d[p][q] - d[p][c] - d[c][q]
```

## Other operations

```text
add_customer(customer)
remove_customer(customer)
remove_last_customer()
copy_vehicle()
```

## See also

[Vehicle split](#vehicle-split), [CVRP Solution](#cvrp-solution), [Insert move](#insert-move), [Swap move](#swap-move).

# Vehicle Split

## Signature

```text
VehicleSplit(name)
```

## Description

`VehicleSplit` decodes a giant tour into a list of `Vehicle` routes. Two methods are supported:

```text
straight
bellman_split
```

## Straight split

### Signature

```text
_straight_split(giant_tour) : list[Vehicle]
```

### Description

Customers are visited in giant-tour order. A customer is appended to the current route when capacity allows it. Otherwise, the current route is closed and a new route is started.

The procedure is greedy with respect to giant-tour order. It does not reconsider earlier route boundaries.

### Complexity

The procedure scans the giant tour once and therefore has linear construction complexity in the number of customers, excluding constant-time distance updates.

## Bellman split

### Signature

```text
_bellman_split(giant_tour) : list[Vehicle]
```

### Description

The Bellman split applies dynamic programming to find the minimum-cost capacity-feasible partition of a fixed giant tour.

Let position `j` represent the prefix containing the first `j` customers. The implementation stores:

```text
best_cost[j]   = best known cost for splitting prefix 0..j
predecessor[j] = prefix position preceding the final route
```

For every feasible segment from `start` to `end`, it evaluates:

```text
candidate_cost = best_cost[start] + route_cost(start, end)
```

When the candidate improves `best_cost[end]`, the predecessor is updated. Routes are reconstructed by following predecessor indices backwards from the end of the giant tour.

### Failure condition

If no predecessor exists for a required position, the method raises:

```text
ValueError("giant_tour cannot be split into feasible routes")
```

### Complexity

The nested segment search is quadratic in the number of customers in the worst case.

## See also

[Giant-tour representation](#giant-tour-representation), [CVRP Problem](#cvrp-problem), [Crossover decoding](#crossover-decoding).

# CVRP Problem

## Signature

```text
Problem(capacity, dist, demand, name, lb=None)
```

## Description

The concrete CVRP `Problem` stores the data required to generate, decode, evaluate, and serialise CVRP solutions.

## Core fields

| Field | Meaning |
|---|---|
| `capacity` | Vehicle capacity. |
| `dist` | Square distance matrix including depot index `0`. |
| `demand` | Demand tuple including depot demand `0`. |
| `name` | Instance name. |
| `lb` | Optional known lower bound or benchmark value. |
| `n` | Number of nodes including the depot. |
| `number_of_customers` | `n - 1`. |
| `mutation_repetition_rate` | Fraction used to calculate mutation repetitions. |

## Configuration fields

The configuration wrapper assigns:

- `c_nbhood_name`,
- `mutation_name`,
- `mutation_repetition_rate`,
- `selection_type`,
- `initial_population`,
- `vehicle_split_method`.

## Route cost

### Signature

```text
route_cost(tour) : float
```

### Description

Returns the depot-to-depot distance of one route.

For route `[c1, c2, ..., ck]`:

```text
cost = d[0][c1]
     + sum(d[ci][c(i+1)])
     + d[ck][0]
```

An empty tour has cost `0.0`.

## Giant-tour validation

### Signature

```text
validate_giant_tour(giant_tour) : bool
```

### Pre-requisites

The giant tour must:

- contain every customer exactly once,
- contain no depot,
- have the expected number of elements,
- contain no customer whose individual demand exceeds vehicle capacity.

The method raises `ValueError` when these conditions are violated.

## Solution construction

```text
construct_solution(vehicles, unassigned, lb) : Solution
solution_from_giant_tour(giant_tour) : Solution
solution_from_routes(routes) : Solution
construct_vehicles_from_giant_tour(giant_tour) : list[Vehicle]
```

`solution_from_giant_tour` decodes the permutation with the active split method and sets the objective field to the sum of route distances.

## Mutation provider

### Signature

```text
mutation_move() : mutation provider
```

### Description

Returns one of:

- `InsertMutation`,
- `SwapMutation`,
- `NoMutation`.

The selected class is determined by `mutation_name`.

## See also

[CVRP Solution](#cvrp-solution), [Vehicle](#vehicle), [Vehicle Split](#vehicle-split), [Mutation](#mutation).

# CVRP Solution

## Signature

```text
Solution(problem, vehicles, unassigned, lb)
```

## Description

The CVRP `Solution` stores a complete route set and a derived giant tour.

## Fields

| Field | Meaning |
|---|---|
| `problem` | Reference to the CVRP instance. |
| `vehicles` | Ordered list of route objects. |
| `unassigned` | Customer indices not currently assigned. |
| `lb` | Stored total route distance used as the objective value. |
| `giant_tour` | Concatenation of all vehicle tours. |

## Giant-tour representation

### Signature

```text
construct_giant_tour() : None
```

### Description

The giant tour is constructed by concatenating routes in vehicle-list order:

```python
giant_tour = [
    customer
    for vehicle in vehicles
    for customer in vehicle.tour
]
```

This representation enables permutation crossovers while preserving a route-based phenotype.

## Feasibility

### Signature

```text
solution.is_feasible : bool
```

### Conditions

A solution is feasible when:

1. `unassigned` is empty,
2. every vehicle respects capacity,
3. the giant tour has exactly `number_of_customers` elements,
4. the giant tour contains exactly the customer set `{1, ..., n - 1}`.

The length check prevents duplicated customers from being accepted when the set of assigned customers is otherwise correct.

## Objective value

### Signature

```text
objective_value() : Optional[float]
```

### Description

Returns `lb` when the solution is feasible; otherwise returns `None`.

## Lower bound

### Signature

```text
lower_bound() : float
```

### Description

Returns the stored `lb` field. In this implementation the same field is used as the current total route distance.

## Copying

### Signature

```text
copy_solution() : Solution
```

### Description

Produces a new solution with copied vehicles, a copied unassigned set, and the same problem reference and objective value.

## Serialisation

### Signature

```text
to_textio(f) : None
```

### Description

Writes a TSPLIB-inspired solution format containing instance metadata, total cost, route records, and the giant tour.

## See also

[Objective value](#objective-value), [Lower bound](#lower-bound), [Copy solution](#copy-solution), [Output formats](#output-formats).

# Operations

# Empty solution

## Signature

```text
empty_solution() : Solution
```

## Protocol

```python
class SupportsEmptySolution(Protocol[Solution]):
    def empty_solution(self) -> Solution: ...
```

## Description

Produces a solution containing no routes and marks all customers as unassigned.

The CVRP implementation uses:

```text
vehicles   = []
unassigned = {1, ..., n - 1}
lb         = 0.0
```

## Use cases

This operation is useful for constructive algorithms that build a solution incrementally. The current GA initialises from random complete solutions instead.

## See also

[Random solution](#random-solution), [Ordered solution](#ordered-solution), [CVRP Solution](#cvrp-solution).

# Random solution

## Signature

```text
random_solution() : Solution
```

## Protocol

```python
class SupportsRandomSolution(Protocol[Solution]):
    def random_solution(self) -> Solution: ...
```

## Description

Creates a list of all customers, shuffles the list with Python's global pseudo-random generator, and decodes the resulting giant tour.

## Use cases

The generic GA repeatedly calls this operation until the requested population size is reached.

## Reproducibility

`solve_ga` calls `random.seed(random_initial_seed)` when the seed is not `None`. Therefore random initial solutions, parent sampling, crossover points, and mutation choices share the same random stream.

## See also

[Initial population](#initial-population), [GA execution](#ga-execution), [Vehicle Split](#vehicle-split).

# Ordered solution

## Signature

```text
ordered_solution() : Solution
```

## Protocol

```python
class SupportsOrderedSolution(Protocol[Solution]):
    def ordered_solution(self) -> Solution: ...
```

## Description

Constructs the deterministic giant tour:

```text
[1, 2, ..., n - 1]
```

and decodes it with the active vehicle split method.

## Use cases

Useful for deterministic tests, debugging, and algorithms that require a reproducible baseline solution.

# Copy solution

## Signature

```text
copy_solution() : Solution
```

## Protocol

```python
class SupportsCopySolution(Protocol):
    def copy_solution(self) -> Self: ...
```

## Description

Returns an independent candidate solution that can be changed without modifying the original.

## Pre-requisites

Nested mutable structures must also be copied. The CVRP implementation copies each vehicle and the unassigned set, while retaining a shared immutable problem reference.

## Use cases

The GA copies:

- the initial best solution,
- selected parents before crossover,
- parents when crossover is skipped,
- elite survivors,
- selected non-elite survivors,
- a newly discovered global best.

# Lower bound

## Signature

```text
lower_bound() : Optional[int | float]
```

## Protocol

```python
class SupportsLowerBound(Protocol):
    def lower_bound(self) -> Optional[Union[int, float]]: ...
```

## Description

Produces a lower-bound value associated with a candidate solution. In the supplied CVRP solution, the method returns `lb`, which is also used as the current total route distance.

## Implementation note

The field name follows the generic API terminology, but its operational role in the GA is the objective value accumulator.

# Objective value

## Signature

```text
objective_value() : Optional[int | float]
```

## Protocol

```python
class SupportsObjectiveValue(Protocol):
    def objective_value(self) -> Optional[Union[int, float]]: ...
```

## Description

Returns the value to be minimised. The CVRP implementation returns total route distance only for feasible solutions.

## Pre-requisites

Selection and sorting in the current GA assume that population members provide comparable numerical objective values. Therefore the active initialisation, crossover, and mutation path must preserve feasibility.

## Use cases

Objective values are used in:

- initial best selection,
- binary tournament selection,
- roulette-wheel weight calculation,
- population sorting,
- global-best updates,
- convergence and result files.

# Apply move

## Signature

```text
apply_move(solution) : Solution
```

## Protocol

```python
class SupportsApplyMove(Protocol[Solution]):
    def apply_move(self, solution: Solution) -> Solution: ...
```

## Description

Applies a previously defined move to a solution. Both concrete move classes modify the supplied solution in place and return the same solution reference.

## Pre-requisites

The move indices must be valid for the current state of the solution. A move generated for one state should not be applied after unrelated modifications have invalidated its positions.

## Use cases

The mutation providers generate a feasible move and apply it immediately.

# Moves

## Signature

```text
moves(solution) : Iterable[Move]
```

## Protocol

```python
class SupportsMoves(Protocol[Solution, Move]):
    def moves(self, solution: Solution) -> Iterable[Move]: ...
```

## Description

Declares exhaustive move generation for a solution.

## Implementation status

The protocol is present in the supplied operation layer, but the current GA mutation path uses random move generation rather than exhaustive enumeration.

# Random move

## Signature

```text
random_move(solution) : Optional[Move]
```

## Protocol

```python
class SupportsRandomMove(Protocol[Solution, Move]):
    def random_move(self, solution: Solution) -> Optional[Move]: ...
```

## Description

Returns a random move provider or `None` when no move is available.

The base mutation object validates that the solution belongs to the configured problem and that at least one vehicle exists. It then returns itself as an object whose `apply_move` method performs one or more random concrete moves.

# Random moves without replacement

## Signature

```text
random_moves_without_replacement(solution) : Iterable[Move]
```

## Protocol

```python
class SupportsRandomMovesWithoutReplacement(Protocol[Solution, Move]):
    def random_moves_without_replacement(self, solution: Solution) -> Iterable[Move]: ...
```

## Description

Declares random enumeration of moves without returning the same move more than once.

## Implementation status

The protocol is supplied but is not used by the current GA.

# Lower-bound increment

## Signature

```text
lower_bound_increment(solution) : Optional[int | float]
```

## Protocol

```python
class SupportsLowerBoundIncrement(Protocol[Solution]):
    def lower_bound_increment(self, solution: Solution) -> Optional[Union[int, float]]: ...
```

## Description

Declares calculation of the change in lower bound caused by a move.

## Implementation status

The generic `Move` protocol includes this capability. The supplied concrete GA moves expose `objective_value_increment` and `apply_move`, but do not define `lower_bound_increment` separately.

# Objective-value increment

## Signature

```text
objective_value_increment(solution) : Optional[int | float]
```

## Protocol

```python
class SupportsObjectiveValueIncrement(Protocol[Solution]):
    def objective_value_increment(self, solution: Solution) -> Optional[Union[int, float]]: ...
```

## Description

Calculates the objective difference before applying a move:

```text
increment = objective(after move) - objective(before move)
```

The implementation assumes minimisation. A negative increment is an improvement. An infeasible move returns positive infinity.

## Use cases

The mutation generators use this operation to reject capacity-infeasible candidates without modifying the solution.

# Apply crossover

## Signature

```text
apply_crossover(parents: list[Solution]) : list[Solution]
```

## Protocol

```python
class SupportsApplyCrossover(Protocol[Solution]):
    def apply_crossover(self, parents: list[Solution]) -> list[Solution]: ...
```

## Description

Takes parent solutions and returns child solutions. The current crossover operators expect two parents and produce two children.

## Pre-requisites

Both parents must belong to the crossover's configured problem and must carry compatible giant-tour permutations.

## See also

[Crossovers](#crossovers), [Crossover decoding](#crossover-decoding), [GA execution](#ga-execution).

# Mutation move

## Signature

```text
mutation_move() : Move provider
```

## Protocol

```python
class SupportsMutationMove(Protocol[Move]):
    def mutation_move(self) -> Move: ...
```

## Description

Allows a problem model to provide a mutation implementation compatible with its solution representation.

The CVRP problem selects the provider from its configured mutation name.

# Genetic Algorithm Components

# Insert move

## Signature

```text
InsertMove(vehicle_1_index, customer_from_index,
           vehicle_2_index, customer_to_index)
```

## Description

Moves one customer from a source route position to a destination route position. The source and destination may be the same vehicle.

## Feasibility

For inter-vehicle insertion, the destination load is checked before the move:

```text
v2.load + demand[customer] <= capacity
```

An infeasible move has objective increment `+infinity`.

## Increment calculation

The method combines:

1. the saving obtained by removing the customer from its current edges,
2. the cost of inserting it between its new predecessor and successor.

Special index logic handles an insertion within the same route after the source customer has been conceptually removed.

## Application

The move:

- calculates the increment,
- removes the customer,
- corrects the destination index for a forward move within the same route,
- inserts the customer,
- adds the increment to `solution.lb`,
- reconstructs the giant tour.

# Swap move

## Signature

```text
SwapMove(vehicle_1_index, customer_1_index,
         vehicle_2_index, customer_2_index)
```

## Description

Exchanges two customers. The customers may belong to the same route or different routes.

## Feasibility

For an inter-vehicle swap, both resulting loads are checked:

```text
v1.load - demand_1 + demand_2 <= capacity
v2.load - demand_2 + demand_1 <= capacity
```

## Increment calculation

The method calculates removed-edge and added-edge totals. Adjacent positions in the same route receive special treatment to avoid treating the exchanged customers as unrelated neighbours.

## Application

The move updates the solution objective incrementally and reconstructs route data and the giant tour.

# Selection

## Binary tournament selection

### Signature

```text
select(population, selection_pool=None) : Solution
```

### Description

Samples two distinct candidates and returns the one with the smaller objective value. When only one candidate remains, that candidate is returned.

If a mutable `selection_pool` is provided, the winner is removed from that pool. This supports selection without immediate replacement until the pool is exhausted.

## Roulette-wheel selection

### Signature

```text
select(population, selection_pool=None) : Solution
```

### Description

Converts minimisation objective values into non-negative weights:

```text
weight = worst_finite_value - objective_value + 1.0
```

`None` and infinite objective values receive weight `0.0`. If no finite values exist, or if the total weight is non-positive, selection falls back to uniform random choice.

## Selection factory

```text
_create_selection(name)
```

Supported names are:

```text
binary_tournament
roulette_wheel
```

An unknown name raises `ValueError`.

# Mutation

## Base mutation

### Signature

```text
_Mutation(problem, repetition_rate=0.10)
```

### Repetition count

```text
repetition_count = max(1, ceil(repetition_rate * problem.n))
```

The count is `0` when the problem size is `0` or the repetition rate is not positive.

Because `problem.n` includes the depot, the default count is based on the total node count rather than strictly on the customer count.

## Insert mutation

### Description

Repeats random insert-move generation `repetition_count` times.

The generator:

1. identifies non-empty source vehicles,
2. chooses a source vehicle,
3. chooses any destination vehicle,
4. chooses source and destination positions,
5. rejects no-op cases,
6. returns the first move whose objective increment is finite.

At most 100 attempts are made for each requested random insert move.

## Swap mutation

### Description

Repeats random swap-move generation `repetition_count` times.

Only non-empty vehicles are candidates. The method rejects an identical position pair and accepts the first capacity-feasible move within 100 attempts.

## No mutation

`NoMutation.random_move` returns `None`; `apply_move` returns the solution unchanged.

# Crossovers

# Crossover decoding

## Signature

```text
_decode_giant_tour(giant_tour) : Solution
```

## Description

Permutation crossovers operate on `solution.giant_tour`. A crossover-specific child permutation must then be decoded into a route-based CVRP solution.

The generic crossover base in `ga.py` delegates to:

```text
problem.solution_from_giant_tour(giant_tour)
```

The CVRP wrapper subclasses the generic crossover classes to connect decoding to the active vehicle-construction strategy.

# Partially Matched Crossover (PMX)

## Signature

```text
PMXCrossover.apply_crossover([parent_1, parent_2]) : list[Solution]
```

## Description

PMX selects two cut positions, copies the selected segment from one parent, resolves mapped values from the other parent, and fills remaining positions from the other parent.

The same cut positions are used to generate two reciprocal children.

# Cycle Crossover (CX)

## Signature

```text
CXCrossover.apply_crossover([parent_1, parent_2]) : list[Solution]
```

## Description

CX detects positional cycles between two parent permutations. Successive cycles alternate their source parent. The two children use opposite starting parents.

# Order Crossover (OX)

## Signature

```text
OXCrossover.apply_crossover([parent_1, parent_2]) : list[Solution]
```

## Description

OX copies one segment from the first parent. It then traverses the second parent cyclically from the position after the second cut, inserting customers not already present.

The result preserves the copied segment and relative order from the second parent.

# No crossover

## Signature

```text
NoCrossover.apply_crossover(parents) : list[Solution]
```

## Description

Returns independent copies of the parent solutions.

# GA Execution

## Signature

```text
ga(problem, crossover, max_iterations, population_size,
   crossover_probability, mutation_probability,
   elitism_rate, selection_type, initial_population,
   write_files=True, best_file_path=...,
   population_file_path=..., convergence_file_path=...)
    : Solution
```

## Initial population

The algorithm creates a selection operator and obtains the problem's mutation provider before generating the population.

### All-random mode

```text
all_random
```

The population is filled entirely through `problem.random_solution()`.

### Clarke-Wright-and-random mode

```text
cw_and_random
```

The generic GA attempts to add one solution from:

```text
problem.clarke_and_wright_savings(customers)
```

and then fills the remaining population randomly.

## Initial best

The first global best is the minimum-objective member of the initial population. It is copied and timestamped with elapsed running time.

## Parent selection

A `parent_selection_pool` begins as a shallow copy of the population. Winners are removed as they are selected. When the pool becomes empty it is replenished.

The second-parent logic attempts to avoid immediately reusing the first parent when the pool has just been exhausted.

## Variation

For each parent pair:

1. crossover is applied with probability `crossover_probability`,
2. otherwise copied parents become children,
3. each child is mutated with probability `mutation_probability`,
4. children are appended until the offspring population reaches `population_size`.

## Survival selection

The parent and offspring populations are combined and sorted by objective value.

```text
elite_count = int(population_size * elitism_rate)
```

The best `elite_count` solutions are copied directly. Remaining positions are filled by the configured selection operator from the non-elite pool.

## Global-best update

The best member of the new population replaces the stored global best only when its objective value is strictly smaller.

## Termination

The algorithm performs exactly `max_iterations` generations after iteration `0` and returns the global best solution.

## Running time

The best solution stores the elapsed time at which that best value was first discovered:

```text
best.running_time_seconds
```

This is not necessarily the total runtime of the entire GA if no improvement occurs near termination.

# CVRP GA Wrapper

## Signature

```text
solve_ga(problem, vehicle_construction=...,
         crossover_name=..., mutation_name=...,
         max_iterations=..., population_size=...,
         crossover_probability=..., mutation_probability=...,
         elitism_rate=..., selection_type=...,
         initial_population=...,
         mutation_repetition_rate=...,
         random_initial_seed=...,
         write_files=False, ...)
    : Solution
```

## Description

`solve_ga` is the public CVRP entry point. It:

1. configures the CVRP problem,
2. creates the requested crossover,
3. prepares output directories when required,
4. sets the random seed,
5. calls the generic `algorithms.ga`,
6. adds metadata headers to generated files,
7. returns the best solution.

# Configuration Reference

## Default values

| Parameter | Default | Meaning |
|---|---:|---|
| `construction_neighbourhood` | `AddNeighbourhood` | Stored construction-neighbourhood label. |
| `vehicle_construction` | `bellman_split` | Giant-tour decoding method. |
| `crossover_name` | `OXCrossover` | Crossover operator. |
| `mutation_name` | `SwapMutation` | Mutation operator. |
| `initial_population` | `all_random` | Initial-population policy. |
| `max_iterations` | `100` | Number of generations after iteration 0. |
| `population_size` | `100` | Number of solutions in each population. |
| `crossover_probability` | `0.75` | Probability of applying crossover to a parent pair. |
| `mutation_probability` | `0.05` | Probability of mutating each child. |
| `mutation_repetition_rate` | `0.10` | Fraction of `problem.n` used as mutation repetition count. |
| `elitism_rate` | `0.20` | Fraction used to calculate direct elite survivors. |
| `selection_type` | `binary_tournament` | Parent and non-elite survivor selection method. |
| `random_initial_seed` | `0` | Seed supplied to Python's `random` module. |

## Supported names

### Vehicle construction

```text
straight
bellman_split
```

### Crossover

```text
PMXCrossover
CXCrossover
OXCrossover
no_crossover
```

### Mutation

```text
InsertMutation
SwapMutation
no_mutation
```

### Selection

```text
binary_tournament
roulette_wheel
```

### Initial population

```text
all_random
cw_and_random
```

# Input Format

## Reader

### Signature

```text
Problem.file_reader(file_path) : Problem
Problem.from_textio(stream) : Problem
```

## Supported TSPLIB-style fields

The reader expects a CVRP instance containing:

```text
NAME
COMMENT
DIMENSION
EDGE_WEIGHT_TYPE
CAPACITY
NODE_COORD_SECTION
DEMAND_SECTION
DEPOT_SECTION
```

## Restrictions

- `EDGE_WEIGHT_TYPE` must be `EUC_2D`.
- Node identifiers must be consecutive and one-based in the file.
- Demand identifiers must be consecutive and one-based.
- The supported depot identifier is file node `1`.
- Depot demand must be `0`.

## Internal indexing

File node numbers are one-based, but internal tuple and matrix positions are zero-based. Internal depot index `0` corresponds to file node `1`.

## Distance matrix

For coordinates `(xi, yi)` and `(xj, yj)`, the reader stores the unrounded Euclidean distance:

```text
d[i][j] = sqrt((xi - xj)^2 + (yi - yj)^2)
```

# Output Formats

# Solution file

`write_solution_file` writes a complete best-solution file.

A representative layout is:

```text
NAME : CMT1.sol
TYPE : CVRP_SOLUTION
DIMENSION : ...
CAPACITY : ...
COST : ...
LB : ...
CROSSOVER: OXCrossover
MUTATION: SwapMutation
CROSSOVER RATE: 0.75
MUTATION RATE: 0.05
POPULATION SIZE: 100
ITERATION NUMBER: 100
ELITISM RATE: 0.2
SELECTION TYPE: binary_tournament
INITIAL POPULATION: all_random
VEHICLE CONSTRUCTION: bellman_split
RANDOM INITIAL SEED: 0
RUNNING TIME: ... seconds

ROUTES_SECTION
Vehicle #1: ..., distance = ..., load = .../...
...
GIANT_TOUR_SECTION
...
EOF
```

## Detailed best-per-iteration file

The generic GA writes, for each iteration:

```text
ITERATION i
BEST_OBJECTIVE : value
<serialised best solution>
```

The CVRP wrapper removes repeated problem-header lines and prepends a common configuration header after the run.

## Population file

Each line starts with the iteration index followed by compact route records for every population member.

## Convergence file

Each line contains:

```text
iteration,best_objective
```

This file can be plotted directly as a convergence curve.

# Usage

## Minimal execution

```python
from pathlib import Path

from vrp import Problem, solve_ga

instance_path = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "roar_net_api"
    / "problem_instances"
    / "CMT1.vrp"
)

problem = Problem.file_reader(str(instance_path))
best = solve_ga(problem)

print(best.objective_value())
print(best)
```

## Configured execution

```python
from pathlib import Path

from vrp import (
    BINARY_TOURNAMENT_SELECTION,
    DEFAULT_RANDOM_INITIAL_SEED,
    Problem,
    solve_ga,
    write_solution_file,
)

instance_name = "CMT1"
example_dir = Path(__file__).resolve().parent
instance_path = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "roar_net_api"
    / "problem_instances"
    / f"{instance_name}.vrp"
)
results_dir = example_dir / f"Results_{instance_name}"
results_dir.mkdir(parents=True, exist_ok=True)

problem = Problem.file_reader(str(instance_path))

best = solve_ga(
    problem,
    vehicle_construction=Problem.BELLMAN_SPLIT,
    crossover_name=Problem.OX_CROSSOVER,
    mutation_name=Problem.SWAP_MUTATION,
    max_iterations=100,
    population_size=100,
    crossover_probability=0.75,
    mutation_probability=0.05,
    elitism_rate=0.20,
    selection_type=BINARY_TOURNAMENT_SELECTION,
    initial_population=Problem.ALL_RANDOM,
    mutation_repetition_rate=0.10,
    random_initial_seed=DEFAULT_RANDOM_INITIAL_SEED,
    write_files=True,
    best_file_path=str(results_dir / "ga_detailed_best_each_iteration.txt"),
    population_file_path=str(results_dir / "ga_population.txt"),
    convergence_file_path=str(results_dir / "ga_convergence.txt"),
)

write_solution_file(
    str(results_dir / "ga_best.txt"),
    best,
    crossover_name=Problem.OX_CROSSOVER,
    mutation_name=Problem.SWAP_MUTATION,
    population_size=100,
    max_iterations=100,
)
```

## Creating a solution from routes

```python
routes = [
    [1, 4, 3],
    [2, 5],
]

solution = problem.solution_from_routes(routes)
print(solution.is_feasible)
print(solution.objective_value())
```

## Applying a move manually

```python
from roar_net_api.algorithms.ga import SwapMove

solution = problem.ordered_solution()
move = SwapMove(
    vehicle_1_index=0,
    customer_1_index=0,
    vehicle_2_index=0,
    customer_2_index=1,
)

increment = move.objective_value_increment(solution)

if increment != float("inf"):
    move.apply_move(solution)
```

# Extension Guide

## Adding a selection operator

1. Subclass `_Selection`.
2. Implement `select(population, selection_pool=None)`.
3. Add a public string constant.
4. Extend `_create_selection`.
5. Define how `None` and infinite objective values are handled.

## Adding a mutation

1. Subclass `_Mutation`.
2. Implement `apply_move`.
3. Add a concrete move class when incremental evaluation is required.
4. Extend `Problem.mutation_move`.
5. Add a public mutation-name constant.
6. Preserve capacity and assignment feasibility.
7. Reconstruct `giant_tour` after route changes.

## Adding a crossover

1. Subclass `_Crossover` or a CVRP decoding wrapper.
2. Implement `apply_crossover(parents)`.
3. Ensure every child permutation contains each customer exactly once.
4. Decode each child through `solution_from_giant_tour`.
5. Register the class in `CROSSOVER_FACTORIES`.

## Adding a vehicle split method

1. Add a method name constant to `VehicleSplit`.
2. Validate the name in `VehicleSplit.__init__`.
3. Dispatch from `VehicleSplit.apply`.
4. Return capacity-feasible `Vehicle` objects.
5. Raise an explicit error when no feasible split exists.

## Supporting another optimisation problem

A different problem model can use the generic GA when it supplies objects satisfying the effective requirements used by `ga.py`:

- the problem provides `random_solution()` and `mutation_move()`,
- solutions provide `copy_solution()` and `objective_value()`,
- solutions and problems expose any additional attributes required by the selected crossover or mutation,
- the crossover returns complete solution objects.

The current built-in crossover and mutation classes are CVRP/permutation-oriented despite the generic protocol annotations. A genuinely different problem representation will normally provide its own crossover and mutation implementations.

# Implementation Coverage Matrix

| Capability | Protocol declared | CVRP implemented | Used by current GA |
|---|:---:|:---:|:---:|
| Empty solution | Yes | Yes | No |
| Random solution | Yes | Yes | Yes |
| Ordered solution | Yes | Yes | No |
| Copy solution | Yes | Yes | Yes |
| Objective value | Yes | Yes | Yes |
| Lower bound | Yes | Yes | No direct GA use |
| Apply move | Yes | Yes | Yes |
| Exhaustive moves | Yes | No concrete implementation supplied | No |
| Random move | Yes | Yes through mutation providers | Yes |
| Random moves without replacement | Yes | No concrete implementation supplied | No |
| Objective increment | Yes | Yes | Yes |
| Lower-bound increment | Yes | Not supplied by concrete GA moves | No |
| Apply crossover | Yes | Yes | Yes |
| Mutation provider | Yes | Yes | Yes |

# Current Code-State Notes

The following points describe the supplied snapshot and should be checked against the active branch before publication or release.

## Module-level problem dependency

`Vehicle` and `VehicleSplit` access a lowercase module-level variable named `problem`. This makes their behaviour depend on global module state. When `vrp.py` is imported rather than executed directly, the active problem must be assigned before a vehicle is created.

A minimal compatibility approach is to assign the configured instance inside `configure_problem`:

```python
globals()["problem"] = problem
```

A more encapsulated future design would store a problem reference in each vehicle or split object.

## Mutable default route

The supplied constructor uses:

```python
def __init__(self, tour: list[int] = []):
```

A mutable default argument is shared across calls. Although the current constructor does not directly mutate the default list in every path, `None` is normally safer as a sentinel.

## Tour initialisation behaviour

The supplied constructor copies a non-empty input tour and then calls `add_customer` for every element of that same input. This can duplicate customer entries. The working branch should initialise `self.tour` as empty before adding customers, or directly assign the tour and calculate load and distance once.

## CVRP crossover decoder return type

The supplied CVRP wrapper defines:

```python
def _decode_giant_tour(self, giant_tour):
    return self.problem.construct_vehicles_from_giant_tour(giant_tour)
```

That method returns `list[Vehicle]`, whereas the generic crossover contract requires child `Solution` objects. The expected decoder is:

```python
return self.problem.solution_from_giant_tour(giant_tour)
```

## Clarke-Wright initialisation dependency

The generic GA supports `cw_and_random` by calling `problem.clarke_and_wright_savings(customers)`. The supplied CVRP `Problem` snapshot does not define that method. Therefore this mode requires an additional implementation or should remain disabled.

## Optional objective values and sorting

`Solution.objective_value()` returns `None` for infeasible solutions. Several GA operations use direct comparison or sorting. The active variation path must therefore preserve feasibility, or the GA must map `None` to a well-defined penalty before comparison.

## Protocol versus concrete move coverage

The generic `Move` protocol includes `lower_bound_increment`, but `InsertMove` and `SwapMove` do not define that method. This does not affect the current GA, which uses `objective_value_increment`, but it matters for strict static conformance.

## Swap application review

`SwapMove.apply_move` first writes swapped customers directly into the route lists and then performs remove-and-insert operations. This sequence should be covered by focused tests for:

- adjacent customers in the same route,
- non-adjacent customers in the same route,
- customers in different routes,
- exact agreement between incremental and fully recomputed distance.

# Recommended Validation Tests

## Route invariants

For every generated solution:

```text
len(giant_tour) == number_of_customers
set(giant_tour) == {1, ..., n - 1}
all(vehicle.load <= capacity)
```

## Distance consistency

For every vehicle:

```text
abs(vehicle.distance - problem.route_cost(vehicle.tour)) <= tolerance
```

For every solution:

```text
abs(solution.lb - sum(v.distance for v in solution.vehicles)) <= tolerance
```

## Increment consistency

For a copied solution and a feasible move:

```text
reported_increment
    == objective_after_apply - objective_before_apply
```

within a numerical tolerance.

## Crossover permutation validity

Every child giant tour must contain every customer exactly once.

## Reproducibility

Two runs with the same seed and configuration should produce identical random choices and output values, assuming deterministic iteration order and no parallel execution.

# Glossary

**Candidate solution**  
A represented point in the optimisation decision space.

**CVRP**  
Capacitated Vehicle Routing Problem.

**Depot**  
The common start and end node of every route. Internal index `0`.

**Elite**  
A high-quality solution copied directly into the next population.

**Giant tour**  
A permutation containing each customer exactly once, without route separators.

**Genotype**  
The representation manipulated by variation operators. Here, the giant tour acts as the permutation genotype.

**Phenotype**  
The decoded route set represented by the vehicle list.

**Move**  
A parameterised transformation from one solution to a neighbouring solution.

**Objective-value increment**  
The change in objective value caused by a move.

**PMX**  
Partially Matched Crossover.

**CX**  
Cycle Crossover.

**OX**  
Order Crossover.

**Selection pool**  
A temporary list from which selected winners are removed until replenishment.

**Straight split**  
Greedy capacity-based partition of a giant tour.

**Bellman split**  
Dynamic-programming partition of a fixed giant tour into minimum-cost feasible routes.

# Signature Index

```text
Problem.empty_solution() -> Solution
Problem.random_solution() -> Solution
Problem.ordered_solution() -> Solution
Problem.solution_from_giant_tour(giant_tour) -> Solution
Problem.solution_from_routes(routes) -> Solution
Problem.mutation_move() -> mutation provider

Solution.copy_solution() -> Solution
Solution.objective_value() -> Optional[float]
Solution.lower_bound() -> float
Solution.construct_giant_tour() -> None
Solution.to_textio(f) -> None

Vehicle.insert_customer(customer, index) -> None
Vehicle.add_customer(customer) -> None
Vehicle.remove_customer_at_index(index) -> None
Vehicle.remove_customer(customer) -> None
Vehicle.remove_last_customer() -> None
Vehicle.copy_vehicle() -> Vehicle

InsertMove.objective_value_increment(solution) -> float
InsertMove.apply_move(solution) -> Solution
SwapMove.objective_value_increment(solution) -> float
SwapMove.apply_move(solution) -> Solution

Selection.select(population, selection_pool=None) -> Solution
Mutation.random_move(solution) -> Optional[Mutation]
Mutation.apply_move(solution) -> Solution
Crossover.apply_crossover(parents) -> list[Solution]

ga(...) -> Solution
solve_ga(...) -> Solution
write_solution_file(file_path, solution, ...) -> None
```
