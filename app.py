import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from io import BytesIO

# Set page configuration
st.set_page_config(page_title="Regex to NFA Converter", layout="wide")

# Helper functions for regex -> postfix -> NFA
def infix_to_postfix(regex):
    # Add concatenation operator '.' explicitly
    def add_concat_operator(regex):
        result = ""
        for i in range(len(regex) - 1):
            result += regex[i]
            if regex[i] not in '(|' and regex[i+1] not in '|)*':
                result += '.'
        result += regex[-1] if regex else ""
        return result
    
    # Process the regex with concatenation operators
    new_regex = add_concat_operator(regex)
    
    # Convert to postfix
    precedence = {'|': 1, '.': 2, '*': 3}
    output, stack = [], []
    
    for c in new_regex:
        if c not in precedence and c not in '()':
            output.append(c)
        elif c == '(':
            stack.append(c)
        elif c == ')':
            while stack and stack[-1] != '(':
                output.append(stack.pop())
            if stack and stack[-1] == '(':
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
        self.is_final = False

def build_nfa(postfix):
    stack = []
    
    for c in postfix:
        if c not in {'*', '|', '.'}:
            start, end = State(), State()
            end.is_final = True  # Mark as potential final state
            transitions = [(start.id, c, end.id)]
            stack.append((start, end, transitions))
        elif c == '.':  # Concatenation
            if len(stack) < 2:
                st.error(f"Invalid expression: not enough operands for '.' operation")
                return None, None, []
            s2 = stack.pop()
            s1 = stack.pop()
            s1[1].is_final = False  # No longer a final state
            transitions = s1[2] + [(s1[1].id, 'ε', s2[0].id)] + s2[2]
            stack.append((s1[0], s2[1], transitions))
        elif c == '|':  # Alternation
            if len(stack) < 2:
                st.error(f"Invalid expression: not enough operands for '|' operation")
                return None, None, []
            s2 = stack.pop()
            s1 = stack.pop()
            start, end = State(), State()
            end.is_final = True
            s1[1].is_final = False
            s2[1].is_final = False
            transitions = [
                (start.id, 'ε', s1[0].id),
                (start.id, 'ε', s2[0].id),
                *s1[2],
                *s2[2],
                (s1[1].id, 'ε', end.id),
                (s2[1].id, 'ε', end.id)
            ]
            stack.append((start, end, transitions))
        elif c == '*':  # Kleene star
            if not stack:
                st.error(f"Invalid expression: not enough operands for '*' operation")
                return None, None, []
            s = stack.pop()
            start, end = State(), State()
            end.is_final = True
            s[1].is_final = False
            transitions = [
                (start.id, 'ε', s[0].id),
                (start.id, 'ε', end.id),
                *s[2],
                (s[1].id, 'ε', s[0].id),
                (s[1].id, 'ε', end.id)
            ]
            stack.append((start, end, transitions))
    
    if not stack:
        st.error("Invalid expression: no valid NFA constructed")
        return None, None, []
    
    return stack[0]

def visualize_nfa(start, end, transitions):
    G = nx.DiGraph()
    
    # Add explicit start node
    G.add_node("start", shape="circle", color="green")
    G.add_edge("start", start.id, label="")
    
    # Add all states
    states = set()
    for src, _, dst in transitions:
        states.add(src)
        states.add(dst)
    
    for state in states:
        if state == end.id:
            G.add_node(state, shape="doublecircle", color="red")
        else:
            G.add_node(state, shape="circle", color="skyblue")
    
    # Add transitions
    for src, symbol, dst in transitions:
        if G.has_edge(src, dst):
            # If edge exists, append new symbol to label
            current_label = G.edges[src, dst]['label']
            G.edges[src, dst]['label'] = f"{current_label},{symbol}"
        else:
            G.add_edge(src, dst, label=symbol)
    
    # Layout and draw
    plt.figure(figsize=(12, 8))
    
    # Use spring layout instead of kamada_kawai_layout (which requires scipy)
    pos = nx.spring_layout(G, k=0.30, iterations=50, seed=42)  # Added seed for consistency
    
    # Draw nodes
    node_colors = [G.nodes[n].get('color', 'skyblue') for n in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_size=2000, node_color=node_colors)
    
    # Draw labels
    nx.draw_networkx_labels(G, pos, font_size=12)
    
    # Draw edges with slight curve to avoid overlap
    nx.draw_networkx_edges(G, pos, arrowsize=20, width=1.5, connectionstyle='arc3,rad=0.1')
    
    # Draw edge labels
    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=12)
    
    plt.axis('off')
    plt.tight_layout()
    
    # Save to buffer
    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=300)
    buf.seek(0)
    plt.close()
    
    return buf

