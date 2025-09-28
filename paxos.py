# paxos.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List, Tuple

@dataclass
class Acceptor:
    name: str
    alive: bool = True
    promised_n: int = -1                 # highest prepare number promised
    accepted_n: Optional[int] = None     # highest accept number accepted
    accepted_v: Optional[str] = None     # value accepted for current slot

    def reset_accepted(self):
        self.accepted_n = None
        self.accepted_v = None

class PaxosCluster:
    """
    Single-proposer, single-slot-at-a-time Multi-Paxos demo.
    - 3+ acceptors (e.g., EU/US/APAC)
    - propose(command) runs Phase 1 & Phase 2 for next log slot (commitIndex+1)
    - crash/recover acceptors
    """
    def __init__(self, names: List[str]):
        self.acceptors: Dict[str, Acceptor] = {n: Acceptor(n) for n in names}
        self.proposal_counter: int = 0      # ensures unique increasing numbers
        self.commitIndex: int = 0
        self.log: Dict[int, str] = {}       # index -> chosen value

    # -------- helpers --------
    def majority(self) -> int:
        return len(self.acceptors) // 2 + 1

    def alive_acceptors(self) -> List[Acceptor]:
        return [a for a in self.acceptors.values() if a.alive]

    def next_proposal_n(self) -> int:
        self.proposal_counter += 1
        return self.proposal_counter

    # -------- API --------
    def crash(self, name: str) -> bool:
        if name in self.acceptors:
            self.acceptors[name].alive = False
            return True
        return False

    def recover(self, name: str) -> bool:
        if name in self.acceptors:
            self.acceptors[name].alive = True
            return True
        return False

    def state(self) -> dict:
        return {
            "commitIndex": self.commitIndex,
            "log": self.log,
            "acceptors": [
                {
                    "name": a.name,
                    "alive": a.alive,
                    "promised": a.promised_n,
                    "accepted": None if a.accepted_n is None else [a.accepted_n, a.accepted_v],
                }
                for a in self.acceptors.values()
            ],
            "majority": self.majority(),
        }

    def propose(self, command: str) -> dict:
        """
        Propose 'command' at slot = commitIndex+1.
        Phase 1: PREPARE(n) to alive; need majority PROMISE.
        Phase 2: ACCEPT(n, v) to alive; need majority ACCEPTED.
        """
        if not self.alive_acceptors():
            return {"ok": False, "reason": "no-acceptors-alive"}

        slot = self.commitIndex + 1
        # if already chosen (retries), return it
        if slot in self.log:
            return {"ok": True, "slot": slot, "chosen": self.log[slot], "already": True}

        n = self.next_proposal_n()

        # ----- Phase 1: Prepare/Promise -----
        promises = 0
        highest_accepted: Tuple[int, Optional[str]] = (-1, None)  # (na, va)
        for acc in self.alive_acceptors():
            # PREPARE(n)
            if n > acc.promised_n:
                acc.promised_n = n
                promises += 1
                # return any previously accepted value (if this slot was in progress)
                if acc.accepted_n is not None and acc.accepted_v is not None:
                    if acc.accepted_n > highest_accepted[0]:
                        highest_accepted = (acc.accepted_n, acc.accepted_v)
            else:
                # reject prepare (no reply)
                pass

        if promises < self.majority():
            return {"ok": False, "reason": "no-majority-phase1", "promises": promises}

        # choose value: highest accepted if any, otherwise our command
        v = highest_accepted[1] if highest_accepted[0] != -1 else command

        # ----- Phase 2: Accept/Accepted -----
        accepts = 0
        for acc in self.alive_acceptors():
            # ACCEPT(n, v): accept iff no higher promise was made
            if n >= acc.promised_n:
                acc.promised_n = n
                acc.accepted_n = n
                acc.accepted_v = v
                accepts += 1
            else:
                # reject accept
                pass

        if accepts < self.majority():
            return {"ok": False, "reason": "no-majority-phase2", "accepts": accepts}

        # chosen!
        self.log[slot] = v
        self.commitIndex = slot

        # clear per-slot accepted memory to keep UI clean (optional)
        for acc in self.acceptors.values():
            # keep promised_n (for safety), drop accepted (we moved to next slot)
            acc.reset_accepted()

        return {"ok": True, "slot": slot, "chosen": v}
