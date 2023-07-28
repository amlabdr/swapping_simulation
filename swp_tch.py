from sequence.kernel.process import Process
from sequence.kernel.event import Event
from sequence.topology.router_net_topo import RouterNetTopo
import json
import numpy as np

class RequestApp:
    def __init__(self, node: "QuantumRouter", other: str, memory_size=1, target_fidelity=0.9):
        self.node = node
        self.node.set_app(self)
        self.other = other
        self.memory_size = memory_size
        self.target_fidelity = target_fidelity
        self.eg_counter = 0

    def start(self):
        now = self.node.timeline.now()
        self.start_time = now + 1e12
        self.end_time = now + 1.5e12
        nm = self.node.network_manager
        nm.request(self.other, start_time=self.start_time, end_time= self.end_time,
                   memory_size=self.memory_size,
                   target_fidelity=self.target_fidelity)
        
    def get_reserve_res(self, reservation: "Reservation", result: bool):
        if result:
            pass
            #print("Reservation approved at time", self.node.timeline.now() * 1e-12)
        else:
            pass
            #print("Reservation failed at time", self.node.timeline.now() * 1e-12)

    def get_memory(self, info: "MemoryInfo"):
        if info.state == "ENTANGLED" and info.remote_node == self.other:
            #print("\t{} app received memory {} ENTANGLED at time {}".format(self.node.name, info.index, self.node.timeline.now() * 1e-12))
            self.node.resource_manager.update(None, info.memory, "RAW")
            self.eg_counter +=1
    
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
    with open('networks/2Routers.json', 'w') as file:
        json.dump(data, file, indent=2)


def set_parameters(topology: RouterNetTopo, tch):
    # set memory parameters
    MEMO_FREQ = -1
    MEMO_EXPIRE = tch
    MEMO_EFFICIENCY =   0.53
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
    SWAP_SUCC_PROB = 1
    for node in topology.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        node.network_manager.protocol_stack[1].set_swapping_success_rate(SWAP_SUCC_PROB)
    

def simulate(network_config,distance, tch):
    set_distances(network_config, distance)
    network_topo = RouterNetTopo(network_config)
    #set the simulation parametters
    set_parameters(network_topo,tch)
    tl = network_topo.get_timeline()
    tl.stop_time = 2e12
    tl.show_progress = False

    start_node_name = "Nodei"
    end_node_name = "Nodej"
    node1 = node2 = None

    for router in network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        if router.name == start_node_name:
            node1 = router
        elif router.name == end_node_name:
            node2 = router
    target_fidelity = 0
    app_node1 = RequestApp(node1, node2.name,target_fidelity=target_fidelity)
    app_node2 = ResetApp(node2, node1.name,target_fidelity=target_fidelity)

    tl.init()
    app_node1.start()
    tl.run()
    print (app_node1.eg_counter)
    rate = app_node1.get_throughput()
    return (rate)

final_distance = 200000
distances = list(range(1000, final_distance+1, 10000))
#distances = [10000]
network_config = "networks/2Routers.json"
TCHdict = {"inf":0,"1ms":1e-3,"10ms":10e-3,"100ms":100e-3,"1s":1}
for tch in TCHdict:
    print("simulation fr tch:", tch)
    rates = []
    for L in distances:
        rates.append(simulate(network_config, L,TCHdict[tch]))
        print("Simulation done for ", L)
        filename =  'data/rates/' +  ('network(N=%s)(cohTime=%s).txt' 
                                        % ( network_config.split('/')[-1],
                                            '%.3fms' % ( TCHdict[tch] / 1e-3 ) if TCHdict[tch] > 0.0 else 'inf'
                                            ))
        # Save rates to a file
        np.savetxt(filename, rates)