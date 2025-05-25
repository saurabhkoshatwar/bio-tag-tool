import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path

# Create necessary directories
DATA_DIR = Path("data")
RESULTS_DIR = Path("results")
DATA_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

def load_tagging_data():
    data_file = DATA_DIR / "tagging_data.json"
    if data_file.exists():
        with open(data_file, 'r') as f:
            return json.load(f)
    return {}

def save_tagging_data():
    data_file = DATA_DIR / "tagging_data.json"
    with open(data_file, 'w') as f:
        json.dump(st.session_state.tagging_data, f)

def load_uploaded_files():
    data_file = DATA_DIR / "uploaded_files.json"
    if data_file.exists():
        with open(data_file, 'r') as f:
            return json.load(f)
    return {}

def save_uploaded_files():
    data_file = DATA_DIR / "uploaded_files.json"
    with open(data_file, 'w') as f:
        json.dump(st.session_state.uploaded_files, f)

def process_uploaded_file(uploaded_file):
    df = pd.read_csv(uploaded_file)
    file_name = uploaded_file.name
    st.session_state.uploaded_files[file_name] = df.to_dict('records')
    if file_name not in st.session_state.tagging_data:
        st.session_state.tagging_data[file_name] = {}
    save_tagging_data()
    save_uploaded_files()

def get_question_words(question):
    return question.split()

def get_entities(entities_str):
    return [e.strip() for e in entities_str.split('|')]

def create_tagging_matrix(question, entities):
    words = get_question_words(question)
    entities = get_entities(entities)
    return words, entities

def get_tag_for_word(word, entity, file_name, question):
    if file_name in st.session_state.tagging_data and question in st.session_state.tagging_data[file_name]:
        if word in st.session_state.tagging_data[file_name][question]:
            if entity in st.session_state.tagging_data[file_name][question][word]:
                return st.session_state.tagging_data[file_name][question][word][entity]
    return 'O'  # Default to 'O' instead of None

def update_tag(word, entity, tag, file_name, question):
    if file_name not in st.session_state.tagging_data:
        st.session_state.tagging_data[file_name] = {}
    if question not in st.session_state.tagging_data[file_name]:
        st.session_state.tagging_data[file_name][question] = {}
    if word not in st.session_state.tagging_data[file_name][question]:
        st.session_state.tagging_data[file_name][question][word] = {}
    st.session_state.tagging_data[file_name][question][word][entity] = tag
    save_tagging_data()

def get_tagged_spans(words, entity_list, file_name, question):
    spans = []
    current_span = None
    
    for i, word in enumerate(words):
        for entity in entity_list:
            tag = get_tag_for_word(word, entity, file_name, question)
            if tag == 'B':
                if current_span:
                    spans.append(current_span)
                current_span = {'start': i, 'entity': entity, 'words': [word]}
            elif tag == 'I' and current_span and current_span['entity'] == entity:
                current_span['words'].append(word)
            elif tag == 'O' and current_span and current_span['entity'] == entity:
                spans.append(current_span)
                current_span = None
    
    if current_span:
        spans.append(current_span)
    
    return spans

def generate_bio_tags(question, entities, file_name):
    words = get_question_words(question)
    entities = get_entities(entities)
    tags = []
    
    for word in words:
        tag = 'O'
        for entity in entities:
            if file_name in st.session_state.tagging_data and question in st.session_state.tagging_data[file_name]:
                if word in st.session_state.tagging_data[file_name][question]:
                    if entity in st.session_state.tagging_data[file_name][question][word]:
                        selected_tag = st.session_state.tagging_data[file_name][question][word][entity]
                        if selected_tag == 'B':
                            tag = f'B-{entity}'
                        elif selected_tag == 'I':
                            tag = f'I-{entity}'
        tags.append(tag)
    
    return ' '.join(tags)

