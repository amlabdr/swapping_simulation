from sequence.topology.node import Node
from sequence.components.memory import MemoryArray
from sequence.resource_management.resource_manager import ResourceManager
from typing import List

class RouterNode(Node):
    def __init__(self, name, tl, memo_size=50):
        super().__init__(name, tl)
        memory_array_name = name + ".MemoryArray"
        memory_array = MemoryArray(memory_array_name, tl, num_memories=memo_size)
        memory_array.add_receiver(self)
        self.add_component(memory_array)

        self.resource_manager = ResourceManager(self, memory_array_name)

    def receive_message(self, src: str, msg: "Message") -> None:
        if msg.receiver == "resource_manager":
            self.resource_manager.received_message(src, msg)
        else:
            if msg.receiver is None:
                matching = [p for p in self.protocols if type(p) == msg.protocol_type]
                for p in matching:
                    p.received_message(src, msg)
            else:
                for protocol in self.protocols:
                    if protocol.name == msg.receiver:
                        protocol.received_message(src, msg)
                        break

    def get_idle_memory(self, info: "MemoryInfo") -> None:
        pass

    def get(self, photon: "Photon", **kwargs):
        dst = kwargs['dst']
        self.send_qubit(dst, photon)

def eg_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager", args):
    index_upper = args["index_upper"]
    index_lower = args["index_lower"]
    if memory_info.state == "RAW" \
            and index_lower <= memory_info.index <= index_upper:
        return [memory_info]
    else:
        return []
# args = {"index_lower": 0, "index_upper": 9}

from sequence.entanglement_management.generation import EntanglementGenerationA

def eg_req_func(protocols, args):
    remote_node = args["remote_node"]
    index_upper = args["index_upper"]
    index_lower = args["index_lower"]

    for protocol in protocols:
        if not isinstance(protocol, EntanglementGenerationA):
            continue
        mem_arr = protocol.own.get_components_by_type("MemoryArray")[0]
        if protocol.remote_node_name == remote_node and \
                index_lower <= mem_arr.memories.index(protocol.memory) <= index_upper:
            return protocol


def eg_rule_action1(memories_info: List["MemoryInfo"], args):
    mid_name = args["mid_name"]
    other_name = args["other_name"]

    memories = [info.memory for info in memories_info]
    memory = memories[0]
    protocol = EntanglementGenerationA(None, "EGA." + memory.name, mid_name,
                                       other_name,
                                       memory)
    req_args = {"remote_node": args["node_name"],
                "index_upper": args["index_upper"],
                "index_lower": args["index_lower"]}
    return [protocol, [other_name], [eg_req_func], [req_args]]


def eg_rule_action2(memories_info: List["MemoryInfo"], args):
    mid_name = args["mid_name"]
    other_name = args["other_name"]
    memories = [info.memory for info in memories_info]
    memory = memories[0]
    protocol = EntanglementGenerationA(None, "EGA." + memory.name,
                                       mid_name, other_name, memory)
    return [protocol, [None], [None], [None]]

from sequence.kernel.timeline import Timeline
from sequence.topology.node import BSMNode
from sequence.components.optical_channel import ClassicalChannel, QuantumChannel

runtime = 10e12
tl = Timeline(runtime)

# nodes
r1 = RouterNode("r1", tl, memo_size=20)
r2 = RouterNode("r2", tl, memo_size=40)
r3 = RouterNode("r3", tl, memo_size=10)

m12 = BSMNode("m12", tl, ["r1", "r2"])
m23 = BSMNode("m23", tl, ["r2", "r3"])

node_list = [r1, r2, r3, m12, m23]
for i, node in enumerate(node_list):
    node.set_seed(i)

# create all-to-all classical connections
cc_delay = 1e9
for node1 in node_list:
    for node2 in node_list:
        cc = ClassicalChannel("cc_%s_%s" % (node1.name, node2.name), tl, 1e3, delay=cc_delay)
        cc.set_ends(node1, node2.name)

# create quantum channels linking r1 and r2 to m1
qc_atten = 0
qc_dist = 1e3
qc1 = QuantumChannel("qc_r1_m12", tl, qc_atten, qc_dist)
qc1.set_ends(r1, m12.name)
qc2 = QuantumChannel("qc_r2_m12", tl, qc_atten, qc_dist)
qc2.set_ends(r2, m12.name)
# create quantum channels linking r2 and r3 to m2
qc3 = QuantumChannel("qc_r2_m23", tl, qc_atten, qc_dist)
qc3.set_ends(r2, m23.name)
qc4 = QuantumChannel("qc_r3_m23", tl, qc_atten, qc_dist)
qc4.set_ends(r3, m23.name)


from sequence.resource_management.rule_manager import Rule

tl.init()

# load rules
action_args = {"mid_name": "m12", "other_name": "r2", "node_name": "r1",
               "index_upper": 9, "index_lower": 0}
condition_args = {"index_lower": 0, "index_upper": 9}
rule1 = Rule(10, eg_rule_action1, eg_rule_condition, action_args, condition_args)
r1.resource_manager.load(rule1)
action_args2 = {"mid_name": "m12", "other_name": "r1"}
rule2 = Rule(10, eg_rule_action2, eg_rule_condition, action_args2, condition_args)
r2.resource_manager.load(rule2)

tl.run()

print("Router 1 Memories")
print("Index:\tEntangled Node:\tFidelity:\tEntanglement Time:")
for i, info in enumerate(r1.resource_manager.memory_manager):
    print("{:6}\t{:15}\t{:9}\t{}".format(str(i), str(info.remote_node),
                                         str(info.fidelity), str(info.entangle_time * 1e-12)))