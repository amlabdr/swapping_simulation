from enum import Enum, auto
from typing import List, TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from sequence.topology.node import QuantumRouter
    from sequence.resource_management.memory_manager import MemoryInfo, MemoryManager
    from sequence.entanglement_management.entanglement_protocol import EntanglementProtocol

from sequence.resource_management.rule_manager import Rule, Arguments
from sequence.entanglement_management.generation import EntanglementGenerationA
from sequence.entanglement_management.purification import BBPSSW
from sequence.entanglement_management.swapping import EntanglementSwappingA, EntanglementSwappingB
from sequence.message import Message
from sequence.protocol import StackProtocol
from sequence.kernel.event import Event
from sequence.kernel.process import Process

MAP = {0:1,
       1:1,
       2:2,
       3:4}
MAP = {0:4,
       1:4,
       2:2,
       3:1}


def eg_rule_condition(memory_info: "MemoryInfo",
                      manager: "MemoryManager",
                      args: Arguments) -> List["MemoryInfo"]:
    """Condition function used by entanglement generation protocol on nodes

    """
    memory_indices = args['memory_indices']
    if memory_info.state == "RAW" and memory_info.index in memory_indices:
        return [memory_info]
    else:
        return []


def eg_rule_action1(memories_info: List["MemoryInfo"], args: Dict[str, Any]):
    """Action function used by entanglement generation protocol on nodes except
    the initiator

    """
    memories = [info.memory for info in memories_info]
    memory = memories[0]
    mid = args["mid"]
    path = args["path"]
    index = args["index"]
    protocol = EntanglementGenerationA(None, "EGA." + memory.name, mid,
                                       path[index - 1], memory)
    return protocol, [None], [None], [None]


def eg_req_func(protocols: List["EntanglementProtocol"],
                args: Arguments) -> "EntanglementGenerationA":
    """Function used by `eg_rule_action2` function for selecting generation
    protocols on the remote node

    """
    name = args["name"]
    reservation = args["reservation"]
    for protocol in protocols:
        if (isinstance(protocol, EntanglementGenerationA)
                and protocol.remote_node_name == name
                and protocol.rule.get_reservation() == reservation):
            return protocol


def eg_rule_action2(memories_info: List["MemoryInfo"], args: Arguments):
    """Action function used by entanglement generation protocol on nodes except
    the responder

    """
    mid = args["mid"]
    path = args["path"]
    index = args["index"]
    memories = [info.memory for info in memories_info]
    memory = memories[0]
    protocol = EntanglementGenerationA(None, "EGA." + memory.name, mid,
                                       path[index + 1], memory)
    req_args = {"name": args["name"], "reservation": args["reservation"]}
    return protocol, [path[index + 1]], [eg_req_func], [req_args]


def ep_rule_condition1(memory_info: "MemoryInfo", manager: "MemoryManager",
                       args: Arguments):
    """Condition function used by BBPSSW protocol on nodes except the initiator

    """
    memory_indices = args["memory_indices"]
    reservation = args["reservation"]
    if (memory_info.index in memory_indices
            and memory_info.state == "ENTANGLED"
            and memory_info.fidelity < reservation.fidelity):
        for info in manager:
            if (info != memory_info and info.index in memory_indices
                    and info.state == "ENTANGLED"
                    and info.remote_node == memory_info.remote_node
                    and info.fidelity == memory_info.fidelity):
                assert memory_info.remote_memo != info.remote_memo
                return [memory_info, info]
    return []


def ep_req_func1(protocols, args: Arguments) -> "BBPSSW":
    """Function used by `ep_rule_action1` for selecting purification protocols
    on the remote node

    """
    remote0 = args["remote0"]
    remote1 = args["remote1"]

    _protocols = []
    for protocol in protocols:
        if not isinstance(protocol, BBPSSW):
            continue

        if protocol.kept_memo.name == remote0:
            _protocols.insert(0, protocol)
        if protocol.kept_memo.name == remote1:
            _protocols.insert(1, protocol)

    if len(_protocols) != 2:
        return None

    protocols.remove(_protocols[1])
    _protocols[1].rule.protocols.remove(_protocols[1])
    _protocols[1].kept_memo.detach(_protocols[1])
    _protocols[0].meas_memo = _protocols[1].kept_memo
    _protocols[0].memories = [_protocols[0].kept_memo,
                              _protocols[0].meas_memo]
    _protocols[0].name = _protocols[0].name + "." + _protocols[
        0].meas_memo.name
    _protocols[0].meas_memo.attach(_protocols[0])

    return _protocols[0]