def export_file_results(file_name):
    all_results = []
    for question_data in st.session_state.uploaded_files[file_name]:
        question = question_data['question']
        entities = question_data['entities']
        tags = generate_bio_tags(question, entities, file_name)
        all_results.append({
            'question': question,
            'entities': entities,
            'tags': tags
        })
    
    df = pd.DataFrame(all_results)
    # Save to results folder
    result_file = RESULTS_DIR / f"{file_name}_tagged.csv"
    df.to_csv(result_file, index=False)
    return df

def update_entities(file_name, question_idx, new_entities):
    # Update the entities in the uploaded files
    st.session_state.uploaded_files[file_name][question_idx]['entities'] = '|'.join(new_entities)
    
    # Update the tagging data to reflect entity changes
    question = st.session_state.uploaded_files[file_name][question_idx]['question']
    if file_name in st.session_state.tagging_data and question in st.session_state.tagging_data[file_name]:
        for word in st.session_state.tagging_data[file_name][question]:
            # Remove tags for deleted entities
            for entity in list(st.session_state.tagging_data[file_name][question][word].keys()):
                if entity not in new_entities:
                    del st.session_state.tagging_data[file_name][question][word][entity]
    
    save_tagging_data()
    save_uploaded_files()

# Initialize session state
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = load_uploaded_files()
if 'current_file' not in st.session_state:
    st.session_state.current_file = None
if 'current_question' not in st.session_state:
    st.session_state.current_question = None
if 'tagging_data' not in st.session_state:
    st.session_state.tagging_data = load_tagging_data()
if 'editing_entity' not in st.session_state:
    st.session_state.editing_entity = None
if 'new_entity_input' not in st.session_state:
    st.session_state.new_entity_input = ""

# Main app
st.title("BIO Tagging Tool")

# Sidebar
with st.sidebar:
    st.title("File Management")
    
    # File upload in sidebar
    uploaded_file = st.file_uploader("Upload CSV file", type=['csv'])
    if uploaded_file is not None:
        process_uploaded_file(uploaded_file)
    
    st.markdown("---")
    
    # Files list with export buttons
    for file_name in st.session_state.uploaded_files.keys():
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button(f"📁 {file_name}", key=f"file_{file_name}"):
                st.session_state.current_file = file_name
                st.session_state.current_question = None
        with col2:
            if st.button("📥", key=f"export_{file_name}"):
                results_df = export_file_results(file_name)
                st.download_button(
                    label="Download",
                    data=results_df.to_csv(index=False),
                    file_name=f"{file_name}_tagged.csv",
                    mime="text/csv",
                    key=f"download_{file_name}"
                )

# Questions list
if st.session_state.current_file:
    st.sidebar.title("Questions")
    for idx, question_data in enumerate(st.session_state.uploaded_files[st.session_state.current_file]):
        # Add a unique key for each question button
        button_key = f"q_{st.session_state.current_file}_{idx}"
        # Use a different style for the selected question
        button_style = "background-color: #e6f3ff;" if idx == st.session_state.current_question else ""
        if st.sidebar.button(
            f"Q{idx+1}: {question_data['question'][:30]}...",
            key=button_key,
            help=question_data['question'],
            use_container_width=True,
            type="primary" if idx == st.session_state.current_question else "secondary"
        ):
            st.session_state.current_question = idx

