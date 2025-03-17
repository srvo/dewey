from joblib import Parallel, delayed
from typing import List, Dict, Callable, Generator, Optional
import logging
import os
import traceback
from datetime import datetime

# Configure structured logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
logger = logging.getLogger("workflow")


class WorkflowPhase:
    """Managed workflow phase with retry logic."""
    
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds

    def __init__(self, name: str, task: Callable, args: Dict = None):
        self.name = name
        self.task = task
        self.args = args or {}
        self.retries = 0
        self.created_at = datetime.now()
        logger.debug(f"Initialized phase: {self.name}")

    def execute(self):
        """Execute phase with retry logic and detailed tracing."""
        logger.info(f"Phase START: {self.name}", extra={"phase": self.name})
        start_time = datetime.now()
        
        try:
            result = self.task(**self.args)
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Phase COMPLETE: {self.name} ({duration:.2f}s)",
                extra={"phase": self.name, "duration": duration}
            )
            return result
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.retries += 1
            
            logger.error(
                f"Phase FAILED: {self.name} (attempt {self.retries}/{self.MAX_RETRIES})",
                extra={
                    "phase": self.name,
                    "error": str(e),
                    "trace": traceback.format_exc(),
                    "duration": duration
                }
            )
            
            if self.retries < self.MAX_RETRIES:
                logger.info(f"Retrying {self.name} in {self.RETRY_DELAY}s...")
                time.sleep(self.RETRY_DELAY)
                return self.execute()
            
            raise WorkflowError(f"Phase {self.name} failed after {self.MAX_RETRIES} attempts") from e


class Workflow:
    """Orchestrated workflow execution with state tracking."""
    
    def __init__(self, phases: List[WorkflowPhase], n_jobs: int = 1):
        self.phases = phases
        self.n_jobs = max(1, n_jobs)
        self.execution_id = f"WF-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.state = {
            "current_phase": None,
            "progress": 0.0,
            "errors": []
        }
        logger.info(f"Created workflow {self.execution_id} with {len(phases)} phases")

    def execute(self) -> List:
        """Execute phases with parallel-serial hybrid strategy."""
        logger.info(f"EXECUTE START: {self.execution_id}")
        results = []
        
        try:
            results = Parallel(n_jobs=self.n_jobs, prefer="threads")(
                delayed(self._safe_execute)(phase) 
                for phase in self.phases
            )
        except WorkflowError as e:
            logger.critical(f"Workflow ABORTED: {self.execution_id}")
            raise
            
        logger.info(f"EXECUTE COMPLETE: {self.execution_id}")
        return results

    def _safe_execute(self, phase: WorkflowPhase):
        """Wrapper for phase execution with state tracking."""
        self.state["current_phase"] = phase.name
        try:
            result = phase.execute()
            self.state["progress"] += 1/len(self.phases)
            return result
        except Exception as e:
            self.state["errors"].append({
                "phase": phase.name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            raise

    def observe(self) -> Generator:
        """Observation generator with progress updates."""
        total = len(self.phases)
        for idx, phase in enumerate(self.phases):
            self.state.update({
                "current_phase": phase.name,
                "progress": idx/total
            })
            
            logger.info(
                f"OBSERVE PROGRESS: {idx+1}/{total} ({self.state['progress']:.1%})",
                extra=self.state
            )
            
            try:
                yield phase.execute()
                self.state["progress"] = (idx+1)/total
            except Exception as e:
                self.state["errors"].append({
                    "phase": phase.name,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                raise

    def audit(self) -> Dict:
        """Generate workflow execution audit report."""
        return {
            "execution_id": self.execution_id,
            "start_time": self.created_at.isoformat(),
            "duration": (datetime.now() - self.created_at).total_seconds(),
            "phases_attempted": len(self.phases),
            "phases_completed": len(self.phases) - len(self.state["errors"]),
            "errors": self.state["errors"],
            "success_rate": (len(self.phases) - len(self.state["errors"])) / len(self.phases)
        }


class WorkflowError(Exception):
    """Specialized exception for workflow failures."""
    def __init__(self, message: str, phase: Optional[str] = None):
        super().__init__(message)
        self.phase = phase
        self.timestamp = datetime.now().isoformat()


class ResearchWorkflow(Workflow):
    """Base research workflow with enhanced validation."""
    
    def __init__(self):
        super().__init__(phases=[], n_jobs=1)
        self.data_validation = {
            "required_fields": ["ticker", "name", "sector"],
            "valid_ticks": range(-100, 101)
        }

    def build_query(self, data: Dict) -> str:
        """Validate input data before query building."""
        missing = [f for f in self.data_validation["required_fields"] if f not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
            
        if data.get("current_tick", 0) not in self.data_validation["valid_ticks"]:
            raise ValueError(f"Invalid tick value: {data.get('current_tick')}")
            
        return super().build_query(data)

    # Remaining methods with augmented validation
