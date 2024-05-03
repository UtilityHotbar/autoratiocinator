# autoratiocinator
Uses `networkx` for graphs, `openai` for LLMs, and `pyvis` for visualisations. Also uses `tiktoken` for token calculations specific to the OpenAI API, `nltk` for basic NLP procedures, and `numpy` for comparing embeddings.

## Quickstart
Trying to create a reasoning engine based on a knowledge graph. To try a toy example save the openai API key as an environmental variable in shell and run the following commands:
```
/print *
/explain $5
```

## Quick Overview

Papers such as the following [https://arxiv.org/abs/2402.08164v1](https://arxiv.org/abs/2402.08164v1) outline some fundamental limitations with Transformers in fields such as semantic or functional composition. A suggested solution is to incorporate LLMs with knowledge graphs. This is a practical experiment in automatically generating, assembling, and using knowledge graphs to reason about existing texts. The project is **in progress**.

## Methodology and Rationale

The project represents a broader effort to treat LLMs as software tools or functions rather than as agents or black-box intelligences. LLMs are used in many places in this project, but where possible their output is controlled, constrained, and recorded in such a way that humans can explore the conclusions they have come to and why they came to those conclusions. For an example, see the function `get_mc_answer_complex` from `rationcinatorutils.py`, which tries to make an LLM answer a multiple choice question in a way that is reliable and somewhat prompt injection resistant. It does this by inspecting and asserting that the output follows pre-determined rules and raises errors when the LLM refuses to comply.

## Explanation
`network_main.py` contains a CLI based interface for constructing knowledge graphs (MultiDiGraphs in `networkx` where nodes are statements and directed edges infer a dependency relationship between statements. E.g. "Socrates is mortal" depends on "Socrates is a man" and "All men are mortal"). Use `/help` to list all available commands. You can create nodes, delete nodes, create and delete dependencies, visualise graphs, and list dependencies for any given node.

`current_graph.gexf` contains an example knowledge graph with a few statements about Socrates you can experiment with.

`rationcinatorutils.py` contains a series of utility functions (cosine similarity, getting embeddings for text etc.).

`ratiocinator.py` contains the code for a recursive search to determine the dependency tree for any given statement in a knowledge graph. Once this tree is constructed, axioms (bottom level statements) are identified. It is assumed that there is a goal to convince the user of a statement `X`. To do this a method similar to "reverse" breadth-first search is employed where the model begins from the axioms and searches for a "path" of dependent statements leading to the target statement `X`. Thus, it would start by convincing you that "All men are mortal" and "Socrates is a man" before moving to "Socrates is mortal". This follows the standard form for a [syllogistic](https://en.wikipedia.org/wiki/Syllogism) argument. If the user is determined to reject any node, a new path ahead is sought for.

At each depth level the system spawns a new LLM with a local context (what you agreed with or disagreed with on the last level of the dependency tree) with the goal of convincing the user of the current statement. Other single-use queries are used to detect if the user has agreed to that statement or is trying to lead the conversation off track. The result is a form of "guided conversation" where LLMs must follow a pre-defined knowledge structure instead of being given "free reign". This was inspired by [CICERO](https://www.science.org/doi/10.1126/science.ade9097)'s directed LLM.

`topdown_ratiocinator.py` contains the code for a top-down model of explaining a statement. The model takes into account the knowledge graph and argument tree as above but tries to directly explain the target statement (i.e. working from the top down) instead of reasoning from first premises. This process takes into account the local context of each statement, statements immediately below it on the argument graph etc. During the conversation you can invoke "/accept" or "/reject" to move on from any statement and "/query" to dive into any substatement the model considers part of the current conversation.

You can trigger this algorithm for any statement in the current knowledge graph by using the `/explain` command while `network_main.py` is active.

`knowledge_graph.py` contains the tools to turn any text file into a knowledge graph of the arguments in that text file. This process involves rewriting each sentence into a more clear version, splitting it when necessary, associating sentences to prior sentences (both immediately and further before) via a series of comparisons, and generating a graph based on these results. Substitutions are used to prevent overly similar sentences from occupying distinct nodes in the graph.