def ep_rule_action1(memories_info: List["MemoryInfo"], args: Arguments):
    """Action function used by BBPSSW protocol on nodes except the
    responder node

    """
    memories = [info.memory for info in memories_info]
    name = "EP.%s.%s" % (memories[0].name, memories[1].name)
    protocol = BBPSSW(None, name, memories[0], memories[1])
    dsts = [memories_info[0].remote_node]
    req_funcs = [ep_req_func1]
    req_args = [{"remote0": memories_info[0].remote_memo,
                 "remote1": memories_info[1].remote_memo}, ]
    return protocol, dsts, req_funcs, req_args


def ep_rule_condition2(memory_info: "MemoryInfo", manager: "MemoryManager",
                       args: Arguments) -> List["MemoryInfo"]:
    """Condition function used by BBPSSW protocol on nodes except the responder

    """
    memory_indices = args["memory_indices"]
    fidelity = args["fidelity"]

    if (memory_info.index in memory_indices
            and memory_info.state == "ENTANGLED"
            and memory_info.fidelity < fidelity):
        return [memory_info]
    return []


def ep_rule_action2(memories_info: List["MemoryInfo"], args: Arguments):
    """Action function used by BBPSSW protocol on nodes except the responder

    """
    memories = [info.memory for info in memories_info]
    name = "EP.%s" % memories[0].name
    protocol = BBPSSW(None, name, memories[0], None)
    return protocol, [None], [None], [None]


def es_rule_actionB(memories_info: List["MemoryInfo"], args: Arguments):
    """Action function used by EntanglementSwappingB protocol

    """
    memories = [info.memory for info in memories_info]
    memory = memories[0]
    protocol = EntanglementSwappingB(None, "ESB." + memory.name, memory)
    return protocol, [None], [None], [None]


def es_rule_conditionB1(memory_info: "MemoryInfo", manager: "MemoryManager", args: Arguments):
    """Condition function used by EntanglementSwappingB protocol on nodes of either responder or initiator
    """
    memory_indices = args["memory_indices"]
    target_remote = args["target_remote"]
    fidelity = args["fidelity"]
    if (memory_info.state == "ENTANGLED"
            and memory_info.index in memory_indices
            # and memory_info.remote_node != path[-1]
            and memory_info.remote_node != target_remote
            # and memory_info.fidelity >= reservation.fidelity):
            and memory_info.fidelity >= fidelity):
        return [memory_info]
    else:
        return []


def es_rule_conditionA(memory_info: "MemoryInfo", manager: "MemoryManager", args: Arguments):
    """Condition function used by EntanglementSwappingA protocol on nodes
    """
    memory_indices = args["memory_indices"]
    left = args["left"]
    right = args["right"]
    fidelity = args["fidelity"]
    if (memory_info.state == "ENTANGLED"
            and memory_info.index in memory_indices
            and memory_info.remote_node == left
            and memory_info.fidelity >= fidelity):
        for info in manager:
            if (info.state == "ENTANGLED"
                    and info.index in memory_indices
                    and info.remote_node == right
                    and info.fidelity >= fidelity):
                return [memory_info, info]
    elif (memory_info.state == "ENTANGLED"
          and memory_info.index in memory_indices
          and memory_info.remote_node == right
          and memory_info.fidelity >= fidelity):
        for info in manager:
            if (info.state == "ENTANGLED"
                    and info.index in memory_indices
                    and info.remote_node == left
                    and info.fidelity >= fidelity):
                return [memory_info, info]
    return []


def es_req_func(protocols: List["EntanglementProtocol"], args: Arguments) -> "EntanglementSwappingB":
    """Function used by `es_rule_actionA` for selecting swapping protocols on the remote node
    """
    target_memo = args["target_memo"]
    for protocol in protocols:
        if (isinstance(protocol, EntanglementSwappingB)
                # and protocol.memory.name == memories_info[0].remote_memo):
                and protocol.memory.name == target_memo):
            return protocol


