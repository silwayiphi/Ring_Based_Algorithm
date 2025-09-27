from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class Node:
    id: int
    alive: bool = True
    participant: bool = False
    elected: Optional[int] = None  # last known coordinator

class Ring:
    """
    Chang–Roberts election, step-by-step:
      1) Initiator marks itself participant, sends ELECTION(j) clockwise.
      2) On receive ELECTION(j):
         - if j > own id: forward unchanged, mark participant.
         - if j < own id:
             - if self non-participant: replace j with own id, mark participant.
             - else (already participant): forward unchanged.
         - if j == own id: winner; send COORDINATOR(k) around the ring.
      3) On receive COORDINATOR(k): set elected=k, mark non-participant, forward.
    """
    def __init__(self, ids: List[int] | None = None):
        ids = ids or [1, 2, 3, 4, 5, 6]
        self.order: List[int] = ids[:]                         # clockwise order
        self.idx: Dict[int, int] = {v: i for i, v in enumerate(self.order)}
        self.nodes: Dict[int, Node] = {i: Node(i) for i in self.order}
        self.leader_id: Optional[int] = None

    # ---------- helpers ----------
    def next_alive(self, id_: int) -> Optional[int]:
        """Clockwise next alive node; wraps around."""
        if id_ not in self.idx:
            return None
        n = len(self.order)
        start = self.idx[id_]
        for k in range(1, n + 1):
            cand = self.order[(start + k) % n]
            if self.nodes[cand].alive:
                return cand
        return None

    def state(self) -> dict:
        return {
            "leaderId": self.leader_id,
            "nodes": [
                {
                    "id": nd.id,
                    "alive": nd.alive,
                    "participant": nd.participant,
                    "elected": nd.elected,
                }
                for nd in (self.nodes[i] for i in self.order)
            ],
        }

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

    def reset_flags(self):
        for nd in self.nodes.values():
            nd.participant = False
            nd.elected = None
        self.leader_id = None

    # ---------- fast (no animation) ----------
    def start_fast(self, initiator: Optional[int] = None) -> dict:
        trace = self.election_trace(initiator)
        if trace.get("ok"):
            leader = trace["leaderId"]
            self.leader_id = leader
            for nd in self.nodes.values():
                nd.elected = leader
                nd.participant = False
        return trace

    # ---------- full step trace (no sleeps; UI animates) ----------
    def election_trace(self, initiator: Optional[int] = None) -> dict:
        live = [i for i in self.order if self.nodes[i].alive]
        if not live:
            return {"ok": False, "reason": "no-alive-nodes"}

        start = initiator if (initiator in self.nodes and self.nodes[initiator].alive) else live[0]

        # simulate with local copies so we don't mutate until the end
        P = {i: self.nodes[i].participant for i in self.order}
        E = {i: self.nodes[i].elected for i in self.order}
        steps: List[dict] = []

        # start: mark participant and send ELECTION(j)
        if not P[start]:
            P[start] = True
            steps.append({"type": "start", "who": start})

        j = start
        frm = start
        to = self.next_alive(frm)
        if to is None:
            return {"ok": False, "reason": "ring-broken"}

        guard = len(self.order) * 6
        while guard > 0:
            guard -= 1
            me = to
            myid = me

            if j > myid:
                was = P[me]
                P[me] = True
                steps.append({
                    "type": "hop",
                    "frm": frm, "to": me,
                    "msg": "ELECTION", "j_in": j,
                    "compare": "j>me",
                    "action": "forward-unchanged",
                    "marked_participant": (not was and P[me]),
                })
                frm, to = me, self.next_alive(me)
                if to is None: return {"ok": False, "reason": "ring-broken"}
                continue

            if j < myid:
                if not P[me]:
                    P[me] = True
                    old = j
                    j = myid
                    steps.append({
                        "type": "hop",
                        "frm": frm, "to": me,
                        "msg": "ELECTION", "j_in": old,
                        "compare": "j<me & non-participant",
                        "action": f"replace-with-{myid}",
                        "marked_participant": True,
                    })
                else:
                    steps.append({
                        "type": "hop",
                        "frm": frm, "to": me,
                        "msg": "ELECTION", "j_in": j,
                        "compare": "j<me & participant",
                        "action": "forward-unchanged",
                        "marked_participant": False,
                    })
                frm, to = me, self.next_alive(me)
                if to is None: return {"ok": False, "reason": "ring-broken"}
                continue

            # j == myid → winner
            if j == myid:
                steps.append({"type": "winner", "who": me})
                leader = me

                # coordinator tour
                frm2 = leader
                to2 = self.next_alive(leader)
                guard2 = len(self.order) * 6
                while guard2 > 0 and to2 is not None and to2 != leader:
                    guard2 -= 1
                    E[to2] = leader
                    P[to2] = False
                    steps.append({
                        "type": "coord",
                        "frm": frm2, "to": to2,
                        "leader": leader,
                        "action": "set-elected-and-forward",
                    })
                    frm2, to2 = to2, self.next_alive(frm2)

                steps.append({"type": "end", "leader": leader})
                return {"ok": True, "leaderId": leader, "steps": steps}

        return {"ok": False, "reason": "loop-guard"}
