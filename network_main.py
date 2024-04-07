# NetworkX version of rhizomes
import networkx as nx
import uuid
import pyvis.network
from ratiocinator import tree_convince_loop, dumb_convince_loop
from constants import *

class IdError(Exception):
    pass

class CmdInterrupt(Exception):
    pass

def list_dependencies(graph, node):
    deps = []
    for source in graph.successors(node):
        if graph.has_edge(node, source, key=SOURCE) and source != node:  # Be careful to avoid circular dependencies!
            deps.append(source)
            deps += list_dependencies(graph, source)
    return deps


def list_parents(graph, node):
    parents = []
    for source in graph.predecessors(node):
        if graph.has_edge(node, source, key=IMPLY) and source != node:  # Be careful to avoid circular dependencies!
            parents.append(source)
            parents += list_parents(graph, source)
    return parents


def get_id(id_cand, curr_run, curr_body):
    id_type = id_cand[0]
    rest = id_cand[1:]
    if id_type == ':':  # Run index
        if rest.lstrip('-').isnumeric():
            return curr_run[int(id_cand[1:])]
        else:
            raise IdError('Invalid ID')
    elif id_type == '@':
        return rest
    elif id_type == '"':  # Doing a dumb search for the statement. "apples are great" becomes "apples-are-great"
        candidate = None
        for node in curr_body.nodes():
            c = curr_body.nodes[node]['label']
            if c == rest:
                return c
            elif c.replace(' ', '-').startswith(rest):
                candidate = node
        if candidate:
            return candidate
        else:
            raise IdError('Invalid ID - Node not found with dumb search')
    elif id_type == '$':
        # absolute statement order (access with print *)
        return list(curr_body.nodes())[int(rest)]
    else:
        rest = id_type + rest
        # Assume ID is in format run:index with index not optional
        r = rest.split(':')
        run_cand = r[0]
        if len(r) > 1:
            run_index = int(r[1])
        else:
            raise IdError('Invalid ID - Specify index of run!')
        candlist = []
        _ = 0
        for node in curr_body.nodes:
            nd = curr_body.nodes[node]
            if nd['tag'] == run_cand:
                if _ == run_index:
                    return node
                else:
                    candlist.append(node)
                    _ += 1
        if candlist:
            return candlist[run_index]  # just in case someone does something like run:-1
        else:
            raise IdError(f'Invalid ID - Run with name {run_cand} may not exist, or there isn\'t a {run_index}th statement there.')