def es_rule_actionA(memories_info: List["MemoryInfo"], args: Arguments):
    """Action function used by EntanglementSwappingA protocol on nodes
    """
    es_succ_prob = args["es_succ_prob"]
    es_degradation = args["es_degradation"]
    memories = [info.memory for info in memories_info]
    protocol = EntanglementSwappingA(None, "ESA.%s.%s" % (memories[0].name,
                                                          memories[1].name),
                                     memories[0], memories[1],
                                     success_prob=es_succ_prob,
                                     degradation=es_degradation)
    dsts = [info.remote_node for info in memories_info]
    req_funcs = [es_req_func, es_req_func]
    req_args = [{"target_memo": memories_info[0].remote_memo},
                {"target_memo": memories_info[1].remote_memo}]
    return protocol, dsts, req_funcs, req_args


def es_rule_conditionB2(memory_info: "MemoryInfo", manager: "MemoryManager", args: Arguments) -> List["MemoryInfo"]:
    """Condition function used by EntanglementSwappingB protocol on intermediate nodes of path
    """
    memory_indices = args["memory_indices"]
    left = args["left"]
    right = args["right"]
    fidelity = args["fidelity"]
    if (memory_info.state == "ENTANGLED"
            and memory_info.index in memory_indices
            and memory_info.remote_node not in [left, right]
            and memory_info.fidelity >= fidelity):
        return [memory_info]
    else:
        return []


def create_rules_es_right_to_left(self, path: List[str], reservation: "Reservation") -> List["Rule"]:
    """Method to create rules for a successful request.

    Rules are used to direct the flow of information/entanglement in the resource manager.

    Args:
        path (List[str]): list of node names in entanglement path.
        reservation (Reservation): approved reservation.

    Returns:
        List[Rule]: list of rules created by the method.
    """

    rules = []
    memory_indices = []
    for card in self.timecards:
        memory_indices.append(card.memory_index)
        """if reservation in card.reservations:
            memory_indices.append(card.memory_index)"""

    # create rules for entanglement generation
    index = path.index(self.own.name)
    #print(memory_indices)
    if index > 0:
        condition_args = {"memory_indices": memory_indices[:MAP[index]]}
        action_args = {"mid": self.own.map_to_middle_node[path[index - 1]],
                        "path": path, "index": index}
        rule = Rule(10, eg_rule_action1, eg_rule_condition, action_args, condition_args)
        rules.append(rule)
        #print("condition args: <--",condition_args)
    if index < len(path) - 1:
        if index == 0:
            condition_args = {"memory_indices": memory_indices[:MAP[index]]}
        else:
            condition_args = {"memory_indices":
                                    memory_indices[MAP[index]:]}

        action_args = {"mid": self.own.map_to_middle_node[path[index + 1]],
                        "path": path, "index": index, "name": self.own.name,
                        "reservation": reservation}
        rule = Rule(10, eg_rule_action2, eg_rule_condition, action_args, condition_args)
        rules.append(rule)
        #print("condition args -->: ",condition_args)
    # create rules for entanglement purification
    if index > 0:
        condition_args = {"memory_indices":
                                memory_indices[:MAP[index]],
                            "reservation": reservation}
        action_args = {}
        rule = Rule(10, ep_rule_action1, ep_rule_condition1, action_args, condition_args)
        rules.append(rule)

    if index < len(path) - 1:
        if index == 0:
            condition_args = {"memory_indices": memory_indices,
                                "fidelity": reservation.fidelity}
        else:
            condition_args = {"memory_indices": memory_indices[MAP[index]:],
                                "fidelity": reservation.fidelity}

        action_args = {}
        rule = Rule(10, ep_rule_action2, ep_rule_condition2, action_args, condition_args)
        rules.append(rule)

    # create rules for entanglement swapping
    if index == 0:
        condition_args = {"memory_indices": memory_indices,
                            "target_remote": path[-1],
                            "fidelity": reservation.fidelity}
        action_args = {}
        rule = Rule(10, es_rule_actionB, es_rule_conditionB1, action_args, condition_args)
        rules.append(rule)

    elif index == len(path) - 1:
        action_args = {}
        condition_args = {"memory_indices": memory_indices,
                            "target_remote": path[0],
                            "fidelity": reservation.fidelity}
        rule = Rule(10, es_rule_actionB, es_rule_conditionB1, action_args, condition_args)
        rules.append(rule)

    else:
        _path = path[:]
        while _path.index(self.own.name) % 2 == 1 and len(_path)>3:
            new_path = []
            for i, n in enumerate(_path):
                if i % 2 == 1 or i == 0:
                    new_path.append(n)
            _path = new_path
        _index = _path.index(self.own.name)
        left, right = _path[_index - 1], _path[_index + 1]

        condition_args = {"memory_indices": memory_indices,
                            "left": left,
                            "right": right,
                            "fidelity": reservation.fidelity}
        action_args = {"es_succ_prob": self.es_succ_prob,
                        "es_degradation": self.es_degradation}
        rule = Rule(10, es_rule_actionA, es_rule_conditionA, action_args, condition_args)
        rules.append(rule)

        action_args = {}
        rule = Rule(10, es_rule_actionB, es_rule_conditionB2, action_args, condition_args)
        rules.append(rule)

    for rule in rules:
        rule.set_reservation(reservation)

    return rules

