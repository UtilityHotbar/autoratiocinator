import streamlit as st
import streamlit.components.v1 as components

from ratiocinatorutils import *
from knowledge_graph import *
from topdown_ratiocinator import *
from network_main import *
import uuid
from io import StringIO
import tempfile

@st.cache_data
def associator_wrap(cleaned_text):
    return associator(cleaned_text)

@st.cache_data
def rewriter_wrap(raw_text):
    return rewriter(raw_text)

st.write('''
# Socratides
For source see [https://github.com/UtilityHotbar/autoratiocinator](https://github.com/UtilityHotbar/autoratiocinator).  
''')

text_file_to_analyse = st.file_uploader("Choose a text file to analyse", type="txt")
if text_file_to_analyse is not None:
    string_data = text_file_to_analyse.getvalue().decode("utf-8")
    print(string_data)
    cleaned_text = rewriter_wrap(string_data)
    with st.expander("Cleaned text"):
        st.write(cleaned_text)
    G = associator_wrap(cleaned_text)
    with tempfile.TemporaryDirectory() as temp:
        tmp_path = temp+'/generated.html'
        visualise(G, path=tmp_path)
        st.write('## Implication/Correlation Graph')
        components.html(open(tmp_path, 'r').read(),height=600)
    reflist = [G.nodes[_]['label'] for _ in G.nodes]
    nodelist = [_ for _ in G.nodes]
    sentence = st.selectbox("Select a sentence to analyse",options=reflist)
    if sentence is not None:
        st.write('## Analysis')
        st.write(f'Sentence to explain: {sentence}')
        node = nodelist[reflist.index(sentence)]
        alldeps = list_dependencies(G, node)
        if alldeps:
            with st.expander("Sentence dependencies"):
                st.write('* '+'\n* '.join([G.nodes[_]['label'] for _ in alldeps]))
        arg_stack = get_arg_stack(G, node)
        st.write(topdown_dfs_convincer(arg_stack, G, sentence, reference_text=cleaned_text, repl=False))
