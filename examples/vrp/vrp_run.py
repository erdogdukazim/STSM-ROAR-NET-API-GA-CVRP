
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import vrp


PROBLEM_INSTANCES_DIR = SRC_DIR / "roar_net_api" / "problem_instances"

BENCHMARK_PROBLEM_FILES = [
    PROBLEM_INSTANCES_DIR / "CMT1.vrp",
    PROBLEM_INSTANCES_DIR / "CMT2.vrp",
    PROBLEM_INSTANCES_DIR / "CMT3.vrp",
    PROBLEM_INSTANCES_DIR / "CMT4.vrp",
    PROBLEM_INSTANCES_DIR / "CMT5.vrp",
    PROBLEM_INSTANCES_DIR / "CMT11.vrp",
    PROBLEM_INSTANCES_DIR / "CMT12.vrp",
    PROBLEM_INSTANCES_DIR / "Golden_1.vrp",
    PROBLEM_INSTANCES_DIR / "Golden_5.vrp",
    PROBLEM_INSTANCES_DIR / "Golden_9.vrp",
    PROBLEM_INSTANCES_DIR / "Golden_13.vrp",
    PROBLEM_INSTANCES_DIR / "Golden_17.vrp",
]

VEHICLE_CONSTRUCTIONS = [
    vrp.Problem.STRAIGHT,
    vrp.Problem.BELLMAN_SPLIT,
]

MAX_ITERATIONS = [
    100,
]

POPULATION_SIZES = [
    100,
]

CROSSOVERS = [
    vrp.Problem.PMX_CROSSOVER,
    vrp.Problem.CX_CROSSOVER,
    vrp.Problem.OX_CROSSOVER,
    vrp.Problem.NO_CROSSOVER,
]

MUTATIONS = [
    vrp.Problem.INSERT_MUTATION,
    vrp.Problem.SWAP_MUTATION,
    vrp.Problem.NO_MUTATION,
]

CROSSOVER_PROBABILITIES = [
    0.75,
]

MUTATION_PROBABILITIES = [
    0.05,
]

ELITISM_RATES = [
    0.2,
]

SELECTION_TYPES = [
    vrp.BINARY_TOURNAMENT_SELECTION,
    vrp.ROULETTE_WHEEL_SELECTION,
]

INITIAL_POPULATION = [
    vrp.Problem.ALL_RANDOM,
]

DEFAULT_INITIAL_SEEDS = [
    0,1,2,3,4,5,6,7,8,9,10,11,12,13,14
]

EXAMPLE_DIR = Path(__file__).resolve().parent

ABBREVIATIONS = {
    vrp.Problem.STRAIGHT: "st",
    vrp.Problem.BELLMAN_SPLIT: "bs",
    vrp.Problem.PMX_CROSSOVER: "pmx",
    vrp.Problem.CX_CROSSOVER: "cx",
    vrp.Problem.OX_CROSSOVER: "ox",
    vrp.Problem.NO_CROSSOVER: "nox",
    vrp.Problem.INSERT_MUTATION: "insm",
    vrp.Problem.SWAP_MUTATION: "swpm",
    vrp.Problem.NO_MUTATION: "nom",
    vrp.BINARY_TOURNAMENT_SELECTION: "bt",
    vrp.ROULETTE_WHEEL_SELECTION: "rw",
    vrp.Problem.ALL_RANDOM: "ar",
}


class RunConfig(NamedTuple):
    vehicle_construction: str
    crossover_name: str
    mutation_name: str
    max_iterations: int
    population_size: int
    crossover_probability: float
    mutation_probability: float
    elitism_rate: float
    selection_type: str
    initial_population: str
    random_initial_seed: int


def iter_run_configs(random_initial_seed: int) -> list[RunConfig]:
    configs: list[RunConfig] = []

    for (
        vehicle_construction,
        crossover,
        mutation,
        max_iterations,
        population_size,
        crossover_probability,
        mutation_probability,
        elitism_rate,
        selection_type,
        initial_population,
    ) in itertools.product(
        VEHICLE_CONSTRUCTIONS,
        CROSSOVERS,
        MUTATIONS,
        MAX_ITERATIONS,
        POPULATION_SIZES,
        CROSSOVER_PROBABILITIES,
        MUTATION_PROBABILITIES,
        ELITISM_RATES,
        SELECTION_TYPES,
        INITIAL_POPULATION,
    ):
        configs.append(
            RunConfig(
                vehicle_construction,
                crossover,
                mutation,
                max_iterations,
                population_size,
                crossover_probability,
                mutation_probability,
                elitism_rate,
                selection_type,
                initial_population,
                random_initial_seed,
            )
        )

    return configs


def load_problem(problem_file: Path) -> vrp.Problem:
    with problem_file.open(encoding="utf-8") as f:
        return vrp.Problem.from_textio(f)


def problem_results_directory(base_results_dir: Path, problem_file: Path) -> Path:
    return base_results_dir / problem_file.stem


def seed_results_directory(base_results_dir: Path, seed: int) -> Path:
    return base_results_dir / f"SEED_{seed}"