def create_rules_es_right_to_left1(self, path: List[str], reservation: "Reservation") -> List["Rule"]:
    """Method to create rules for a successful request.

    Rules are used to direct the flow of information/entanglement in the resource manager.

    Args:
        path (List[str]): list of node names in entanglement path.
        reservation (Reservation): approved reservation.

    Returns:
        List[Rule]: list of rules created by the method.
    """
    path = path[::-1]
    rules = []
    memory_indices = []
    for card in self.timecards:
        if reservation in card.reservations:
            memory_indices.append(card.memory_index)

    # create rules for entanglement generation
    index = path.index(self.own.name)
    if index > 0:
        condition_args = {"memory_indices": memory_indices[:reservation.memory_size]}
        action_args = {"mid": self.own.map_to_middle_node[path[index - 1]],
                        "path": path, "index": index}
        rule = Rule(10, eg_rule_action1, eg_rule_condition, action_args, condition_args)
        rules.append(rule)

    if index < len(path) - 1:
        if index == 0:
            condition_args = {"memory_indices": memory_indices[:reservation.memory_size]}
        else:
            condition_args = {"memory_indices":
                                    memory_indices[reservation.memory_size:]}

        action_args = {"mid": self.own.map_to_middle_node[path[index + 1]],
                        "path": path, "index": index, "name": self.own.name,
                        "reservation": reservation}
        rule = Rule(10, eg_rule_action2, eg_rule_condition, action_args, condition_args)
        rules.append(rule)

    # create rules for entanglement purification
    if index > 0:
        condition_args = {"memory_indices":
                                memory_indices[:reservation.memory_size],
                            "reservation": reservation}
        action_args = {}
        rule = Rule(10, ep_rule_action1, ep_rule_condition1, action_args, condition_args)
        rules.append(rule)

    if index < len(path) - 1:
        if index == 0:
            condition_args = {"memory_indices": memory_indices,
                                "fidelity": reservation.fidelity}
        else:
            condition_args = {"memory_indices": memory_indices[reservation.memory_size:],
                                "fidelity": reservation.fidelity}

        action_args = {}
        rule = Rule(10, ep_rule_action2, ep_rule_condition2, action_args, condition_args)
        rules.append(rule)

    # create rules for entanglement swapping
    if index == 0:
        condition_args = {"memory_indices": memory_indices,
                            "target_remote": path[-1],
                            "fidelity": reservation.fidelity}
        action_args = {}
        rule = Rule(10, es_rule_actionB, es_rule_conditionB1, action_args, condition_args)
        rules.append(rule)

    elif index == len(path) - 1:
        action_args = {}
        condition_args = {"memory_indices": memory_indices,
                            "target_remote": path[0],
                            "fidelity": reservation.fidelity}
        rule = Rule(10, es_rule_actionB, es_rule_conditionB1, action_args, condition_args)
        rules.append(rule)

    else:
        _path = path[:]
        while _path.index(self.own.name) % 2 == 0:
            new_path = []
            for i, n in enumerate(_path):
                if i % 2 == 0 or i == len(_path) - 1:
                    new_path.append(n)
            _path = new_path
        _index = _path.index(self.own.name)
        left, right = _path[_index - 1], _path[_index + 1]

        condition_args = {"memory_indices": memory_indices,
                            "left": left,
                            "right": right,
                            "fidelity": reservation.fidelity}
        action_args = {"es_succ_prob": self.es_succ_prob,
                        "es_degradation": self.es_degradation}
        rule = Rule(10, es_rule_actionA, es_rule_conditionA, action_args, condition_args)
        rules.append(rule)

        action_args = {}
        rule = Rule(10, es_rule_actionB, es_rule_conditionB2, action_args, condition_args)
        rules.append(rule)

    for rule in rules:
        rule.set_reservation(reservation)

    return rules    

