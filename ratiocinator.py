from openai import OpenAI
import os
import networkx as nx
from constants import *
import time

MODEL_NAME = 'gpt-4'
STM_HISTORY = []

client = OpenAI(api_key=(os.getenv('OPENAI_API_KEY')))

CONVINCER_PROMPT = 'You are a clever, dedicated, and confident philosopher designed to convince an end user of a hypothesis for the purposes of education. The hypothesis is this statement %STM%. Make your answer concise.\n'
SCRUTINISER_PROMPT = 'You are an attentive, clever, and careful assistant. Your job is to see if the message below is off topic from a discussion about the statement "%STM%". This is the statement to analyse: "%CAND%". We need to tell if the statement is part of a discussion about "%STM%". Output your answer in one word: YES or NO, in all caps.'

INIT_PROMPT = 'You are a clever teacher teaching a clever student. You want to introduce the topic "%STM%". In a sentence or two say what you would say to introduce the topic. In your response, only include the dialogue surrounded by speech marks.'
BRIDGE_PROMPT = 'You are a clever teacher teaching a student about the statement "%PREV_PROMPT%". You want to switch the topic to something not really related and talk about "%STM%" instead. In a sentence or two say what you would say to change the topic. In your response, only include the dialogue surrounded by speech marks.'
RAISE_LEVEL_PROMPT = 'You are a clever teacher teaching a student about the statement "%PREV_PROMPT%". You want to build on this and talk about the statement "%STM%". In a sentence or two say what you would say to change the topic. In your response, only include the dialogue surrounded by speech marks.'
PROMPT_CONNECT_PROMPT = 'You are a clever teacher with two statements in front of you. Statement one is "%STM1%". Statement two is "%STM2%". Are they related? Answer in one word, yes or no.'

EVALUATOR_PROMPT = 'You are a clever teacher teaching a bright student about the topic "%STM%". They have just given you this response: %RESPONSE%. Is the student confident in their knowledge, resolved about this topic, ready to move on to the next topic? Respond in one word, yes or no.'

def stm_convince_loop(stm, additional_info='', last_prompt=''):
    chosen_start_prompt = INIT_PROMPT

    if not last_prompt:
        last_prompt = 'a topic'
    else:
        connection_verification = client.chat.completions.create(model=MODEL_NAME,
            messages=[
                {"role": "system", "content": PROMPT_CONNECT_PROMPT.replace('%STM1%', last_prompt).replace('%STM2%', stm)},
                ],
            temperature=0.5,
            max_tokens=300)
        if connection_verification.choices[0].message.content.lower().strip('.') == 'yes':
            chosen_start_prompt = RAISE_LEVEL_PROMPT
        else:
            chosen_start_prompt = BRIDGE_PROMPT
    history = []
    # if not stm:
    #     stm = 'Unicorns are real.'
    startoff = client.chat.completions.create(model=MODEL_NAME,
            messages=[
                {"role": "system", "content": chosen_start_prompt.replace('%PREV_PROMPT%', last_prompt).replace('%STM%', stm)},
                ],
            temperature=1.00,
            max_tokens=300)

    startoff_text = startoff.choices[0].message.content.strip("\"")
    history.append({"role": "assistant", "content": startoff_text})
    print(startoff_text)
    time.sleep(1)
    while True:
        # print(history)
        # input('[PRESS RETURN TO CONTINUE]')
        model_answer_acceptable = False
        tries = 0
        while not model_answer_acceptable:
            completion= client.chat.completions.create(model=MODEL_NAME,
            messages=[
                {"role": "system", "content": CONVINCER_PROMPT.replace('%STM%', stm)+additional_info},
                {"role": "user", "content": "I don't believe you. Why is this statement true?"}
                ]+history,
            temperature=0.75,
            max_tokens=3000)
            candidate = completion.choices[0].message
            verification = client.chat.completions.create(model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SCRUTINISER_PROMPT.replace('%STM%', stm).replace('%CAND%', candidate.content)},
                ]+history,
            temperature=0.75,
            max_tokens=3000)
            result = verification.choices[0].message.content.lower().strip('.').strip('"')
            if result == 'yes':
                model_answer_acceptable = True
                continue
            else:
                print(result)
                tries += 1
            if tries == 5:
                print('[!] I couldn\'t find an answer that makes sense given your last statement. I\'ll forget the last thing you said.')
                history = history[:-1]
        history.append({'content': candidate.content, 'role': 'system'})
        print('\n'+candidate.content+'\n')
        user_input = input('>').strip()
        if user_input == '/yes':
            print('[!] Statement Completed.')
            return True
        elif user_input == '/no':
            print('[!] Statement Rejected.')
            return False
        elif user_input == '/help':
            print('[?] Try to answer in short sentences. If you are convinced, type "/yes". If you feel there is no way you can be convinced, type "/no". Otherwise, keep talking.')
        else:
            evaluation = client.chat.completions.create(model=MODEL_NAME,
            messages=[
                {"role": "system", "content": EVALUATOR_PROMPT.replace("%STM%", stm).replace('%RESPONSE%', user_input)},
                ],
            temperature=0.75,
            max_tokens=300)
            if (evaluation.choices[0].message.content.lower()=='yes'):
                return True
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
    ## Now we do depth first search
    if dfs_convincer(arg_stack, graph):
        print('[!] Goal complete.')
    else:
        print('[!] Goal rejected.')

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
                    STM_HISTORY.append(graph.nodes[arg_stack[NODE]]['label'])
                    if (len(STM_HISTORY) > 1):
                        s_hist = STM_HISTORY[-2]
                    else:
                        s_hist = None
                    if stm_convince_loop(graph.nodes[arg_stack[NODE]]['label'], additional_info=convert_prior_results(yes_nos, graph), last_prompt=s_hist):
                        return True
            else:
                yes_nos[sub_argument] = False
        if not tried_skip:
            STM_HISTORY.append(graph.nodes[arg_stack[NODE]]['label'])
            if (len(STM_HISTORY) > 1):
                s_hist = STM_HISTORY[-2]
            else:
                s_hist = None
            if stm_convince_loop(graph.nodes[arg_stack[NODE]]['label'], additional_info=convert_prior_results(yes_nos, graph), last_prompt=s_hist):
                return True
            else:
                return False
        else:
            return False
    else:
        STM_HISTORY.append(graph.nodes[arg_stack[NODE]]['label'])
        if (len(STM_HISTORY) > 1):
            s_hist = STM_HISTORY[-2]
        else:
            s_hist = None
        if stm_convince_loop(graph.nodes[arg_stack[NODE]]['label'],last_prompt=s_hist):
            return True
        else:
            return False

def dumb_convince_loop(list_of_stms):
    for stm in list_of_stms:
        stm_convince_loop(stm)


