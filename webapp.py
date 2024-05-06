import streamlit as st
import streamlit.components.v1 as components

from ratiocinatorutils import *
from knowledge_graph import *
from topdown_ratiocinator import *
from network_main import *

st.write('''
# Socratides          
''')

text_file_to_analyse = st.file_uploader("Choose a text file to analyse", type="txt")
if text_file_to_analyse is not None:
    string_data = text_file_to_analyse.getvalue().decode("utf-8")
    cleaned_text = rewriter(string_data)
    with st.expander("Cleaned text"):
        st.write(cleaned_text)
    G = associator(cleaned_text)
    visualise(G)
    st.write('## Implication/Correlation Graph')
    components.html(open('generated.html', 'r').read(),height=600)
    reflist = [G.nodes[_]['label'] for _ in G.nodes]
    nodelist = [_ for _ in G.nodes]
    sentence = st.selectbox("Select a sentence to analyse",options=reflist)
    if sentence is not None:
        st.write('## Analysis')
        st.write(f'Sentence to explain: {sentence}')
        node = nodelist[reflist.index(sentence)]
        with st.expander("Sentence dependencies"):
            st.write('* '+'\n* '.join(list_dependencies(G, node)))
        arg_stack = get_arg_stack(G, node)
        st.write(topdown_dfs_convincer(arg_stack, G, sentence, reference_text=cleaned_text, repl=False))
