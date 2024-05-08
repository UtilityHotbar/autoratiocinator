import nltk
from nltk.corpus import stopwords
from nltk import sent_tokenize, word_tokenize

nltk.download('stopwords')
nltk.download('punkt')
STOP_WORDS = set(stopwords.words('english'))

import uuid
import networkx as nx
from ratiocinatorutils import *
import pyvis
import copy
import numpy as np
import tempfile

CONTEXT_WINDOW_SIZE = 3

BLANKS = ['', ' ', '\n']

SIMILARITY_THRESHOLD = 0.9

CLEANER_PROMPT = 'You are a dedicated, attentive, and intelligent copy editor. Your job is to rewrite passages and remove line breaks in the middle of sentences, loose headers, errors in spelling, artefacts from printing etc. This is the passage you need to rewrite : "%STM%". Respond with the rewritten passage and nothing else.'
REWRITER_PROMPT = 'You are a dedicated, attentive, and intelligent copy editor. Your job is to rewrite passages into clearer, more intelligible sentences that are easier to read and understand. Where possible, use simple language and clear vocabulary. If the sentence is a simple sentence, keep it the same. If the sentence is too long or complex, split it into multiple shorter sentences. Do not say "the passage said...", rewrite it as if you were the writer. This is the passage you need to rewrite : "%STM%". Respond with the rewritten passage and nothing else.'
NOUN_EXPANDER_PROMPT = 'You are a dedicated, attentive, and intelligent copy editor. Your job is to expand pronouns like "they", "them", "it" etc. into the nouns they represent. For example, if you see "John went to the store. He was hungry", return "John went to the store. John was hungry". If people are quoted, add who was quoted. If you are given "The author cites Cicero. He was writing about romans. It is said that the romans are clever." Return "The author cites Cicero. Cicero was writing about romans. Cicero said that the romans are clever." This is the passage you need to rewrite : "%STM%". Respond with the rewritten passage and nothing else.'
SUMMARISER_PROMPT = 'You are a dedicated, attentive, and intelligent copy editor. Your job is to summarise a passage into one or a few short sentences representing its key arguments. This is the passage you need to rewrite : "%STM%". Respond with the rewritten passage and nothing else.'
COMPARATOR_PROMPT = 'You are a dedicated, attentive, and intelligent copy editor. Your job is to compare two sentences and see if they are related. These are the sentences you need to compare. \n Sentence 1: "%STM1%" \n Sentence 2: (located %CONTEXT% \sentence 1) "%STM2%". \nIf the two sentences above are related, answer "related". If the first sentence depends on the second, answer "first-depend-second". If the second sentence depends on the first, answer "second-depend-first". Otherwise, answer "unrelated".'


def get_key(val, d):
    try:
        return list(d.keys())[list(d.values()).index(val)]
    except ValueError:
        return False

def clean_substitutions(substitutions):
    done = False
    while not done:
        done = True
        for substitution in substitutions:
            target = substitutions[substitution]
            if target in substitutions:
                done = False
                substitutions[substitution] = substitutions[target]
    print('cleaned')
    return substitutions

def get_top_search_results(sentence: str, text_embeds: dict, cutoff=10):
    sentence = get_embedding(' '.join([_ for _ in sentence if _.lower() not in STOP_WORDS]).lower())
    top_x = list(sorted(map(lambda text: [cosine_similarity(sentence, text_embeds[text]), text], text_embeds.keys()),key=lambda x: x[0]))[:cutoff]
    return [pair[1] for pair in top_x if pair[0] > 0.3]