# Main content area
if st.session_state.current_file and st.session_state.current_question is not None:
    question_data = st.session_state.uploaded_files[st.session_state.current_file][st.session_state.current_question]
    question = question_data['question']
    entities = question_data['entities']
    
    st.subheader("Question")
    st.write(question)
    
    words, entity_list = create_tagging_matrix(question, entities)
    
    # Visualization of tagged spans
    st.subheader("Tagged Spans")
    tagged_spans = get_tagged_spans(words, entity_list, st.session_state.current_file, question)
    
    # Create the visualization as a table
    html_content = "<table style='width: 100%; border-collapse: collapse;'>"
    
    # First row: Words
    html_content += "<tr>"
    current_pos = 0
    for span in tagged_spans:
        # Add words before the span
        while current_pos < span['start']:
            html_content += f"<td style='padding: 5px; border: 1px solid #ddd;'>{words[current_pos]}</td>"
            current_pos += 1
        
        # Add the tagged span
        span_text = " ".join(span['words'])
        html_content += f"<td style='padding: 5px; border: 1px solid #ddd; text-decoration: underline;' colspan='{len(span['words'])}'>{span_text}</td>"
        current_pos += len(span['words'])
    
    # Add remaining words
    while current_pos < len(words):
        html_content += f"<td style='padding: 5px; border: 1px solid #ddd;'>{words[current_pos]}</td>"
        current_pos += 1
    html_content += "</tr>"
    
    # Second row: Entity names
    html_content += "<tr>"
    current_pos = 0
    for span in tagged_spans:
        # Add empty cells before the span
        while current_pos < span['start']:
            html_content += "<td style='padding: 5px; border: 1px solid #ddd;'></td>"
            current_pos += 1
        
        # Add the entity name
        html_content += f"<td style='padding: 5px; border: 1px solid #ddd;' colspan='{len(span['words'])}'>{span['entity']}</td>"
        current_pos += len(span['words'])
    
    # Add remaining empty cells
    while current_pos < len(words):
        html_content += "<td style='padding: 5px; border: 1px solid #ddd;'></td>"
        current_pos += 1
    html_content += "</tr>"
    
    html_content += "</table>"
    st.markdown(html_content, unsafe_allow_html=True)
    
    # Tagging matrix
    st.subheader("Tagging Matrix")
    
    # Create columns for the matrix
    cols = st.columns(len(entity_list) + 2)  # +2 for word column and add button
    
    # First row: Controls
    cols[0].write("")  # Empty space for word column
    for i, entity in enumerate(entity_list):
        col1, col2 = cols[i+1].columns([1, 1])
        with col1:
            if st.button("✏️", key=f"edit_{i}"):
                st.session_state.editing_entity = i
                st.rerun()
        with col2:
            if st.button("❌", key=f"delete_{i}"):
                entity_list.remove(entity)
                update_entities(st.session_state.current_file, st.session_state.current_question, entity_list)
                st.rerun()
    
    # Add new entity button in the last column
    with cols[-1]:
        if st.button("➕", key="add_entity"):
            st.session_state.show_new_entity_input = True
    
    # Second row: Entity names
    cols[0].write("Word")
    for i, entity in enumerate(entity_list):
        if st.session_state.editing_entity == i:
            new_name = cols[i+1].text_input("", value=entity, key=f"edit_entity_{i}")
            if new_name != entity:
                entity_list[i] = new_name
                update_entities(st.session_state.current_file, st.session_state.current_question, entity_list)
                st.session_state.editing_entity = None
                st.rerun()
        else:
            cols[i+1].write(entity)
    
    # New entity input row
    if st.session_state.get('show_new_entity_input', False):
        new_entity = st.text_input("Enter new entity name:", key="new_entity_input")
        if new_entity and new_entity not in entity_list:
            entity_list.append(new_entity)
            update_entities(st.session_state.current_file, st.session_state.current_question, entity_list)
            st.session_state.show_new_entity_input = False
            st.rerun()
    
    # Matrix content
    for word_idx, word in enumerate(words):
        cols = st.columns(len(entity_list) + 1)
        cols[0].write(word)
        for i, entity in enumerate(entity_list):
            current_tag = get_tag_for_word(word, entity, st.session_state.current_file, question)
            unique_key = f"radio_{word}_{entity}_{st.session_state.current_file}_{question}_{word_idx}_{i}"
            selected = cols[i+1].radio(
                unique_key,
                options=['O', 'B', 'I'],
                index=['O', 'B', 'I'].index(current_tag),
                key=unique_key,
                label_visibility="collapsed"
            )
            if selected:
                update_tag(word, entity, selected, st.session_state.current_file, question) 