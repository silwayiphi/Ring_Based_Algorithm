from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class RingNode:
    id: int
    next_id: Optional[int] = None
    alive: bool = True

class Ring:
    def __init__(self, ids: List[int]):
        ids = sorted(ids)
        self.nodes: Dict[int, RingNode] = {i: RingNode(i) for i in ids}
        for i, nid in enumerate(ids):
            self.nodes[nid].next_id = ids[(i + 1) % len(ids)]
        self.leader_id: Optional[int] = max(ids)  # initial leader

    def _next_alive(self, nid: int) -> Optional[int]:
        """Follow next pointers, skipping dead nodes; stop if no alive found."""
        if nid not in self.nodes:
            return None
        start = nid
        cur = self.nodes[nid].next_id
        for _ in range(len(self.nodes)):
            if cur is None:
                return None
            if self.nodes[cur].alive:
                return cur
            cur = self.nodes[cur].next_id
        return None

    def start_election(self, initiator: Optional[int] = None) -> bool:
        """Chang–Roberts: pass ELECTION(candidateId) around the ring (alive nodes)."""
        alive_ids = [n.id for n in self.nodes.values() if n.alive]
        if not alive_ids:
            self.leader_id = None
            return False
        start = initiator or min(alive_ids)
        if not self.nodes[start].alive:
            start = min(alive_ids)
        candidate = start
        cur = start
        hops = 0
        while True:
            nxt = self._next_alive(cur)
            if nxt is None:  
                return False
            if nxt == start:
                break  
            candidate = max(candidate, nxt)
            cur = nxt
            hops += 1
            if hops > len(self.nodes) * 3: 
                return False
        self.leader_id = candidate
        return True

    def crash(self, nid: int) -> bool:
        if nid in self.nodes:
            self.nodes[nid].alive = False
            if self.leader_id == nid:
                self.leader_id = None
            return True
        return False

    def recover(self, nid: int) -> bool:
        if nid in self.nodes:
            self.nodes[nid].alive = True
            return True
        return False

    def state(self) -> dict:
        return {
            "leaderId": self.leader_id,
            "nodes": [
                {"id": n.id, "next": n.next_id, "alive": n.alive}
                for n in sorted(self.nodes.values(), key=lambda x: x.id)
            ],
        }