def interpret_command(instruction, curr_run_name, curr_run_ids, G):
            instruction = instruction.split()
            cmd = instruction[0]
            body = instruction[1:]
            if cmd == '/statement' or cmd == '/s' or cmd == '/then' or cmd == '/t':
                # Create a new "standalone" statement
                stm_id = str(uuid.uuid4())
                G.add_node(stm_id, label=' '.join(body), comments=[] ,tag=curr_run_name)
                if cmd == '/then' or cmd == '/t':
                    G.add_edge(stm_id, curr_run_ids[-1], key=SOURCE, title=SOURCE_LABEL)
                curr_run_ids.append(stm_id)

            elif cmd == '/print' or cmd == '/p':
                if len(body) > 0:
                    target = body[0]
                    try:
                        target_id = get_id(target, curr_run_ids, G)
                        print('ID', target_id)
                        print(G.nodes[target_id]['label'])
                    except IdError:
                        _ = 0
                        for node in G.nodes:
                            nd = G.nodes[node]
                            if nd['tag'] == target or target == '*':
                                print(f'{_}.', nd['label'])
                                _ += 1
                else:
                    _ = 0
                    # Print current run
                    if curr_run_name:
                        print(curr_run_name)
                    else:
                        print('New Run')
                    for id in curr_run_ids:
                        print(f'{_}.', G.nodes(data=True)[id]['label'])
                        _ += 1
            # elif cmd == '/imply' or cmd == '/i':
            #     if len(body) >= 2:
            #         start = get_id(body[0], curr_run_ids, G)
            #         end = get_id(body[1], curr_run_ids, G)
            #         if start and end:
            #             G.add_edge(start, end, key=IMPLY, title=IMPLY_LABEL)
                    
            #     else:
            #         print('Specify start and end.')
            # elif cmd == '/unimply' or cmd == '/ui':
            #     if len(body) >= 2:
            #         start = get_id(body[0], curr_run_ids, G)
            #         end = get_id(body[1], curr_run_ids, G)
            #         if start and end:
            #             G.remove_edge(start, end, key=IMPLY)
            #     else:
            #         print('Specify start and end.')
            elif cmd == '/origin' or cmd == '/o':
                if len(body) >= 2:
                    start = get_id(body[0], curr_run_ids, G)
                    end = get_id(body[1], curr_run_ids, G)
                    if start and end:
                        G.add_edge(start, end, key=SOURCE, title=SOURCE_LABEL)
                    
                else:
                    print('Specify start and end.')
            elif cmd == '/unorigin' or cmd == '/uo':
                if len(body) >= 2:
                    start = get_id(body[0], curr_run_ids, G)
                    end = get_id(body[1], curr_run_ids, G)
                    if start and end:
                        G.remove_edge(start, end, key=SOURCE)
                else:
                    print('Specify start and end.')
            elif cmd == '/run' or cmd == '/r':
                # Start a new run
                curr_run_ids = []
                curr_run_name = ''
                if len(body) > 0:
                    run_name = body[0]
                    if ':' in run_name:
                        print('Don\'t use colons (:) in the run name!')
                        raise CmdInterrupt
                    curr_run_name = run_name
            elif cmd == '/wrap' or cmd == '/w':
                # Wrap up a run as a formal group and commit to body
                if len(body) > 0:
                    run_name = body[0]
                    if ':' in run_name:
                        print('Don\'t use colons (:) in the run name!')
                        raise CmdInterrupt
                else:
                    print('Input a run name!')
                for id in curr_run_ids:
                    G.nodes[id]['tag'] = run_name
                curr_run_name = run_name
            elif cmd == '/explain' or cmd == '/x':
                if len(body) > 0:
                    statement = body[0]
                    i = get_id(statement, curr_run_ids, G)
                    if i:
                        statement_to_prove = i
                        print(G.nodes[statement_to_prove]['label'])
                        print('===')
                        deps = list_dependencies(G, statement_to_prove)
                        parents = list_parents(G, statement_to_prove)
                        if deps:
                            print('DEPENDENCIES >')
                            for dep in deps:
                                print(G.nodes[dep]['label'])
                        if parents:
                            print('\nSOURCES >')
                            for parent in parents:
                                print(G.nodes[parent]['label'])
                        if input("Try to convince you? [y/n]") =='y':

                            # dumb_convince_loop([G.nodes[dep]['label'] for dep in deps]+[G.nodes[statement_to_prove]['label']])
                            tree_convince_loop(G, statement_to_prove)
            elif cmd == '/commit' or cmd == '/c':
                if len(body) > 0:
                    path = body[0]
                else:
                    path = CURRENT
                print(G, G.nodes)
                nx.write_gexf(G, path)
            elif cmd == '/load' or cmd == '/l':
                if len(body) > 0:
                    path = body[0]
                else:
                    path = CURRENT
                if len(body) > 1:
                    if body[1] == '--overwrite' or body[1] == '-o':
                        G = nx.MultiDiGraph(nx.read_gexf(path))
                else:
                    G = nx.compose(nx.MultiDiGraph(nx.read_gexf(path)),G)
                print(G, G.nodes)
            elif cmd == '/loadmergecommit' or cmd == '/lmc':
                if len(body) > 0:
                    path = body[0]
                else:
                    path = CURRENT
                G = nx.compose(nx.MultiDiGraph(nx.read_gexf(path)),G)
                print(G, G.nodes)
                nx.write_gexf(G, path)
            elif cmd == '/delete' or cmd == '/d':
                if len(body) <= 0:
                    print('Specify statement/run to delete!')
                    raise CmdInterrupt
                target = get_id(body[0], curr_run_ids, G)
                if input('Node found: delete node? y/n').lower() == 'y':
                    G.remove_node(target)
            elif cmd == '/quit' or cmd == '/q':
                print('Saving and quitting.')
                if len(body) > 0:
                    path = body[0]
                else:
                    path = CURRENT
                nx.write_gexf(G, path)
                quit()
            elif cmd == '/forcequit' or cmd == '/fq':
                print('Force quitting...')
                print('*slam*')
                quit()
            elif cmd == '/visualise' or cmd == '/v':
                show_net = pyvis.network.Network(height="750px", width="100%", bgcolor="#222222", font_color="white", directed=True)
                show_net.barnes_hut()
                show_net.show_buttons(filter_=['physics'])
                show_net.from_nx(G)
                for edge in show_net.edges:
                    if edge['title'] == SOURCE_LABEL:
                        edge['color'] = '#99ffcc'
                    elif edge['title'] == IMPLY_LABEL:
                        edge['color'] = '#ff9999'
                show_net.save_graph('test.html')
                print('Rhizome saved to "test.html".')
            elif cmd == '/rewrite' or cmd == '/rw':
                if not len(body) >= 2:
                    raise CmdInterrupt('Provide a node ID and a new statement please!')
                rewrite_target_id = get_id(body[0], curr_run_ids, G)
                rewrite_content = ' '.join(body[1:])
                G.nodes[rewrite_target_id]['label'] = rewrite_content
            elif cmd == '/help':
                print('==HELP==')
                print('When IDs are required, use "print *" to view current IDs and then $N where N is the number displayed during "print *" to target that statement. (I leave using the alternate ID schemas implemented as an exercise for the reader)')
                print('/s STM - New statement with text "STM".')
                print('/t STM - New statement "STM", which follows from the last statement.')
                print('/o ID1 ID2 - Creates a link from statement with ID "ID1" to "ID2".')
                print('/d ID - Deletes statement with ID "ID".')
                print('/r RUN_ID - New run [list] of statements with ID "RUN_ID".')
                print('/p * || ID - Prints all statements [if you put in *], otherwise prints the statement with ID "ID".')
                print('/x ID - Generates dependencies of statement with ID "ID" and explains it with Autoratiocinator.')
                print('/l FL.GEXF - Loads rhizome from file with name "FL.GEXF".')
                print('/lmc FL.GEXF - Loads rhizome from file with name "FL.GEXF", merges it with current knowledge graph, and saves result to output [default "current_graph.gexf"].')
                print('/c FL.GEXF - Commits current knowledge graph to file with name "FL.GEXF".')
                print('/q - Quit and save.')
                print('/fq - Force quit and do not save.')
                print('/v - Generate graph visualisation.')

            else:
                print('Command not recognised. Please try again?')
            return curr_run_name, curr_run_ids, G