def validate_regex(regex):
    # Simple validation for common regex errors
    errors = []
    
    # Check for balanced parentheses
    open_paren = regex.count('(')
    close_paren = regex.count(')')
    if open_paren != close_paren:
        errors.append(f"Unbalanced parentheses: {open_paren} opening vs {close_paren} closing")
    
    # Check for invalid operators
    if regex.startswith('|') or regex.startswith('*'):
        errors.append("Expression cannot start with '|' or '*'")
    
    if regex.endswith('|'):
        errors.append("Expression cannot end with '|'")
    
    # Check for consecutive operators
    for i in range(len(regex) - 1):
        if regex[i] == '|' and regex[i+1] == '|':
            errors.append("Cannot have consecutive '|' operators")
    
    return errors

# Streamlit UI
st.title("🔄 Regex to NFA Converter")
st.write("""
This application converts a regular expression to its equivalent Non-deterministic Finite Automaton (NFA).
Enter a regular expression below using these operators:
- `a`, `b`, `c`, etc. for basic symbols
- `|` for alternation (OR)
- `*` for Kleene star (zero or more repetitions)
- `()` for grouping
""")

with st.expander("📚 Regular Expression Examples", expanded=False):
    st.markdown("""
    | Example | Description |
    | ------- | ----------- |
    | `a(b\|c)*d` | 'a' followed by any number of 'b' or 'c', ending with 'd' |
    | `(a\|b)*` | Any number of 'a's or 'b's |
    | `ab*c` | 'a' followed by any number of 'b's, ending with 'c' |
    | `(ab)\|(cd)` | Either 'ab' or 'cd' |
    """)

# Input for regex
col1, col2 = st.columns([3, 1])
with col1:
    regex_input = st.text_input("Enter Regular Expression:", value="a(b|c)*d")

with col2:
    example_regex = st.selectbox(
        "Or select an example:",
        ["a(b|c)*d", "(a|b)*", "ab*c", "(ab)|(cd)"]
    )
    if st.button("Use Example"):
        regex_input = example_regex

if regex_input:
    # Validate regex
    validation_errors = validate_regex(regex_input)
    if validation_errors:
        st.error("Regex validation errors:")
        for error in validation_errors:
            st.error(f"- {error}")
    else:
        # Process regex
        try:
            st.subheader("Conversion Process")
            
            # 1. Show original regex
            st.write(f"**Original Regex:** `{regex_input}`")
            
            # 2. Convert to postfix
            postfix = infix_to_postfix(regex_input)
            st.write(f"**Postfix Notation:** `{postfix}`")
            
            # 3. Build and visualize NFA
            State.count = 0  # Reset state counter
            start, end, transitions = build_nfa(postfix)
            
            if start and end:
                # Display the transitions in a table
                st.subheader("NFA Transitions")
                transition_data = []
                for src, symbol, dst in transitions:
                    symbol_display = "ε" if symbol == "ε" else symbol
                    transition_data.append({"From State": src, "Symbol": symbol_display, "To State": dst})
                
                st.dataframe(transition_data, use_container_width=True)
                
                # Display the NFA diagram
                st.subheader("NFA Diagram")
                buf = visualize_nfa(start, end, transitions)
                st.image(buf, use_container_width=True)
                
                # Explain NFA
                with st.expander("NFA Explanation", expanded=True):
                    st.markdown(f"""
                    This NFA represents the regular expression `{regex_input}`.
                    
                    - **Start state**: {start.id}
                    - **Final/Accepting state**: {end.id}
                    - **Number of states**: {State.count}
                    - **Number of transitions**: {len(transitions)}
                    
                    The NFA processes input strings by following transitions based on the current input symbol.
                    Epsilon (ε) transitions can be taken without consuming any input.
                    A string is accepted if there exists a path from the start state to the accepting state
                    that consumes the entire input string.
                    """)
        except Exception as e:
            st.error(f"Error processing regex: {str(e)}")
            # Add debug information
            st.error(f"Error type: {type(e).__name__}")
            import traceback
            st.error(f"Traceback: {traceback.format_exc()}")

# Information about the project
with st.sidebar:
    st.header("About this Project")
    st.markdown("""
    **Regex to NFA Converter** is a tool that visualizes the conversion from Regular Expressions to
    Non-deterministic Finite Automata using Thompson's Construction Algorithm.
    
    **Key Features:**
    - Converts regular expressions to postfix notation
    - Builds NFA using Thompson's Construction
    - Visualizes the resulting NFA with a clear diagram
    - Displays state transitions in a readable format
    
    **Supported Operations:**
    - Basic symbols (a, b, c, etc.)
    - Alternation (|)
    - Kleene star (*)
    - Concatenation (implicitly added)
    - Grouping with parentheses
    """)
