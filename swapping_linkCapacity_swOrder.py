from sequence.network_management.network_manager import ResourceReservationProtocol
from sequence.network_management.reservation import Reservation
from swaping_rules.ResourceReservationProtocol import create_rules
from sequence.topology.node import QuantumRouter
from sequence.topology.router_net_topo import RouterNetTopo
import json
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from typing import TYPE_CHECKING, List, Dict
import logging
import numpy as np
class RequestApp:
    def __init__(self, node: "QuantumRouter", other: str, memory_size=1, target_fidelity=0.9):
        self.node = node
        self.node.set_app(self)
        self.other = other
        self.memory_size = memory_size
        self.target_fidelity = target_fidelity
        self.eg_counter = 0
        self.reserve_res: bool = None
        self.memory_counter: int = 0
        self.path: List[str] = []
        self.memo_to_reserve: Dict[int, Reservation] = {}

    def start(self):
        now = self.node.timeline.now()
        self.start_time = now + 1e12
        self.end_time = now + 1.5e12
        nm = self.node.network_manager
        nm.request(self.other, start_time=self.start_time, end_time= self.end_time,
                   memory_size=self.memory_size,
                   target_fidelity=self.target_fidelity)
        
        
    def get_reserve_res(self, reservation: "Reservation", result: bool) -> None:
        """Method to receive reservation result from network manager.

        Args:
            reservation (Reservation): reservation that has been completed.
            result (bool): result of the request (approved/rejected).

        Side Effects:
            May schedule a start/retry event based on reservation result.
        """
        self.reserve_res = result
        if result:
            self.schedule_reservation(reservation)

    def add_memo_reserve_map(self, index: int, reservation: "Reservation") -> None:
        self.memo_to_reserve[index] = reservation

    def remove_memo_reserve_map(self, index: int) -> None:
        self.memo_to_reserve.pop(index)

    def get_memory(self, info: "MemoryInfo") -> None:
        """Method to receive entangled memories.

        Will check if the received memory is qualified.
        If it's a qualified memory, the application sets memory to RAW state
        and release back to resource manager.
        The counter of entanglement memories, 'memory_counter', is added.
        Otherwise, the application does not modify the state of memory and
        release back to the resource manager.

        Args:
            info (MemoryInfo): info on the qualified entangled memory.
        """

        if info.state == "ENTANGLED" and info.remote_node == self.other:
            #print("\t{} app received memory {} ENTANGLED at time {}".format(self.node.name, info.index, self.node.timeline.now() * 1e-12))
            self.node.resource_manager.update(None, info.memory, "RAW")
            self.eg_counter +=1

        if info.state != "ENTANGLED":
            return

        if info.index in self.memo_to_reserve:
            reservation = self.memo_to_reserve[info.index]
            if info.remote_node == reservation.initiator and info.fidelity >= reservation.fidelity:
                self.node.resource_manager.update(None, info.memory, "RAW")
            elif info.remote_node == reservation.responder and info.fidelity >= reservation.fidelity:
                self.memory_counter += 1
                self.node.resource_manager.update(None, info.memory, "RAW")

    def get_throughput(self) -> float:
        return self.memory_counter / (self.end_t - self.start_t) * 1e12

    def get_other_reservation(self, reservation: "Reservation") -> None:
        """Method to add the approved reservation that is requested by other
        nodes

        Args:
            reservation (Reservation): reservation that uses the node of application as the responder

        Side Effects:
            Will add calls to `add_memo_reserve_map` and `remove_memo_reserve_map` methods.
        """
        self.schedule_reservation(reservation)

    def schedule_reservation(self, reservation: "Reservation") -> None:
        if reservation.initiator == self.node.name:
            self.path = reservation.path
        for card in self.node.network_manager.protocol_stack[1].timecards:
            if reservation in card.reservations:
                process = Process(self, "add_memo_reserve_map", [card.memory_index, reservation])
                event = Event(reservation.start_time, process)
                self.node.timeline.schedule(event)
                process = Process(self, "remove_memo_reserve_map", [card.memory_index])
                event = Event(reservation.end_time, process)
                self.node.timeline.schedule(event)

    
    def get_throughput(self) -> float:
        return self.eg_counter / (self.end_time - self.start_time) * 1e12

