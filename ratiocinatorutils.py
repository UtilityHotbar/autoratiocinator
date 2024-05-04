import tiktoken
import os
from openai import OpenAI
import random
import numpy as np

IMPLY = 1
SOURCE = 0
CONNECT = 9999
SOURCE_LABEL = 'SOURCE'
CONNECT_LABEL = 'CONNECT'
CURRENT = 'current_graph.gexf'
AXIOM = 'AXIOM'
NODE = 'NODE'
CHILDREN = 'CHILDREN'
LABEL = 'LABEL'
DIST = 'DIST'
MODEL_NAME = 'gpt-4-turbo'
EMBEDDING_MODEL_NAME = 'text-embedding-3-small'
DEPENDENCY_SEARCH_RECURSION_LIMIT = 1000

RANDOM_CHARACTERS = ['ghost', 'hamlet', 'gertrude', 'claudius', 'ophelia', 'laertes', 'polonius', 'reynaldo', 'horatio', 'voltemand', 'cornelius', 'rosencrantz', 'guildenstern', 'osric', 'gentlemen', 'lord', 'francisco', 'barnardo', 'marcellus', 'fortinbras', 'captain', 'ambassadors', 'players', 'messengers', 'sailors', 'gravedigger', 'companion', 'doctor']
MASKED_ANSWER_PROMPT = 'You are a bright assistant answering a multiple choice question. The question is surrounded by <question> tags <question>\n%QUESTION%\n</question>\n The valid answers are: \n%TRUE_ANSWERS%\n\n %ANSWER_SCRIPT%\n Respond with your answer only.'

client = OpenAI(api_key=(os.getenv('OPENAI_API_KEY')))

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def get_embedding(text, model=EMBEDDING_MODEL_NAME):
   text = text.replace("\n", " ")
   return client.embeddings.create(input = [text], model=model).data[0].embedding

def num_tokens_from_string(string: str, encoding_name: str ="cl100k_base") -> int:
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def get_mc_answer_complex(question: str, answers: list, iterations=None, tries_per_iteration=5, client=client):
    answer_prefs = {}
    for answer in answers:
        answer_prefs[answer] = 0
    if not iterations:
        iterations = len(answers)+1
    for iteration in range(iterations):
        answer_map = {}
        answer_names = []
        for answer in answers:
            current_answer_name = ''
            while True:
                for i in range(3):
                    current_answer_name += '-'+random.choice(RANDOM_CHARACTERS)
                current_answer_name = current_answer_name.strip('-')
                if not current_answer_name in answer_names:
                    break
            answer_map[current_answer_name] = answer
            answer_names.append(current_answer_name)
        answer_script = ''
        for masked_answer_name in answer_names:
            answer_script += f'If the answer is "{answer_map[masked_answer_name]}", respond with "{masked_answer_name}". '
        final_prompt = MASKED_ANSWER_PROMPT.replace('%QUESTION%', question).replace('%TRUE_ANSWERS%', ', '.join(answers)).replace('%ANSWER_SCRIPT%', answer_script)
        print(final_prompt)
        attempts_remaining = tries_per_iteration
        candidate = None
        while True:
            completion= client.chat.completions.create(model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": final_prompt},
                    ],
                temperature=1.0,
                max_tokens=num_tokens_from_string(final_prompt)+30)
            candidate = completion.choices[0].message.content.lower()
            if candidate in answer_names:
                break
            else:
                attempts_remaining -= 1
            if attempts_remaining == 0:
                raise RuntimeError(f'Randomised prompting failed to elicit valid masked multiple choice response with prompt:\n\n${final_prompt}\n\nThe last returned response was: ${candidate}')
        answer_prefs[answer_map[candidate]] += 1
    return max(answer_prefs, key=answer_prefs.get)  # get the favoured answer by the LLM

def get_mc_answer_simple(question: str, answers: list, iterations=None, tries_per_iteration=5, client=client):
    answer_prefs = {}
    for answer in answers:
        answer_prefs[answer] = 0
    if not iterations:
        iterations = len(answers)+1
    final_prompt = MASKED_ANSWER_PROMPT.replace('%QUESTION%', question).replace('%TRUE_ANSWERS%', ', '.join(answers)).replace('%ANSWER_SCRIPT%', '')
    for iteration in range(iterations):
        attempts_remaining = tries_per_iteration
        candidate = None
        while True:
            completion= client.chat.completions.create(model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": final_prompt},
                    ],
                temperature=1.0,
                max_tokens=num_tokens_from_string(final_prompt)+30)
            candidate = completion.choices[0].message.content.lower()
            if candidate in answers:
                break
            else:
                attempts_remaining -= 1
            if attempts_remaining == 0:
                raise RuntimeError(f'Randomised prompting failed to elicit valid multiple choice response with prompt:\n\n${final_prompt}\n\nThe last returned response was: ${candidate}')
        answer_prefs[candidate] += 1
    return max(answer_prefs, key=answer_prefs.get)  # get the favoured answer by the LLM

def get_completion(messages, temperature=0.75, max_tokens=3000, model=MODEL_NAME):
    answer = client.chat.completions.create(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
    return answer.choices[0].message.content

def get_refined_answer(init_prompt: str, additional_details: list, max_tokens=3000, ):
    CHANGE_PROMPT = 'How would you change your answer if you had this additional information: %ADD%. Return your new answer as if you were answering my original question.'
    history = [{'role':'system', 'content': 'You are a clever and attentive assistant that listens to user directions.'},{'role': 'user', 'content': init_prompt}]
    init_answer = get_completion(messages=history)
    history.append({'role': 'assistant', 'content': init_answer})
    for detail in additional_details:
        history.append({'role': 'user', 'content': CHANGE_PROMPT.replace('%ADD%', detail)})
        new_answer = get_completion(history, max_tokens=max_tokens)
        history.append({'role': 'assistant', 'content': new_answer})
    return new_answer

if __name__ == '__main__':
    print(get_refined_answer('Describe a small red house.', ['The house has a chimney', 'the house is also blue', 'the house is old']))
