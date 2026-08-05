# Academy Scientific Workflow Examples

## Example 1: Molecular Simulation Pipeline

A pipeline for running and analyzing molecular dynamics simulations.

```python
from academy.agent import Agent, action
from academy.manager import Manager
from academy.exchange import LocalExchangeFactory


class StructurePreparationAgent(Agent):
    """Prepare molecular structures for simulation."""

    @action
    async def prepare(self, pdb_path: str) -> dict:
        """Load and prepare a molecular structure.

        Args:
            pdb_path: Path to PDB file

        Returns:
            Prepared structure with topology and coordinates
        """
        structure = await self._load_pdb(pdb_path)
        solvated = await self._add_solvent(structure)
        minimized = await self._energy_minimize(solvated)

        return {
            "topology": minimized["topology"],
            "coordinates": minimized["coordinates"],
            "box_vectors": minimized["box_vectors"]
        }


class SimulationAgent(Agent):
    """Run molecular dynamics simulations."""

    @action
    async def equilibrate(self, structure: dict, temperature: float = 300.0) -> dict:
        """Run equilibration simulation.

        Args:
            structure: Prepared molecular structure
            temperature: Target temperature in Kelvin

        Returns:
            Equilibrated structure and trajectory
        """
        result = await self._run_md(
            structure,
            steps=50000,
            temperature=temperature,
            ensemble="NPT"
        )
        return {
            "final_structure": result["final_frame"],
            "trajectory": result["trajectory_path"],
            "properties": result["computed_properties"]
        }

    @action
    async def production(self, structure: dict, nanoseconds: float = 10.0) -> dict:
        """Run production simulation.

        Args:
            structure: Equilibrated structure
            nanoseconds: Simulation length

        Returns:
            Trajectory and computed observables
        """
        steps = int(nanoseconds * 500000)  # 2 fs timestep
        result = await self._run_md(
            structure,
            steps=steps,
            ensemble="NVT"
        )
        return {
            "trajectory": result["trajectory_path"],
            "observables": result["observables"]
        }


class AnalysisAgent(Agent):
    """Analyze simulation trajectories."""

    @action
    async def analyze(self, trajectory_path: str) -> dict:
        """Compute analysis metrics from trajectory.

        Args:
            trajectory_path: Path to trajectory file

        Returns:
            Analysis results including RMSD, RMSF, contacts
        """
        trajectory = await self._load_trajectory(trajectory_path)

        return {
            "rmsd": await self._compute_rmsd(trajectory),
            "rmsf": await self._compute_rmsf(trajectory),
            "contacts": await self._compute_contacts(trajectory),
            "secondary_structure": await self._compute_dssp(trajectory)
        }


async def run_simulation_workflow(pdb_path: str):
    """Run complete simulation workflow."""
    async with await Manager.from_exchange_factory(
        factory=LocalExchangeFactory(),
    ) as manager:
        # Launch agents
        prep = await manager.launch(StructurePreparationAgent)
        sim = await manager.launch(SimulationAgent)
        analysis = await manager.launch(AnalysisAgent)

        # Execute workflow
        structure = await prep.prepare(pdb_path)
        equilibrated = await sim.equilibrate(structure)
        production = await sim.production(equilibrated["final_structure"])
        results = await analysis.analyze(production["trajectory"])

        return results
```

## Example 2: High-Throughput Screening

Parallel screening of molecular candidates.