class ResetApp:
    def __init__(self, node, other_node_name, target_fidelity=0.9):
        self.node = node
        self.node.set_app(self)
        self.other_node_name = other_node_name
        self.target_fidelity = target_fidelity

    def get_other_reservation(self, reservation):
        """called when receiving the request from the initiating node.

        For this application, we do not need to do anything.
        """

        pass

    def get_memory(self, info):
        """Similar to the get_memory method of the main application.

        We check if the memory info meets the request first,
        by noting the remote entangled memory and entanglement fidelity.
        We then free the memory for future use.
        """
        if (info.state == "ENTANGLED" and info.remote_node == self.other_node_name
                and info.fidelity > self.target_fidelity):
            self.node.resource_manager.update(None, info.memory, "RAW")

def set_parameters(topology: RouterNetTopo):
    # set memory parameters
    MEMO_FREQ = -1
    MEMO_EXPIRE = 10e-3 #(10 ms)
    MEMO_EFFICIENCY =   1
    MEMO_FIDELITY =0.99
    WAVE_LENGTH = 500
    for node in topology.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        memory_array = node.get_components_by_type("MemoryArray")[0]
        memory_array.update_memory_params("frequency", MEMO_FREQ)
        memory_array.update_memory_params("coherence_time", MEMO_EXPIRE)
        memory_array.update_memory_params("efficiency", MEMO_EFFICIENCY)
        memory_array.update_memory_params("raw_fidelity", MEMO_FIDELITY)
        memory_array.update_memory_params("wavelength", WAVE_LENGTH)

    # set detector parameters
    DETECTOR_EFFICIENCY = 1
    
    for node in topology.get_nodes_by_type(RouterNetTopo.BSM_NODE):
        bsm = node.get_components_by_type("SingleAtomBSM")[0]
        bsm.update_detectors_params("efficiency", DETECTOR_EFFICIENCY)
    # set entanglement swapping parameters
    SWAPPIN_SUCCESS_RATE = 1
    for node in topology.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        node.network_manager.protocol_stack[1].set_swapping_success_rate(SWAPPIN_SUCCESS_RATE)
        
def simulate(network_config,link_capacity=None,swapping_order = None):
    if link_capacity is not None:
        Reservation.link_capacity = link_capacity
        ResourceReservationProtocol.create_rules = create_rules
    if swapping_order is not None: 
        Reservation.swapping_order = swapping_order
        ResourceReservationProtocol.create_rules = create_rules
    
    network_topo = RouterNetTopo(network_config)
    #set the simulation parametters
    set_parameters(network_topo)
    tl = network_topo.get_timeline()
    tl.stop_time = 2e12
    tl.show_progress = False

    start_node_name = "Nodei"
    end_node_name = "Nodej"

    for router in network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        if router.name == start_node_name:
            node1 = router
        elif router.name == end_node_name:
            node2 = router
    target_fidelity = 0
    app_node1 = RequestApp(node1, node2.name,memory_size=1, target_fidelity=target_fidelity)
    app_node2 = ResetApp(node2, node1.name,target_fidelity=target_fidelity)

    tl.init()
    app_node1.start()
    tl.run()
    #print (app_node1.eg_counter)
    rate = app_node1.get_throughput()
    print(rate)
    return (rate)


network_config = "networks/3RoutersMultiChannels.json"

link_capacity = [1,2,3,4]
swap_order = ["r1","r3","r2"]
simulate(network_config,link_capacity,swap_order)
swap_order = ["r1","r2","r3"]
simulate(network_config,link_capacity,swap_order)
swap_order = ["r3","r1","r2"]
simulate(network_config,link_capacity,swap_order)
swap_order = ["r3","r2","r1"]
simulate(network_config,link_capacity,swap_order)