def _format_float_for_filename(value: float) -> str:
    return f"{value:g}".replace(".", "p")


def _abbreviate(value: object) -> str:
    text = str(value)
    return ABBREVIATIONS.get(text, text.lower().replace(" ", "_").replace(".", "p"))


def result_file_prefix(problem_file: Path, config: RunConfig) -> str:
    parts = [
        problem_file.stem,
        f"vc-{_abbreviate(config.vehicle_construction)}",
        f"cx-{_abbreviate(config.crossover_name)}",
        f"mt-{_abbreviate(config.mutation_name)}",
        f"it-{config.max_iterations}",
        f"pop-{config.population_size}",
        f"cr-{_format_float_for_filename(config.crossover_probability)}",
        f"mr-{_format_float_for_filename(config.mutation_probability)}",
        f"er-{_format_float_for_filename(config.elitism_rate)}",
        f"sel-{_abbreviate(config.selection_type)}",
        f"ip-{_abbreviate(config.initial_population)}",
        f"seed-{config.random_initial_seed}",
    ]
    return "_".join(parts)


def result_type_directory(problem_file: Path, results_dir: Path, result_type: str) -> Path:
    return results_dir / f"{problem_file.stem}_{result_type}"


class ResultPaths(NamedTuple):
    detailed_best: Path
    population: Path
    convergence: Path
    best: Path


def result_paths(problem_file: Path, results_dir: Path, config: RunConfig) -> ResultPaths:
    file_prefix = result_file_prefix(problem_file, config)
    return ResultPaths(
        detailed_best=(
            result_type_directory(problem_file, results_dir, "ga_detailed_best_each_iteration")
            / f"{file_prefix}.txt"
        ),
        population=(
            result_type_directory(problem_file, results_dir, "ga_population")
            / f"{file_prefix}.txt"
        ),
        convergence=(
            result_type_directory(problem_file, results_dir, "ga_convergence")
            / f"{file_prefix}.txt"
        ),
        best=(
            result_type_directory(problem_file, results_dir, "ga_best")
            / f"{file_prefix}.txt"
        ),
    )


def write_best_solution(path: Path, solution: vrp.Solution, config: RunConfig) -> None:
    vrp.write_solution_file(
        str(path),
        solution,
        crossover_name=config.crossover_name,
        mutation_name=config.mutation_name,
        crossover_probability=config.crossover_probability,
        mutation_probability=config.mutation_probability,
        population_size=config.population_size,
        max_iterations=config.max_iterations,
        elitism_rate=config.elitism_rate,
        selection_type=config.selection_type,
        initial_population=config.initial_population,
        vehicle_construction=config.vehicle_construction,
        random_initial_seed=config.random_initial_seed,
    )


def run_problem(problem_file: Path, base_results_dir: Path, config: RunConfig) -> None:
    results_dir = problem_results_directory(base_results_dir, problem_file)
    results_dir.mkdir(parents=True, exist_ok=True)

    paths = result_paths(problem_file, results_dir, config)
    if all(path.exists() for path in paths):
        print(f"Skipping completed combination: {paths.best.stem}")
        return

    problem = load_problem(problem_file)

    solution = vrp.solve_ga(
        problem,
        vehicle_construction=config.vehicle_construction,
        crossover_name=config.crossover_name,
        mutation_name=config.mutation_name,
        max_iterations=config.max_iterations,
        population_size=config.population_size,
        crossover_probability=config.crossover_probability,
        mutation_probability=config.mutation_probability,
        elitism_rate=config.elitism_rate,
        selection_type=config.selection_type,
        initial_population=config.initial_population,
        random_initial_seed=config.random_initial_seed,
        write_files=True,
        best_file_path=str(paths.detailed_best),
        population_file_path=str(paths.population),
        convergence_file_path=str(paths.convergence),
    )

    write_best_solution(paths.best, solution, config)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-dir",
        default=EXAMPLE_DIR / "Results_DoE",
        type=Path,
        help="Directory where GA output files are written.",
    )
    parser.add_argument(
        "--seeds",
        default=DEFAULT_INITIAL_SEEDS,
        nargs="+",
        type=int,
        help="Random initial seed(s) to run. Defaults to seed 1 so a normal Run resumes SEED_1.",
    )
    args = parser.parse_args()

    args.results_dir.mkdir(parents=True, exist_ok=True)

    for seed in args.seeds:
        seed_results_dir = seed_results_directory(args.results_dir, seed)
        seed_results_dir.mkdir(parents=True, exist_ok=True)
        configs = iter_run_configs(seed)

        for problem_file in BENCHMARK_PROBLEM_FILES:
            if not problem_file.exists():
                print(f"Skipping missing problem instance: {problem_file}")
                continue

            problem_results_directory(seed_results_dir, problem_file).mkdir(parents=True, exist_ok=True)

            for run_index, config in enumerate(configs, start=1):
                print(
                    f"Running seed {seed}, {problem_file.name}, combination {run_index:03d}/"
                    f"{len(configs):03d}: {result_file_prefix(problem_file, config)}"
                )
                run_problem(problem_file, seed_results_dir, config)


if __name__ == "__main__":
    main()