```python
class ScreeningCoordinator(Agent):
    """Coordinate high-throughput screening."""

    def __init__(self):
        super().__init__()
        self._workers: list[Handle] = []

    @action
    async def add_worker(self, worker: Handle) -> None:
        """Add a screening worker."""
        self._workers.append(worker)

    @action
    async def screen(self, candidates: list[dict]) -> list[dict]:
        """Screen all candidates in parallel.

        Args:
            candidates: List of molecular candidates

        Returns:
            Screening results sorted by score
        """
        import asyncio

        # Distribute candidates across workers
        n_workers = len(self._workers)
        batches = [candidates[i::n_workers] for i in range(n_workers)]

        # Run in parallel
        batch_results = await asyncio.gather(*[
            worker.screen_batch(batch)
            for worker, batch in zip(self._workers, batches)
        ])

        # Flatten and sort
        all_results = [r for batch in batch_results for r in batch]
        return sorted(all_results, key=lambda x: x["score"], reverse=True)


class ScreeningWorker(Agent):
    """Worker that screens molecular candidates."""

    @action
    async def screen_batch(self, candidates: list[dict]) -> list[dict]:
        """Screen a batch of candidates.

        Args:
            candidates: Batch of candidates to screen

        Returns:
            Results with scores for each candidate
        """
        results = []
        for candidate in candidates:
            score = await self._compute_score(candidate)
            results.append({
                "id": candidate["id"],
                "smiles": candidate["smiles"],
                "score": score,
                "properties": await self._compute_properties(candidate)
            })
        return results


async def run_screening(candidates: list[dict], n_workers: int = 4):
    """Run high-throughput screening."""
    async with await Manager.from_exchange_factory(
        factory=LocalExchangeFactory(),
    ) as manager:
        coordinator = await manager.launch(ScreeningCoordinator)

        # Launch worker pool
        for _ in range(n_workers):
            worker = await manager.launch(ScreeningWorker)
            await coordinator.add_worker(worker)

        # Run screening
        return await coordinator.screen(candidates)
```

## Example 3: Autonomous Experiment Controller

Agent that autonomously controls experimental equipment.

```python
class ExperimentController(Agent):
    """Autonomous controller for experimental facility."""

    def __init__(self):
        super().__init__()
        self._instrument: Handle = None
        self._analyzer: Handle = None
        self._running = False
        self._experiment_log = []

    @action
    async def configure(
        self,
        instrument: Handle,
        analyzer: Handle
    ) -> None:
        """Configure controller with instrument and analyzer."""
        self._instrument = instrument
        self._analyzer = analyzer

    @action
    async def start_campaign(self, objectives: dict) -> str:
        """Start autonomous experimental campaign.

        Args:
            objectives: Target properties and constraints

        Returns:
            Campaign ID
        """
        self._objectives = objectives
        self._running = True
        return str(uuid.uuid4())

    @action
    async def stop_campaign(self) -> dict:
        """Stop campaign and return summary."""
        self._running = False
        return {
            "experiments_run": len(self._experiment_log),
            "best_result": self._get_best_result()
        }

    @loop
    async def autonomous_loop(self, shutdown: asyncio.Event) -> None:
        """Autonomous experiment loop."""
        while not shutdown.is_set():
            if not self._running:
                await asyncio.sleep(1)
                continue

            # Plan next experiment
            next_params = await self._plan_next_experiment()

            # Run experiment
            raw_data = await self._instrument.measure(next_params)

            # Analyze results
            analysis = await self._analyzer.process(raw_data)

            # Log and update model
            self._experiment_log.append({
                "parameters": next_params,
                "results": analysis
            })

            # Check if objectives met
            if self._check_objectives(analysis):
                self._running = False

    async def _plan_next_experiment(self) -> dict:
        """Use Bayesian optimization to plan next experiment."""
        # Fit model to existing data
        # Optimize acquisition function
        # Return next parameters to try
        pass
```

## Example 4: Federated Data Processing

Process data across multiple HPC facilities.

```python
from academy.exchange import HttpExchangeFactory
from globus_compute_sdk import Executor as GCExecutor


class DataProcessor(Agent):
    """Process scientific data at an HPC facility."""

    @action
    async def process_dataset(self, dataset_path: str) -> dict:
        """Process a dataset using local HPC resources.

        Args:
            dataset_path: Path to dataset (Globus endpoint path)

        Returns:
            Processing results and output path
        """
        # Load data from Globus endpoint
        data = await self._load_from_globus(dataset_path)

        # Process using local compute
        results = await self._run_analysis(data)

        # Save results to local Globus endpoint
        output_path = await self._save_to_globus(results)

        return {
            "status": "complete",
            "output_path": output_path,
            "summary": self._summarize(results)
        }


class FederatedWorkflow(Agent):
    """Coordinate processing across multiple facilities."""

    def __init__(self):
        super().__init__()
        self._facilities: dict[str, Handle] = {}

    @action
    async def register_facility(self, name: str, processor: Handle) -> None:
        """Register a processing facility."""
        self._facilities[name] = processor

    @action
    async def process_distributed(self, datasets: dict[str, str]) -> dict:
        """Process datasets at their respective facilities.

        Args:
            datasets: Mapping of facility name to dataset path

        Returns:
            Combined results from all facilities
        """
        import asyncio

        # Submit to each facility
        tasks = {
            name: self._facilities[name].process_dataset(path)
            for name, path in datasets.items()
        }

        # Gather results
        results = {}
        for name, task in tasks.items():
            results[name] = await task

        return results


async def run_federated_processing():
    """Run federated processing across DOE facilities."""
    # One hosted exchange moves messages; named Globus Compute executors
    # decide which facility each agent runs at.
    async with await Manager.from_exchange_factory(
        factory=HttpExchangeFactory(auth_method="globus"),
        executors={
            "argonne": GCExecutor("argonne-polaris-endpoint"),
            "nersc": GCExecutor("nersc-perlmutter-endpoint"),
        },
        default_executor="argonne",
    ) as manager:
        # Launch processors at each site
        processor_anl = await manager.launch(DataProcessor, executor="argonne")
        processor_nersc = await manager.launch(DataProcessor, executor="nersc")

        # Create federated coordinator
        coordinator = await manager.launch(FederatedWorkflow, executor="argonne")
        await coordinator.register_facility("argonne", processor_anl)
        await coordinator.register_facility("nersc", processor_nersc)

        # Run federated workflow
        results = await coordinator.process_distributed({
            "argonne": "/polaris/data/experiment_001",
            "nersc": "/perlmutter/data/experiment_002"
        })

        return results
```

