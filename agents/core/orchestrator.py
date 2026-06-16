"""AgentOrchestrator — manages logging and agent pipeline execution."""
import traceback
from datetime import datetime

from sqlalchemy.orm import Session

from .db import AgentRun, SessionLocal


class AgentOrchestrator:
    """
    Manages one agent run: creates the AgentRun DB record, streams logs
    line-by-line (so NestJS SSE can stream them), and handles failures.
    """

    def __init__(self, agent_type: str, triggered_by: str = "scheduler"):
        self.agent_type = agent_type
        self.triggered_by = triggered_by
        self.run_id: int | None = None
        self._session: Session | None = None

    def __enter__(self):
        self._session = SessionLocal()
        run = AgentRun(
            agent_type=self.agent_type,
            status="running",
            started_at=datetime.utcnow(),
            triggered_by=self.triggered_by,
            log="",
        )
        self._session.add(run)
        self._session.commit()
        self._session.refresh(run)
        self.run_id = run.id
        self.log(f"[START] {self.agent_type} run #{run.id}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        run = self._session.get(AgentRun, self.run_id)
        run.finished_at = datetime.utcnow()
        if exc_type:
            run.status = "failed"
            run.error = f"{exc_type.__name__}: {exc_val}\n{traceback.format_exc()}"
            self.log(f"[ERROR] {run.error}")
        else:
            run.status = "completed"
            self.log(f"[DONE] {self.agent_type} run #{self.run_id} completed")
        self._session.commit()
        self._session.close()
        return False  # don't suppress exceptions

    def log(self, message: str):
        """Append a timestamped log line and flush to DB immediately."""
        ts = datetime.utcnow().strftime("%H:%M:%S")
        line = f"[{ts}] {message}\n"
        print(line, end="", flush=True)
        if self._session and self.run_id:
            run = self._session.get(AgentRun, self.run_id)
            run.log = (run.log or "") + line
            self._session.commit()

    def get_session(self) -> Session:
        return self._session
