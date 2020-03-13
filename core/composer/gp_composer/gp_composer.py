from copy import deepcopy
from dataclasses import dataclass
from functools import partial
from typing import (
    Callable,
    Optional,
    List
)

from core.composer.chain import Chain
from core.composer.composer import Composer, ComposerRequirements
from core.composer.gp_composer.gp_node import GPNode
from core.composer.node import Node
from core.composer.node import NodeGenerator
from core.composer.optimisers.gp_optimiser import GPChainOptimiser
from core.composer.visualisation import ComposerVisualiser
from core.models.data import InputData


@dataclass
class GPComposerRequirements(ComposerRequirements):
    pop_size: Optional[int] = 50
    num_of_generations: Optional[int] = 50
    crossover_prob: Optional[float] = None
    mutation_prob: Optional[float] = None
    verbose: bool = True


class GPComposer(Composer):
    def compose_chain(self, data: InputData, initial_chain: Optional[Chain],
                      composer_requirements: Optional[GPComposerRequirements],
                      metrics: Optional[Callable]) -> Chain:
        metric_function_for_nodes = partial(self._metric_for_nodes,
                                            metrics, data)
        optimiser = GPChainOptimiser(initial_chain=initial_chain,
                                     requirements=composer_requirements,
                                     primary_node_func=NodeGenerator.primary_node,
                                     secondary_node_func=NodeGenerator.secondary_node)

        best_found, history = optimiser.optimise(metric_function_for_nodes)

        if composer_requirements.is_visualise:
            historical_chains = []
            for historical_data in history:
                historical_nodes_set = GPComposer._tree_to_chain(historical_data[0], data).nodes
                historical_chain = Chain()
                [historical_chain.add_node(nodes) for nodes in historical_nodes_set]
                historical_chains.append(historical_chain)

        historical_fitnesses = [opt_step[1] for opt_step in history]

        if composer_requirements.is_visualise:
            ComposerVisualiser.visualise_history(historical_chains, historical_fitnesses)

        best_chain = GPComposer._tree_to_chain(tree_root=best_found, data=data)
        print("GP composition finished")
        return best_chain

    @staticmethod
    def _tree_to_chain(tree_root: GPNode, data: InputData) -> Chain:
        chain = Chain()
        nodes = GPComposer._flat_nodes_tree(deepcopy(tree_root))
        for node in nodes:
            if node.nodes_from:
                for i in range(len(node.nodes_from)):
                    node.nodes_from[i] = node.nodes_from[i].chain_node
            chain.add_node(node.chain_node)
        chain.reference_data = data
        return chain

    @staticmethod
    def _flat_nodes_tree(node) -> List[Node]:
        if node.nodes_from:
            nodes = []
            for children in node.nodes_from:
                nodes += GPComposer._flat_nodes_tree(children)
            return [node] + nodes
        else:
            return [node]

    @staticmethod
    def _metric_for_nodes(metric_function, data, root: GPNode) -> float:
        chain = GPComposer._tree_to_chain(root, data)
        return metric_function(chain)