## Example 5: Multi-Agent Discovery Pipeline

Scientific discovery with specialized agent roles.

```python
class ScoutAgent(Agent):
    """Survey literature and identify opportunities."""

    @action
    async def survey(self, topic: str) -> dict:
        """Survey scientific literature for a topic.

        Returns:
            Identified opportunities and knowledge gaps
        """
        papers = await self._search_literature(topic)
        gaps = await self._identify_gaps(papers)
        return {
            "relevant_papers": papers,
            "knowledge_gaps": gaps,
            "opportunities": await self._rank_opportunities(gaps)
        }


class PlannerAgent(Agent):
    """Design experimental plans."""

    @action
    async def design(self, opportunities: dict) -> dict:
        """Create experimental plan for top opportunities.

        Returns:
            Detailed experimental plan
        """
        top_opportunity = opportunities["opportunities"][0]
        return {
            "hypothesis": await self._formulate_hypothesis(top_opportunity),
            "experiments": await self._design_experiments(top_opportunity),
            "success_criteria": await self._define_criteria(top_opportunity)
        }


class OperatorAgent(Agent):
    """Execute computational experiments."""

    @action
    async def execute(self, plan: dict) -> dict:
        """Execute experimental plan.

        Returns:
            Raw experimental results
        """
        results = []
        for experiment in plan["experiments"]:
            result = await self._run_experiment(experiment)
            results.append(result)
        return {"raw_results": results}


class AnalystAgent(Agent):
    """Interpret experimental results."""

    @action
    async def interpret(self, results: dict) -> dict:
        """Analyze and interpret results.

        Returns:
            Interpretation and recommendations
        """
        analysis = await self._statistical_analysis(results["raw_results"])
        return {
            "analysis": analysis,
            "conclusions": await self._draw_conclusions(analysis),
            "next_steps": await self._recommend_next_steps(analysis)
        }


class ArchivistAgent(Agent):
    """Document and store findings."""

    @action
    async def archive(self, findings: dict) -> dict:
        """Archive findings for future reference.

        Returns:
            Archive location and metadata
        """
        doc = await self._generate_report(findings)
        location = await self._store_in_repository(doc)
        return {"archive_id": location, "report": doc}


async def run_discovery_pipeline(research_topic: str):
    """Run autonomous discovery pipeline."""
    async with await Manager.from_exchange_factory(
        factory=LocalExchangeFactory(),
    ) as manager:
        # Launch specialized agents
        scout = await manager.launch(ScoutAgent)
        planner = await manager.launch(PlannerAgent)
        operator = await manager.launch(OperatorAgent)
        analyst = await manager.launch(AnalystAgent)
        archivist = await manager.launch(ArchivistAgent)

        # Execute discovery pipeline
        opportunities = await scout.survey(research_topic)
        plan = await planner.design(opportunities)
        results = await operator.execute(plan)
        interpretation = await analyst.interpret(results)
        archive = await archivist.archive({
            "topic": research_topic,
            "opportunities": opportunities,
            "plan": plan,
            "results": results,
            "interpretation": interpretation
        })

        return archive
```
