from abc import ABC

from pydantic import BaseModel


class BaseAgent(BaseModel, ABC):
    """Shared identity for every agent — the coordinator and each sub-agent.

    Carries only ``name``/``description``. How an agent is invoked differs by
    role (the coordinator decides a round, sub-agents run a dispatched task), so
    the call interface lives on the role-specific subclasses, not here.
    """

    name: str
    description: str