def mainloop():
    try:
        G = nx.MultiDiGraph(nx.read_gexf(CURRENT))
        print('Loaded saved rhizome!')
    except:
        G = nx.MultiDiGraph()
        print('No current rhizome found, made a blank rhizome for you.')
    curr_run_name = ''
    curr_run_ids = []
    done = False
    while not done:
        try:
            instruction = input('THM.DS> ')
            curr_run_name, curr_run_ids, G = interpret_command(instruction, curr_run_name, curr_run_ids, G)
        except IdError as anticipated:
            # ID resolution errors usually don't entail data corruption etc.
            print('ID error thrown with the message:', anticipated)
        except CmdInterrupt as interrupt:
            # We assume that the interpretation function has already thrown an error message so we just smoothly pick up the REPL
            print('Returning to REPL flow.')
        except Exception as unanticipated:
            # For everything else we save an error dump before trying to move on.
            print('Unanticipated system error thrown with the message:', repr(unanticipated))
            print('Dumping rhizome to "recovery.gexf" just in case.')
            nx.write_gexf(G, 'recovery.gexf')
            if input('Raise the full error? This will end the REPL. [y/n] ').lower() == 'y':
                raise unanticipated
            else:
                print('We now return you to your regularly scheduled REPL.')
        except KeyboardInterrupt:
            print('Saving and exiting (/fq for force quit without saving).')
            nx.write_gexf(G, CURRENT)
            print('Bye!')
            exit()
        

if __name__ == '__main__':
    print('Welcome to THEOREM.DS. Type "/help" for help.')
    while True:
        mainloop()

