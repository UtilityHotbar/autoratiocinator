from openai import OpenAI
import os
import networkx as nx
from constants import *
import time

client = OpenAI(api_key=(os.getenv('OPENAI_API_KEY')))

CONVINCER_PROMPT = 'You are a clever, dedicated, and confident philosopher designed to convince an end user of a hypothesis for the purposes of education. The hypothesis is this statement %STM%. Make your answer concise.\n'
SCRUTINISER_PROMPT = 'You are an attentive, clever, and careful assistant. Your job is to see if the message below is related to the hypothesis "%STM%". This is the statement to analyse: "%CAND%". We need to tell if the statement is related to the hypothesis "%STM%". Output your answer in one word: YES or NO, in all caps.'

def stm_convince_loop(stm, additional_info=''):
    history = []
    # if not stm:
    #     stm = 'Unicorns are real.'
    print('I will now try to convince you of this: %STM%'.replace('%STM%', stm))
    time.sleep(1)
    while True:
        # print(history)
        # input('[PRESS RETURN TO CONTINUE]')
        model_answer_acceptable = False
        tries = 0
        while not model_answer_acceptable:
            completion= client.chat.completions.create(model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": CONVINCER_PROMPT.replace('%STM%', stm)+additional_info},
                {"role": "user", "content": "I don't believe you. Why is this statement true?"}
                ]+history,
            temperature=0.5,
            max_tokens=300)
            candidate = completion.choices[0].message
            verification = client.chat.completions.create(model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SCRUTINISER_PROMPT.replace('%STM%', stm).replace('%CAND%', candidate.content)},
                ]+history,
            temperature=0.5,
            max_tokens=300)
            if verification.choices[0].message.content.lower() == 'yes':
                model_answer_acceptable = True
            else:
                tries += 1
            if tries == 10:
                print('[!] I couldn\'t find an answer that makes sense given your last statement. I\'ll forget the last thing you said.')
                history = history[:-1]
        history.append({'content': candidate.content, 'role': 'system'})
        print(candidate.content)
        user_input = input('>').strip()
        if user_input == '/yes':
            print('[!] Statement Done.')
            return True
        elif user_input == '/no':
            print('[!] Statement Rejected.')
            return False
        elif user_input == '/help':
            print('[?] Try to answer in short sentences. If you are convinced, type "/yes". If you feel there is no way you can be convinced, type "/no". Otherwise, keep talking.')
        else:
            history.append({"role": "user", "content": user_input})

# def get_statements_graph(graph, node, existing_tree=None):
#     statements_tree = nx.DiGraph()
#     if not existing_tree:
#         statements_tree.add_node(node)
#     for source in graph.successors(node):
#         if graph.has_edge(node, source, key=SOURCE) and source != node:
#             statements_tree.add_node(source)
#             statements_tree.add_edge(node, source)
#             statements_tree = nx.compose(statements_tree, get_statements_graph(graph, source, statements_tree))
#     return statements_tree

def get_arg_stack(graph, node, dist=0):
    steps = {NODE: node, CHILDREN: {}, DIST: dist}
    for succ in graph.successors(node):
        if succ != node:
            desc = list(graph.successors(succ))
            if len(desc) > 0 and dist < DEPTH_LIMIT:
                steps[CHILDREN][succ] = get_arg_stack(graph, succ, dist+1)
            else:
                steps[CHILDREN][succ] = {NODE: succ, CHILDREN: AXIOM, DIST: dist}
    return steps

def tree_convince_loop(graph, node):
    # statements_graph = get_statements_graph(graph, node)
    # print(statements_graph)
    arg_stack = get_arg_stack(graph, node)
    print(arg_stack)
    ## Now we do depth first search
    if dfs_convincer(arg_stack, graph):
        print('[!] Goal complete.')
    else:
        print('[!] Goal failed.')

def convert_prior_results(yes_nos, graph):
    summary = ''
    for item in yes_nos:
        if yes_nos[item]:
            summary += f'The user already believes that {graph.nodes[item]["label"]}.\n'
        else:
            summary += f'The user does not believe that {graph.nodes[item]["label"]}.\n'
    return summary

def dfs_convincer(arg_stack, graph):
    if arg_stack[CHILDREN] != AXIOM:
        # print('going deeper')
        yes_nos = {}
        totals = len(arg_stack[CHILDREN])
        conviction_count = 0
        tried_skip = False
        for sub_argument in arg_stack[CHILDREN]:
            sub_argument_content = arg_stack[CHILDREN][sub_argument]
            if dfs_convincer(sub_argument_content, graph):
                yes_nos[sub_argument] = True
                conviction_count += 1
                if conviction_count >= round(totals*SKIP_VAL):
                    tried_skip = True
                    if stm_convince_loop(graph.nodes[arg_stack[NODE]]['label'], additional_info=convert_prior_results(yes_nos, graph)):
                        return True
            else:
                yes_nos[sub_argument] = False
        if not tried_skip:
            print(graph[arg_stack[NODE]])
            if stm_convince_loop(graph.nodes[arg_stack[NODE]]['label'], additional_info=convert_prior_results(yes_nos, graph)):
                return True
            else:
                return False
        else:
            return False
    else:
        # print('At axiom level')
        if stm_convince_loop(graph.nodes[arg_stack[NODE]]['label']):
            return True
        else:
            return False

def dumb_convince_loop(list_of_stms):
    for stm in list_of_stms:
        stm_convince_loop(stm)


