# autoratiocinator
Uses `networkx` for graphs, `openai` for LLMs, and `pyvis` for visualisations.

## Quickstart
Trying to create a reasoning engine based on a knowledge graph. To try a toy example save the openai API key as an environmental variable in shell and run the following commands:
```
/print *
/explain $5
```

## Explanation
`network_main.py` contains a CLI based interface for constructing knowledge graphs (MultiDiGraphs in `networkx` where nodes are statements and directed edges infer a dependency relationship between statements. E.g. "Socrates is mortal" depends on "Socrates is a man" and "All men are mortal"). Use `/help` to list all available commands. You can create nodes, delete nodes, create and delete dependencies, visualise graphs, and list dependencies for any given node.

`current_graph.gexf` contains an example knowledge graph with a few statements about Socrates you can experiment with.

`autoratiocinator.py` contains the code for a recursive search to determine the dependency tree for any given statement in a knowledge graph. Once this tree is constructed, axioms (bottom level statements) are identified. It is assumed that there is a goal to convince the user of a statement `X`. To do this a method similar to "reverse" breadth-first search is employed where the model begins from the axioms and searches for a "path" of dependent statements leading to the target statement `X`. Thus, it would start by convincing you that "All men are mortal" and "Socrates is a man" before moving to "Socrates is mortal". This follows the standard form for a [syllogistic](https://en.wikipedia.org/wiki/Syllogism) argument. You can trigger this algorithm for any statement in the current knowledge graph by using the `/explain` command while `network_main.py` is active.
