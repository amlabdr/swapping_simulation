from typing import List

def create_rules(index: int, path: List[str], swapping_order: List[str]) -> tuple:
    # create rules for entanglement swapping
    if index == 0:
        return None, None
    elif index == len(path) - 1:
        return None, None
    else:
        # Modified logic based on the specified order
        node_index_in_order = swapping_order.index(path[index])
        
        # For the last node in the order list
        if node_index_in_order == len(swapping_order) - 1:
            left, right = path[0], path[-1]
        else:
            # Find the nearest node from the left that is not before the current node in the order list
            left = next((node for node in reversed(path[:index]) if node not in swapping_order[:node_index_in_order]), None)

            # Find the nearest node from the right that is not before the current node in the order list
            right = next((node for node in path[index + 1:] if node not in swapping_order[:node_index_in_order]), None)

        return left, right

order_list = ["v2", "v4", "v6", "v3", "v5"]
path = ["v1", "v2", "v3", "v4", "v5", "v6", "v7"]

for node_index in range(len(path)):
    left, right = create_rules(node_index, path, order_list)
    print(f"For node {path[node_index]}: Left = {left}, Right = {right}")
