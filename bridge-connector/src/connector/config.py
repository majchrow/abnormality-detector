from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class Config:
    login: str
    password: str
    addresses: List[Tuple[str, int]]
    logfile: str
    dumpfile: str
    kafka_bootstrap_address: Optional[str]
    ssl: bool = True
