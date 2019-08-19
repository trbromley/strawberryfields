# Copyright 2019 Xanadu Quantum Technologies Inc.
r"""
Dense subgraph identification
=============================

**Module name:** :mod:`glassonion.graph.dense`

.. currentmodule:: glassonion.graph.dense

The frontend module for users to find dense subgraphs. The :func:`find_dense` function
provides approximate solutions to the densest-:math:`k` subgraph problem
:cite:`arrazola2018using`, which is NP-hard. This problem considers an undirected graph :math:`G
= (V, E)` of :math:`N` nodes :math:`V` and a list of edges :math:`E`, and sets the objective of
finding a :math:`k`-vertex subgraph with the greatest density. In this setting, subgraphs
:math:`G[S]` are defined by nodes :math:`S \subset V` and corresponding edges :math:`E_{S}
\subseteq E` that have both endpoints in :math:`S`. The density of a subgraph is given by

.. math:: d(G[S]) = \frac{2 |E_{S}|}{|S|(|S|-1)},

where :math:`|\cdot|` denotes cardinality, and the densest-:math:`k` subgraph problem can be
written succinctly as

.. math:: {\rm argmax}_{S \in \mathcal{S}_{k}} d(G[S])

with :math:`\mathcal{S}_{k}` the set of all possible :math:`k` node subgraphs. This problem grows
combinatorially with :math:`{N \choose k}` and is NP-hard in the worst case.

The :func:`find_dense` function provides access to heuristic algorithms for finding
approximate solutions. At present, random search is the heuristic algorithm provided, accessible
through the :func:`random_search` function. This algorithm proceeds by randomly generating a set
of :math:`k` vertex subgraphs and selecting the densest. Sampling of subgraphs can be achieved
both uniformly at random and also with a quantum sampler programmed to be biased toward
outputting dense subgraphs.

Summary
-------

.. autosummary::
    METHOD_DICT
    OPTIONS_DEFAULTS
    find_dense
    random_search

Code details
------------
"""
from typing import Tuple, Optional
import networkx as nx

import glassonion.sample
import glassonion.graph.resize
import glassonion.graph.sample
import glassonion.graph.utils
from glassonion.graph.utils import graph_type


def find_dense(
    graph: graph_type, nodes: int, iterations: int = 1, options: Optional[dict] = None
) -> Tuple[float, list]:
    """Find a dense subgraph of a given size.

    This function returns the densest `node-induced subgraph
    <http://mathworld.wolfram.com/Vertex-InducedSubgraph.html>`__ of size ``nodes`` after
    multiple repetitions. It uses heuristic optimization that combines search space exploration
    with local searching. The heuristic method can be set with the ``options`` argument. Methods
    can contain stochastic elements, where randomness can come from distributions including GBS.

    All elements of the heuristic can be controlled with the ``options`` argument, which should be a
    dict-of-dicts where the first level specifies the option type as a string-based key,
    with corresponding value being a dictionary of options for that type. The option types are:

    - ``"heuristic"``: specifying options used by optimization heuristic; corresponding
      dictionary of options explained further :ref:`below <heuristic>`
    - ``"backend"``: specifying options used by backend quantum samplers; corresponding
      dictionary of options explained further in :mod:`~glassonion.sample`
    - ``"resize"``: specifying options used by resizing method; corresponding dictionary of
      options explained further in :mod:`~glassonion.graph.resize`
    - ``"sample"``: specifying options used in sampling; corresponding dictionary of options
      explained further in :mod:`~glassonion.graph.sample`

    If unspecified, a default set of options is adopted for a given option type.

    .. _heuristic:

    The options dictionary corresponding to ``"heuristic"`` can contain any of the following:

    .. glossary::

        key: ``"method"``, value: *str* or *callable*
            Value can be either a string selecting from a range of available methods or a
            customized callable function. Options include:

            - ``"random-search"``: a simple random search algorithm where many subgraphs are
              selected and the densest one is chosen (default)
            - *callable*: accepting ``(graph: nx.Graph, nodes: int, iterations: int, options:
              dict)`` as arguments and returning ``Tuple[float, list]`` corresponding to the
              density and list of nodes of the densest subgraph found, see :func:`random_search`
              for an example

    Args:
        graph (graph_type): the input graph
        nodes (int): the size of desired dense subgraph
        iterations (int): number of iterations to use in algorithm
        options (dict[str, dict[str, Any]]): dict-of-dicts specifying options in different parts
            of heuristic search algorithm; defaults to :const:`OPTIONS_DEFAULTS`

    Returns:
        Tuple[float, list]: the density and list of nodes corresponding to the densest subgraph
        found
    """
    options = {**OPTIONS_DEFAULTS, **(options or {})}

    method = options["heuristic"]["method"]

    if not callable(method):
        method = METHOD_DICT[method]

    return method(
        graph=glassonion.graph.utils.to_networkx_graph(graph),
        nodes=nodes,
        iterations=iterations,
        options=options,
    )


def random_search(
    graph: nx.Graph, nodes: int, iterations: int = 1, options: Optional[dict] = None
) -> Tuple[float, list]:
    """Random search algorithm for finding dense subgraphs of a given size.

    The algorithm proceeds by sampling subgraphs according to the
    :func:`~glassonion.graph.sample.sample_subgraphs`. The resultant subgraphs are resized using
    :func:`~glassonion.graph.resize.resize_subgraphs` to be of size ``nodes``. The densest
    subgraph is then selected among all the resultant subgraphs. Specified``options`` must be of
    the form given in :func:`find_dense`.

    Args:
        graph (nx.Graph): the input graph
        nodes (int): the size of desired dense subgraph
        iterations (int): number of iterations to use in algorithm
        options (dict[str, dict[str, Any]]): dict-of-dicts specifying options in different parts
            of heuristic search algorithm; defaults to :const:`OPTIONS_DEFAULTS`

    Returns:
        Tuple[float, list]: the density and list of nodes corresponding to the densest subgraph
        found
    """
    options = {**OPTIONS_DEFAULTS, **(options or {})}

    samples = glassonion.graph.sample.sample_subgraphs(
        graph=graph,
        nodes=nodes,
        samples=iterations,
        sample_options=options["sample"],
        backend_options=options["backend"],
    )

    samples = glassonion.graph.resize.resize_subgraphs(
        subgraphs=samples, graph=graph, target=nodes, resize_options=options["resize"]
    )

    density_and_samples = [(nx.density(graph.subgraph(s)), s) for s in samples]

    return max(density_and_samples)


METHOD_DICT = {"random-search": random_search}
"""Dict[str, func]: Included methods for finding dense subgraphs. The dictionary keys are strings
describing the method, while the dictionary values are callable functions corresponding to the
method."""

OPTIONS_DEFAULTS = {
    "heuristic": {"method": random_search},
    "backend": glassonion.graph.sample.SAMPLE_DEFAULTS,
    "resize": glassonion.graph.resize.RESIZE_DEFAULTS,
    "sample": glassonion.sample.BACKEND_DEFAULTS,
}
"""Dict[str, dict[str, Any]]: Options for dense subgraph identification heuristics. Composed of a
dictionary of dictionaries with the first level specifying the option type, selected from keys
``"heuristic"``, ``"backend"``, ``"resize"``, and ``"sample"``, with the corresponding value a
dictionary of options for that type.
"""