def rewriter(text):
    paras = [_ for _ in text.replace('\r', '').split('\n\n') if _ not in BLANKS]
    diced_paras = []
    for undiced_para in paras:
        if num_tokens_from_string(undiced_para) > 150:
            sentences_in_para = sent_tokenize(undiced_para)
            done = False
            i = 0
            ctoks = 0
            cbuf = []
            while not done:
                curr_sent = sentences_in_para[i]
                curr_sent_len = num_tokens_from_string(curr_sent)
                if curr_sent_len > 150:
                    diced_paras.append(' '.join(cbuf))
                    diced_paras.append(curr_sent)
                    cbuf = []
                    ctoks = 0
                else:
                    if (ctoks + curr_sent_len) > 150:
                        diced_paras.append(' '.join(cbuf))
                        cbuf = [curr_sent]
                        ctoks = curr_sent_len
                    else:
                        cbuf.append(curr_sent)
                        ctoks += curr_sent_len
                i += 1
                if (i==(len(sentences_in_para)-1)):
                    done = True

        else:
            diced_paras.append(undiced_para)
    paras = diced_paras
    print('PARAGRAPHS - ', paras)
    toked_paras = []
    for text in paras:
        prompt_list = [CLEANER_PROMPT, SUMMARISER_PROMPT, REWRITER_PROMPT, NOUN_EXPANDER_PROMPT]
        for curr_prompt in prompt_list:
            rewrite = client.chat.completions.create(model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": curr_prompt.replace('%STM%', text)},
                    ],
                temperature=0.5,
                max_tokens=3000)
            text = rewrite.choices[0].message.content
        print(text)
        toked_paras+=sent_tokenize(text)
    return toked_paras

def associator_dumb(text):
    G = nx.MultiDiGraph()
    covered_sentences = {}
    covered_pairs = []
    for curr_sentence in text:
        for next_sentence in text:
            if curr_sentence == next_sentence:
                continue
            curr_pair = list(sorted([curr_sentence, next_sentence]))
            if curr_pair in covered_pairs:
                continue
            else:
                covered_pairs.append(curr_pair)
            print(curr_sentence, '\n', next_sentence)
            if not (curr_sentence in covered_sentences.keys()):
                cid = str(uuid.uuid4())
                G.add_node(cid, label=curr_sentence, comments=[] ,tag='')
                covered_sentences[curr_sentence] = cid
            else:
                cid = covered_sentences[curr_sentence]
            if not (next_sentence in covered_sentences.keys()):
                nid = str(uuid.uuid4())
                G.add_node(nid, label=next_sentence, comments=[] ,tag='')
                covered_sentences[next_sentence] = nid
            else:
                nid = covered_sentences[next_sentence]
            done = False
            while not done:
                done = True
                # relate = client.chat.completions.create(model=MODEL_NAME,
                #     messages=[
                #         {"role": "system", "content": COMPARATOR_PROMPT.replace('%STM1%', curr_sentence).replace('%STM2%', next_sentence)},
                #         ],
                #     temperature=0.5,
                #     max_tokens=1000)
                # answer = relate.choices[0].message.content.lower().strip('"')
                answer = get_mc_answer_simple(COMPARATOR_PROMPT.replace('%STM1%', curr_sentence).replace('%STM2%', next_sentence), ['related', 'first-depend-second', 'second-depend-first'],)
                if answer == 'related':
                    G.add_edge(cid, nid, key=CONNECT, title=CONNECT_LABEL)
                elif answer == 'first-depend-second':
                    G.add_edge(cid, nid, key=SOURCE, title=SOURCE_LABEL)
                elif answer == 'second-depend-first':
                    G.add_edge(nid, cid, key=SOURCE, title=SOURCE_LABEL)
                elif answer == 'unrelated':
                    pass
                else:
                    done = False
    return G

