import streamlit as st
from graphviz import Digraph

# Helper functions from your original code (regex -> postfix -> NFA)
def infix_to_postfix(regex):
    precedence = {'|': 1, '.': 2, '*': 3}
    output, stack = [], []
    new_regex = ''
    for i in range(len(regex)):
        c = regex[i]
        new_regex += c
        if c not in '(|' and i + 1 < len(regex):
            next_c = regex[i + 1]
            if next_c not in '|)*':
                new_regex += '.'
    for c in new_regex:
        if c not in precedence and c not in '()':
            output.append(c)
        elif c == '(':
            stack.append(c)
        elif c == ')':
            while stack and stack[-1] != '(':
                output.append(stack.pop())
            stack.pop()
        else:
            while stack and stack[-1] != '(' and precedence.get(stack[-1], 0) >= precedence.get(c, 0):
                output.append(stack.pop())
            stack.append(c)
    while stack:
        output.append(stack.pop())
    return ''.join(output)

class State:
    count = 0
    def __init__(self):
        self.id = f"q{State.count}"
        State.count += 1

def build_nfa(postfix):
    stack = []
    for c in postfix:
        if c not in {'*', '|', '.'}:
            start, end = State(), State()
            transitions = [(start.id, c, end.id)]
            stack.append((start, end, transitions))
        elif c == '.':
            s2 = stack.pop()
            s1 = stack.pop()
            transitions = s1[2] + [(s1[1].id, 'ε', s2[0].id)] + s2[2]
            stack.append((s1[0], s2[1], transitions))
        elif c == '|':
            s2 = stack.pop()
            s1 = stack.pop()
            start, end = State(), State()
            transitions = [
                (start.id, 'ε', s1[0].id),
                (start.id, 'ε', s2[0].id),
                *s1[2],
                *s2[2],
                (s1[1].id, 'ε', end.id),
                (s2[1].id, 'ε', end.id)
            ]
            stack.append((start, end, transitions))
        elif c == '*':
            s = stack.pop()
            start, end = State(), State()
            transitions = [
                (start.id, 'ε', s[0].id),
                (start.id, 'ε', end.id),
                *s[2],
                (s[1].id, 'ε', s[0].id),
                (s[1].id, 'ε', end.id)
            ]
            stack.append((start, end, transitions))
    return stack[0]

def visualize_nfa(start, end, transitions):
    dot = Digraph()
    dot.attr(rankdir='LR')
    dot.node('start', shape='point')
    dot.edge('start', start.id)
    for a, sym, b in transitions:
        dot.edge(a, b, label=sym)
    dot.node(end.id, shape='doublecircle')
    return dot

# Streamlit Interface
st.title("Regex to NFA Converter")
st.write("Enter a regular expression to visualize its NFA.")

# Regex Input
regex_input = st.text_input("Enter Regular Expression")

if regex_input:
    postfix = infix_to_postfix(regex_input)
    State.count = 0
    start, end, transitions = build_nfa(postfix)
    nfa_graph = visualize_nfa(start, end, transitions)
    
    # Display NFA graph
    nfa_graph_path = "nfa_output.png"
    nfa_graph.render(nfa_graph_path, format='png', cleanup=False)
    
    st.image(nfa_graph_path)

