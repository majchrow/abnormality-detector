from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Config:
    login: str
    password: str
    addresses: List[Tuple[str, int]]
    logfile: str
    dumpfile: str
    kafka_file: str
    ssl: bool = True