def associator(text):
    G = nx.MultiDiGraph()
    embedding_reference = {}
    uuid_reference = {}
    pairs = []
    substitutions = {}

    for sentence in text:
        if sentence not in embedding_reference:
            embedding_reference[sentence] = get_embedding(sentence)
    for sentence in embedding_reference:
        for other_sentence in embedding_reference:
            if sentence == other_sentence:
                continue
            if cosine_similarity(embedding_reference[sentence], embedding_reference[other_sentence]) > SIMILARITY_THRESHOLD:
                substitutions[other_sentence] = sentence
                print('Substituting ', sentence[:50], 'for', other_sentence[:50])
    
    substitutions = clean_substitutions(substitutions)
    for i in range(len(text)):
        print(f'PROGRESS: [{i+1}/{len(text)}]')
        sentence = text[i]
        prev_text = text[:i]
        prev_embed = {}
        for prev_sent in prev_text:
            prev_embed[prev_sent] = embedding_reference[prev_sent]
        if not (sentence in uuid_reference.keys()):
            if sentence in substitutions:
                sub = substitutions[sentence]
                if not (sub in uuid_reference):
                    uuid_reference[sub] = str(uuid.uuid4())
                    G.add_node(uuid_reference[sub], label=sub ,tag='')
                uuid_reference[sentence] = uuid_reference[sub]
            else:
                uuid_reference[sentence] = str(uuid.uuid4())
            G.add_node(uuid_reference[sentence], label=sentence,tag='')
            print(G, uuid_reference)
        compare_candidates = []
        compare_candidates += text[max(0, i-CONTEXT_WINDOW_SIZE):min(len(text)-1, i+CONTEXT_WINDOW_SIZE)]  # nab immediate context
        # Find related sentences from past sentences (Is this RAG?)
        if prev_embed:
            compare_candidates += get_top_search_results(sentence, prev_embed)
        compare_candidates = list(set(compare_candidates)) #  No duplicate LLM calls!
        print(compare_candidates)
        # Do pairwise LLM-powered comparison for each pair (we need to add new nodes to the graph if theey haven't been added yet)
        for candidate in compare_candidates:
            if not (candidate in uuid_reference.keys()):
                if candidate in substitutions:
                    sub = substitutions[candidate]
                    if not (sub in uuid_reference):
                        uuid_reference[sub] = str(uuid.uuid4())
                        G.add_node(uuid_reference[sub], label=sub,tag='')
                    uuid_reference[candidate] = uuid_reference[sub]
                    candidate = sub
                else:
                    uuid_reference[candidate] = str(uuid.uuid4())
                G.add_node(uuid_reference[candidate], label=candidate,tag='')
                print(G, uuid_reference)
            make_pair = list(sorted([sentence, candidate]))
            if make_pair in pairs or sentence == candidate:
                continue
            else:
                pairs.append(make_pair)
            print('Comparing ', make_pair)
            context = 'around'
            ci = text.index(candidate)
            si = i
            if ci < si:
                context = 'before'
            elif ci > si:
                context = 'after'
            # relate = client.chat.completions.create(model=MODEL_NAME,
            #     messages=[
            #         {"role": "system", "content": COMPARATOR_PROMPT.replace('%STM1%', sentence).replace('%CONTEXT%', context).replace('%STM2%', candidate)},
            #         ],
            #     temperature=0.5,
            #     max_tokens=1000)
            # answer = relate.choices[0].message.content.lower().strip('"')
            answer = get_mc_answer_simple(COMPARATOR_PROMPT.replace('%STM1%', sentence).replace('%CONTEXT%', context).replace('%STM2%', candidate), ['related', 'first-depend-second', 'second-depend-first', 'unrelated'])
            if answer == 'related':
                G.add_edge(uuid_reference[sentence], uuid_reference[candidate], key=CONNECT, title=CONNECT_LABEL)
            elif answer == 'first-depend-second':
                G.add_edge(uuid_reference[sentence], uuid_reference[candidate], key=SOURCE, title=SOURCE_LABEL)
            elif answer == 'second-depend-first':
                G.add_edge(uuid_reference[candidate], uuid_reference[sentence], key=SOURCE, title=SOURCE_LABEL)
            elif answer == 'unrelated':
                pass
    return G


def visualise(G, path='generated.html'):
    show_net = pyvis.network.Network(height="750px", width="100%", bgcolor="#222222", font_color="white", directed=True)
    show_net.barnes_hut()
    show_net.show_buttons(filter_=['physics'])
    show_net.from_nx(G)
    for edge in show_net.edges:
        if edge['title'] == SOURCE_LABEL:
            edge['color'] = '#99ffcc'
        elif edge['title'] == CONNECT_LABEL:
            edge['color'] = '#ff9999'
    show_net.save_graph(path)
    print(f'Rhizome saved to "{path}".')


def save(G):
    print(G, G.nodes)
    nx.write_gexf(G, 'generated.gexf')
    print('Saved to "generated.gexf".')

if __name__ == '__main__':
    choice = input('Choose: [r]ewrite or [g]enerate graph? ').lower()
    if choice == 'r':
        print('Rewriting text')
        cleaned_text = rewriter(open(input('File path: ')).read())
        with open('cleaned_text_in_progress.txt', 'w') as g:
            g.write('\n'.join(cleaned_text))
    elif choice == 'g':
        with open('cleaned_text_in_progress.txt') as f:
            cleaned_text_from_file = f.readlines()
        print('Associating text')
        G = associator(cleaned_text_from_file)
        print('Visualising Rhizome')
        visualise(G)
        print('Saving Rhizome')
        save(G)
