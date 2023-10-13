from sequence.kernel.timeline import Timeline
from sequence.topology.router_net_topo import RouterNetTopo
from sequence.app.random_request import RandomRequestApp

from sequence.network_management.network_manager import ResourceReservationProtocol
from sequence.network_management.reservation import Reservation
from swaping_rules.ResourceReservationProtocol import create_rules_es_left_to_right, create_rules_es_right_to_left
from sequence.topology.node import QuantumRouter
from sequence.topology.router_net_topo import RouterNetTopo
import json
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from typing import TYPE_CHECKING, List, Dict
import logging
"""
# Configure the logging
log_filename = 'entanglement_log.log'
logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create a logger
logger = logging.getLogger(__name__)
"""
# Define a custom filter
class EntanglementFilter(logging.Filter):
    def filter(self, record):
        return "successful entanglement" in record.getMessage()

# Add the filter to the logger
#logger.addFilter(EntanglementFilter())
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

def print_node_info(node):
    print(node.name," Memories")
    print("Index:\tEntangled Node:\tFidelity:\tEntanglement Time:")
    for i, info in enumerate(node.resource_manager.memory_manager):
        print("{:6}\t{:15}\t{:9}\t{}".format(str(i), str(info.remote_node),
                                             str(info.fidelity),
                                             str(info.entangle_time * 1e-12)))

def set_distances(network_config, total_distance):
    # Load the JSON file
    
    with open(network_config) as file:
        data = json.load(file)
    qconnections = data['qconnections']
    cconnections = data['cconnections']
    hubs_number = len(data['nodes'])
    DISTANCE = total_distance/(hubs_number-1)
    
    # Update qconnections distances
    for qconnection in qconnections:
        qconnection['distance'] = DISTANCE
    
    # Update cconnections distances
    for cconnection in cconnections:
        cconnection['distance'] = DISTANCE

    # Save the updated JSON file
    with open(network_config, 'w') as file:
        json.dump(data, file, indent=2)

def set_parameters(topology: RouterNetTopo):
    # set memory parameters
    MEMO_FREQ = -1
    MEMO_EXPIRE = 10e-3 #(10 ms)
    MEMO_EFFICIENCY =   1
    MEMO_FIDELITY =0.99
    WAVE_LENGTH = 500
    i=0
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
        
def simulate(network_config,distance,swapping_order = None):
    set_distances(network_config, distance)
    if swapping_orders is not None:
        ResourceReservationProtocol.create_rules = swapping_order
    network_topo = RouterNetTopo(network_config)
    #set the simulation parametters
    set_parameters(network_topo)
    

    start_node_name = "Nodei"
    end_node_name = "Nodej"
    router1_name = "r1"
    router2_name = "r2"
    node1 = node2 = r1 = r2 =None

    for router in network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        if router.name == start_node_name:
            node1 = router
        elif router.name == end_node_name:
            node2 = router
        elif router.name == router1_name:
            r1 = router
        elif router.name == router2_name:
            r2 = router
    target_fidelity = 0
    
    apps = []
    app_node1_r1 = RandomRequestApp(node1, [r1.name], 0,
                               min_dur=1, max_dur=2e13, min_size=1,
                               max_size=2, min_fidelity=0.5, max_fidelity=1.0)
    apps.append(app_node1_r1)
    app_node1_r1.start()


    app_r1_r2 = RandomRequestApp(r1, [r2.name], 0,
                               min_dur=1, max_dur=2e13, min_size=2,
                               max_size=3, min_fidelity=0.5, max_fidelity=1.0)
    apps.append(app_r1_r2)
    app_r1_r2.start()

    app_r2_node2 = RandomRequestApp(r2, [node2.name], 0,
                               min_dur=1, max_dur=2e13, min_size=4,
                               max_size=5, min_fidelity=0.5, max_fidelity=1.0)
    apps.append(app_r2_node2)
    app_r2_node2.start()

    """app_node2 = RandomRequestApp(node2, [r2.name,node1.name], 0,
                               min_dur=1, max_dur=2e13, min_size=5,
                               max_size=6, min_fidelity=0.5, max_fidelity=1.0)
    apps.append(app_node2)
    app_node2.start()"""

    app_node1_node2 = RandomRequestApp(node1, [node2.name], 0,
                               min_dur=1, max_dur=2e13, min_size=1,
                               max_size=2, min_fidelity=0.5, max_fidelity=1.0)
    apps.append(app_node1_node2)
    app_node1_node2.start()

    app_node2_reset = ResetApp(node2, node1.name,target_fidelity=target_fidelity)
    
    tl = network_topo.get_timeline()
    tl.stop_time = 2e12
    tl.show_progress = False
    tl.init()
    tl.run()
    ####
    print_node_info(node1)
    print_node_info(r1)
    print_node_info(r2)
    print_node_info(node2)
    
    #print (app_node2.eg_counter)
    #rate = app_node1.get_throughput()
    #print(rate)
    #return ("rate",rate)

final_distance = 200000
distances = list(range(1000, final_distance+1, 10000))
distances = [10000]
network_config = "networks/2RoutersMultiChannels.json"

#network_config = "networks/adjacents.json"
#network_config = "networks/1Routers.json"
swapping_orders = {"left_to_right":create_rules_es_left_to_right,"right_to_left":create_rules_es_right_to_left}
#swapping_orders = {"left_to_right":create_rules_es_left_to_right}

for swp_order in swapping_orders:
    print("simulation fr swapping order:", swp_order)
    rates = []
    for L in distances:
        rates.append(simulate(network_config, L,swapping_orders[swp_order]))
        #simulate(network_config, L)
        print("Simulation done for ", L)
        filename =  'data/rates/' +  ('network(N=%s)(Swapping_order=%s).txt' 
                                        % ( network_config.split('/')[-1],
                                            swp_order
                                            ))
        # Save rates to a file
        #np.savetxt(filename, rates)