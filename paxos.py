from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import itertools

@dataclass
class Acceptor:
    name: str
    alive: bool = True
    promised_n: Dict[int, int] = field(default_factory=dict)      # index -> n
    accepted: Dict[int, Tuple[int, str]] = field(default_factory=dict)  # index -> (n,val)

    def promise(self, index: int, n: int):
        if not self.alive: return None
        if n >= self.promised_n.get(index, -1):
            self.promised_n[index] = n
            prev = self.accepted.get(index)  # (n,val) or None
            return {"promised": n, "prev": prev}
        return {"rejected": True, "promised": self.promised_n[index]}

    def accept(self, index: int, n: int, val: str):
        if not self.alive: return None
        if n >= self.promised_n.get(index, -1):
            self.promised_n[index] = n
            self.accepted[index] = (n, val)
            return {"accepted": True}
        return {"rejected": True, "promised": self.promised_n[index]}

class Paxos:
    def __init__(self):
        self.acceptors: Dict[str, Acceptor] = {
            "EU": Acceptor("EU"),
            "US": Acceptor("US"),
            "APAC": Acceptor("APAC"),
        }
        self.seq = itertools.count(1)
        self.log: Dict[int, str] = {}   # index -> chosen value
        self.commit_index = 0

    def _majority(self) -> int:
        alive = sum(1 for a in self.acceptors.values() if a.alive)
        return alive // 2 + 1

    def propose(self, value: str, index: Optional[int] = None) -> dict:
        index = index or (self.commit_index + 1)
        n = next(self.seq)

        # Phase 1: Prepare/Promise
        votes = []
        for a in self.acceptors.values():
            r = a.promise(index, n)
            if r is not None: votes.append(r)
        if sum(1 for v in votes if v and "promised" in v and "rejected" not in v) < self._majority():
            return {"ok": False, "phase": 1}

        # choose highest previously accepted value (if any)
        chosen = value
        best_n = -1
        for v in votes:
            if v and v.get("prev"):
                pn, pv = v["prev"]
                if pn > best_n:
                    best_n, chosen = pn, pv

        # Phase 2: Accept
        acks = 0
        for a in self.acceptors.values():
            r = a.accept(index, n, chosen)
            if r and r.get("accepted"): acks += 1
        if acks < self._majority():
            return {"ok": False, "phase": 2}

        # Chosen
        self.log[index] = chosen
        self.commit_index = max(self.commit_index, index)
        return {"ok": True, "index": index, "value": chosen, "commitIndex": self.commit_index}

    def crash(self, name: str) -> bool:
        name = name.upper()
        if name in self.acceptors:
            self.acceptors[name].alive = False
            return True
        return False

    def recover(self, name: str) -> bool:
        name = name.upper()
        if name in self.acceptors:
            self.acceptors[name].alive = True
            return True
        return False

    def snapshot(self) -> dict:
        acc = []
        for a in self.acceptors.values():
            acc.append({
                "name": a.name, "alive": a.alive,
                "promised": a.promised_n, "accepted": {i: v[1] for i, v in a.accepted.items()}
            })
        consistent = all(i in self.log for i in range(1, self.commit_index + 1))
        return {"acceptors": acc, "log": self.log, "commitIndex": self.commit_index, "consistent": consistent}
