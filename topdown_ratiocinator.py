import os
import networkx as nx
from ratiocinatorutils import *
import time
import random

REFERENCE_ORIG_TEXT = True
REFERENCE_PATH = 'cleaned_text_in_progress.txt'

DEPTH_LIMIT = 10

AUTHOR_EXPLAIN_PROMPT = 'You are a clever teacher trying to explain to a student why an author made a particular statement. The statement is "%STM%".\n%PARAGRAPH%\n%STUDENT% \nIn your response give a succinct explanation of why the author made this point. Stick strictly to the author\'s original words when saying your answer.'
SCRUTINISER_PROMPT = 'You are an attentive, clever, and careful assistant. Your job is to see if the message below is off topic from a discussion about the statement "%STM%". This is the statement to analyse: "%CAND%". We need to tell if the statement is part of a discussion about "%STM%".'

RELEVANCY_PROMPT = 'Here are two phrases. Is phrase 1 a search query for phrase 2? \nPhrase 1: "%STM1%". \nPhrase 2: "%STM2%".'
INSPECT_STUDENT_PROMPT = 'You are a clever assistant inspecting a statement made by a student. Currently, the subject of the conversation is "%STM%", and the student said "%RESPONSE%". Do you think the student wants to shift the topic to a different focus? Answer in one word, "yes" or "no".'

def get_arg_stack(graph, node,depth_limit=3, dist=0,  all_exp=None, head=True):
    if not all_exp:
        all_exp = []
    steps = {NODE: node, CHILDREN: {}, DIST: dist, LABEL: graph.nodes[node]['label']}
    for succ in graph.successors(node):
        if graph.has_edge(node, succ, key=SOURCE) and succ != node and not succ in all_exp:
            # Filtering out connection edges
            if not graph.get_edge_data(node, succ, key=SOURCE)['title'] == SOURCE_LABEL:
                continue
            all_exp.append(succ)
            desc = list(graph.successors(succ))
            if len(desc) > 0 and dist < depth_limit:
                results = get_arg_stack(graph, succ, depth_limit, dist+1, all_exp, head=False)
                all_exp = results[0]
                steps[CHILDREN][succ] = results[1]
            else:
                steps[CHILDREN][succ] = {NODE: succ, CHILDREN: AXIOM, DIST: dist, LABEL: graph.nodes[succ]['label']}
    if head:
        return steps
    else:
        return [all_exp, steps]


def tree_convince_loop(graph, node):
    print('Remember, you can always do "/help" for help.')
    # statements_graph = get_statements_graph(graph, node)
    # print(statements_graph)
    arg_stack = get_arg_stack(graph, node)
    print(arg_stack)
    if REFERENCE_ORIG_TEXT:
        reference_text = open(REFERENCE_PATH).readlines()
    else:
        reference_text = None
    ## Now we do depth first search
    if topdown_dfs_convincer(arg_stack, graph, reference_text=reference_text):
        print('[!] Goal complete.')
    else:
        print('[!] Goal rejected.')


def get_all_stms(arg_stack, graph):
    all_stms = {arg_stack[NODE]:graph.nodes[arg_stack[NODE]]['label']}
    if arg_stack[CHILDREN] != AXIOM:
        for sub_arg in arg_stack[CHILDREN]:
            all_stms = all_stms | get_all_stms(arg_stack[CHILDREN][sub_arg], graph)
    return all_stms

def topdown_dfs_convincer(arg_stack, graph, goal='', dict_of_stms=None, stm_history=None, prior_user_data=None, reference_text=None, repl=True):
    if not goal:
        goal = graph.nodes[arg_stack[NODE]]['label']
    if not dict_of_stms:
        dict_of_stms = get_all_stms(arg_stack, graph)
    if not stm_history:
        stm_history = []
    supports = ''
    immediate_support_stms = []
    if arg_stack[CHILDREN]:
        for subarg in arg_stack[CHILDREN]:
            immediate_support_stms.append('The author also said that "'+dict_of_stms[subarg].strip("\n")+'"')
    if immediate_support_stms:
        supports = ' '.join(immediate_support_stms).strip('\n')

    paragraph = ''
    if REFERENCE_ORIG_TEXT and reference_text:
        si = reference_text.index(goal)
        paragraph = 'This is the immediate context in which the statement was found: "'+''.join(reference_text[max(si-3,0):si+3]).strip('\n')+'"'
    student_stm = ''
    if prior_user_data:
        for prev_usr_stm in prior_user_data:
            student_stm += f'The student believes that "{prev_usr_stm}" is {str(prior_user_data[prev_usr_stm])}.'
    starting_prompt = AUTHOR_EXPLAIN_PROMPT.replace('%STM%', goal.strip('\n')).replace('%PARAGRAPH%', paragraph).replace('%STUDENT%', student_stm)
    starting_msg = get_refined_answer(starting_prompt, immediate_support_stms)
    stm_history.append({'role': 'system', 'content': starting_msg})
    print('\nDEBUG -- GOAL:', goal, '\nPROMPT:', starting_prompt, '\nDICT:', dict_of_stms, '\n\nSUPPORT:', supports, '\nPRIOR USER DATA:', prior_user_data,'\n')
    print('\n===\n')
    print(starting_msg)
    if not repl:
        return starting_msg
    while True:
        valid_user_answ = False
        while not valid_user_answ:
            raw_response = input('RESPONSE > ')
            if raw_response.split()[0] == '/help':
                print('/accept to confirm current topic of discussion. /reject to say no to current topic and move on. /query SEARCH_TERMS to explore more of this topic.')
            elif raw_response.split()[0] == '/accept':
                return True
            elif raw_response.split()[0] == '/reject':
                return False
            elif raw_response.split()[0] == '/query':
                rest_of_query = ' '.join(raw_response.split()[1:])
                for stm_id in dict_of_stms:
                    if dict_of_stms[stm_id] != goal:
                        if get_mc_answer_simple(RELEVANCY_PROMPT.replace('%STM1%', rest_of_query).replace('%STM2%', dict_of_stms[stm_id]), ['yes', 'no'], iterations=1):
                            print(f'I think you want to discuss this idea further: "{dict_of_stms[stm_id]}"')
                            if topdown_dfs_convincer(get_arg_stack(graph, stm_id), graph, prior_user_data=prior_user_data):
                                prior_user_data[dict_of_stms[stm_id]] = True
                            else:
                                prior_user_data = False
                            break
                else:
                    print('[!] I don\'t think your query makes sense right now. It seems like this is not in the topic of discussion or we are already discussing it.')
                break
            if get_mc_answer_simple(INSPECT_STUDENT_PROMPT.replace('%STM%', goal).replace('%RESPONSE%', raw_response), ['yes', 'no']) == 'yes':
                return True
            user_response = {'role': 'user', 'content': raw_response}

            possible_next_line = get_completion(messages=stm_history+user_response)
            if get_mc_answer_complex(SCRUTINISER_PROMPT.replace('%STM%', goal).replace('%CAND%', possible_next_line), ['yes', 'no']) == 'yes':
                valid_user_answ = True
                print(possible_next_line)
                stm_history.append(user_response)
                stm_history.append({'role': 'system', 'content': possible_next_line})
            else:
                print('Please try again. I didn\'t understand your point.')

    