def create_rules_es_left_to_right(self, path: List[str], reservation: "Reservation") -> List["Rule"]:
    """Method to create rules for a successful request.

    Rules are used to direct the flow of information/entanglement in the resource manager.

    Args:
        path (List[str]): list of node names in entanglement path.
        reservation (Reservation): approved reservation.

    Returns:
        List[Rule]: list of rules created by the method.
    """
    rules = []
    memory_indices = []
    for card in self.timecards:
        memory_indices.append(card.memory_index)
        """if reservation in card.reservations:
            memory_indices.append(card.memory_index)"""

    # create rules for entanglement generation
    index = path.index(self.own.name)
    #print(memory_indices)
    if index > 0:
        condition_args = {"memory_indices": memory_indices[:MAP[index]]}
        action_args = {"mid": self.own.map_to_middle_node[path[index - 1]],
                        "path": path, "index": index}
        rule = Rule(10, eg_rule_action1, eg_rule_condition, action_args, condition_args)
        rules.append(rule)
        #print("condition args: <--",condition_args)
    if index < len(path) - 1:
        if index == 0:
            condition_args = {"memory_indices": memory_indices[:MAP[index]]}
        else:
            condition_args = {"memory_indices":
                                    memory_indices[MAP[index]:]}

        action_args = {"mid": self.own.map_to_middle_node[path[index + 1]],
                        "path": path, "index": index, "name": self.own.name,
                        "reservation": reservation}
        rule = Rule(10, eg_rule_action2, eg_rule_condition, action_args, condition_args)
        rules.append(rule)
        #print("condition args -->: ",condition_args)
    # create rules for entanglement purification
    if index > 0:
        condition_args = {"memory_indices":
                                memory_indices[:MAP[index]],
                            "reservation": reservation}
        action_args = {}
        rule = Rule(10, ep_rule_action1, ep_rule_condition1, action_args, condition_args)
        rules.append(rule)

    if index < len(path) - 1:
        if index == 0:
            condition_args = {"memory_indices": memory_indices,
                                "fidelity": reservation.fidelity}
        else:
            condition_args = {"memory_indices": memory_indices[MAP[index]:],
                                "fidelity": reservation.fidelity}

        action_args = {}
        rule = Rule(10, ep_rule_action2, ep_rule_condition2, action_args, condition_args)
        rules.append(rule)

    # create rules for entanglement swapping
    if index == 0:
        condition_args = {"memory_indices": memory_indices,
                            "target_remote": path[-1],
                            "fidelity": reservation.fidelity}
        action_args = {}
        rule = Rule(10, es_rule_actionB, es_rule_conditionB1, action_args, condition_args)
        rules.append(rule)

    elif index == len(path) - 1:
        action_args = {}
        condition_args = {"memory_indices": memory_indices,
                            "target_remote": path[0],
                            "fidelity": reservation.fidelity}
        rule = Rule(10, es_rule_actionB, es_rule_conditionB1, action_args, condition_args)
        rules.append(rule)

    else:
        _path = path[:]
        while _path.index(self.own.name) % 2 == 0:
            new_path = []
            for i, n in enumerate(_path):
                if i % 2 == 0 or i == len(_path) - 1:
                    new_path.append(n)
            _path = new_path
        _index = _path.index(self.own.name)
        left, right = _path[_index - 1], _path[_index + 1]

        condition_args = {"memory_indices": memory_indices,
                            "left": left,
                            "right": right,
                            "fidelity": reservation.fidelity}
        action_args = {"es_succ_prob": self.es_succ_prob,
                        "es_degradation": self.es_degradation}
        rule = Rule(10, es_rule_actionA, es_rule_conditionA, action_args, condition_args)
        rules.append(rule)

        action_args = {}
        rule = Rule(10, es_rule_actionB, es_rule_conditionB2, action_args, condition_args)
        rules.append(rule)

    for rule in rules:
        rule.set_reservation(reservation)

    return rules