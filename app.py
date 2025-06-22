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
        try:
            with open(data_file, 'r') as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except Exception:
            return {}
    return {}

def save_tagging_data():
    data_file = DATA_DIR / "tagging_data.json"
    with open(data_file, 'w') as f:
        json.dump(st.session_state.tagging_data, f)

def load_uploaded_files():
    data_file = DATA_DIR / "uploaded_files.json"
    if data_file.exists():
        try:
            with open(data_file, 'r') as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except Exception:
            return {}
    return {}

def save_uploaded_files():
    data_file = DATA_DIR / "uploaded_files.json"
    with open(data_file, 'w') as f:
        json.dump(st.session_state.uploaded_files, f)

def parse_bio_tags(tags_str):
    """Parse BIO tags string into a dictionary of word-entity-tag mappings."""
    if not tags_str or pd.isna(tags_str):
        return {}
    
    tags = tags_str.split()
    result = {}
    
    current_entity = None
    for i, tag in enumerate(tags):
        if tag.startswith('B-'):
            current_entity = tag[2:]
            result[i] = {'entity': current_entity, 'tag': 'B'}
        elif tag.startswith('I-'):
            current_entity = tag[2:]
            result[i] = {'entity': current_entity, 'tag': 'I'}
        else:
            current_entity = None
            result[i] = {'entity': None, 'tag': 'O'}
    
    return result

def get_entities(entities_str):
    """Parse comma-separated entities string into a list."""
    return [e.strip() for e in entities_str.split(',')]

def process_uploaded_file(uploaded_file):
    df = pd.read_csv(uploaded_file)
    file_name = uploaded_file.name
    
    # Convert DataFrame to records
    records = df.to_dict('records')
    
    # Initialize tagging data for this file
    if file_name not in st.session_state.tagging_data:
        st.session_state.tagging_data[file_name] = {}
    
    # Process each record
    for record in records:
        question = record['question']
        # Convert pipe-separated entities to comma-separated if needed
        if '|' in record['entities']:
            record['entities'] = record['entities'].replace('|', ',')
        entities = record['entities']
        words = get_question_words(question)
        entity_list = get_entities(entities)
        
        # Initialize question data in tagging_data
        if question not in st.session_state.tagging_data[file_name]:
            st.session_state.tagging_data[file_name][question] = {}
        
        # If tags column exists, parse it
        if 'tags' in record and record['tags']:
            parsed_tags = parse_bio_tags(record['tags'])
            
            # Initialize word data
            for i, word in enumerate(words):
                if word not in st.session_state.tagging_data[file_name][question]:
                    st.session_state.tagging_data[file_name][question][word] = {}
                
                # If we have parsed tags for this word
                if i in parsed_tags:
                    tag_info = parsed_tags[i]
                    if tag_info['entity']:
                        # Set the tag for the specific entity
                        st.session_state.tagging_data[file_name][question][word][tag_info['entity']] = tag_info['tag']
                    else:
                        # Set 'O' tag for all entities
                        for entity in entity_list:
                            st.session_state.tagging_data[file_name][question][word][entity] = 'O'
                else:
                    # If no tag found, set 'O' for all entities
                    for entity in entity_list:
                        st.session_state.tagging_data[file_name][question][word][entity] = 'O'
    
    # Save the records to uploaded_files
    st.session_state.uploaded_files[file_name] = records
    
    # Save both data structures
    save_tagging_data()
    save_uploaded_files()

def get_question_words(question):
    return question.split()

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
            'entities': entities,  # This will now be comma-separated
            'tags': tags
        })
    
    df = pd.DataFrame(all_results)
    # Save to results folder
    result_file = RESULTS_DIR / f"{file_name}_tagged.csv"
    df.to_csv(result_file, index=False)
    return df

def update_entities(file_name, question_idx, new_entities):
    # Update the entities in the uploaded files
    st.session_state.uploaded_files[file_name][question_idx]['entities'] = ','.join(new_entities)
    
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

# Main content area
if st.session_state.current_file:
    st.header(f"Questions in {st.session_state.current_file}")
    
    questions = st.session_state.uploaded_files[st.session_state.current_file]
    questions_per_page = 50
    total_questions = len(questions)
    total_pages = (total_questions - 1) // questions_per_page + 1 if total_questions > 0 else 1
    page_labels = [
        f"Questions {i*questions_per_page+1}-{min((i+1)*questions_per_page, total_questions)}" 
        for i in range(total_pages)
    ]
    if total_questions > 0:
        page_options = list(range(1, total_pages+1))
        page = st.selectbox("Select questions:", options=page_options, format_func=lambda i: page_labels[i-1], index=0)
        if page is None:
            page = 1
        start_idx = int((page - 1) * questions_per_page)
        end_idx = int(min(start_idx + questions_per_page, total_questions))
    else:
        page = 1
        start_idx = 0
        end_idx = 0
    
    # Create a container for the scrollable content
    questions_container = st.container()
    
    with questions_container:
        for idx in range(start_idx, end_idx):
            question_data = questions[idx]
            question = question_data['question']
            entities = question_data['entities']
            words, entity_list = create_tagging_matrix(question, entities)

            # Question header
            st.subheader(f"Question {idx+1}")

            # Always show the tagged spans visualization
            tagged_spans = get_tagged_spans(words, entity_list, st.session_state.current_file, question)
            html_content = "<table style='width: 100%; border-collapse: collapse;'>"
            # First row: Words
            html_content += "<tr>"
            current_pos = 0
            for span in tagged_spans:
                while current_pos < span['start']:
                    html_content += f"<td style='padding: 5px; border: 1px solid #ddd;'>{words[current_pos]}</td>"
                    current_pos += 1
                span_text = " ".join(span['words'])
                html_content += f"<td style='padding: 5px; border: 1px solid #ddd; text-decoration: underline;' colspan='{len(span['words'])}'>{span_text}</td>"
                current_pos += len(span['words'])
            while current_pos < len(words):
                html_content += f"<td style='padding: 5px; border: 1px solid #ddd;'>{words[current_pos]}</td>"
                current_pos += 1
            html_content += "</tr>"
            # Second row: Entity names
            html_content += "<tr>"
            current_pos = 0
            for span in tagged_spans:
                while current_pos < span['start']:
                    html_content += "<td style='padding: 5px; border: 1px solid #ddd;'></td>"
                    current_pos += 1
                html_content += f"<td style='padding: 5px; border: 1px solid #ddd;' colspan='{len(span['words'])}'>{span['entity']}</td>"
                current_pos += len(span['words'])
            while current_pos < len(words):
                html_content += "<td style='padding: 5px; border: 1px solid #ddd;'></td>"
                current_pos += 1
            html_content += "</tr>"
            html_content += "</table>"
            st.markdown(html_content, unsafe_allow_html=True)

            # Tagging controls inside expander
            with st.expander("Tagging Controls"):
                st.markdown("---")
                st.subheader("Tagging Controls")
                # Create columns for the matrix
                cols = st.columns(len(entity_list) + 2)  # +2 for word column and add button
                # First row: Controls
                cols[0].write("")  # Empty space for word column
                for i, entity in enumerate(entity_list):
                    col1, col2 = cols[i+1].columns([1, 1])
                    with col1:
                        if st.button("✏️", key=f"edit_{idx}_{i}"):
                            st.session_state.editing_entity = i
                            st.rerun()
                    with col2:
                        if st.button("❌", key=f"delete_{idx}_{i}"):
                            entity_list.remove(entity)
                            update_entities(st.session_state.current_file, idx, entity_list)
                            st.rerun()
                # Add new entity button in the last column
                with cols[-1]:
                    if st.button("➕", key=f"add_entity_{idx}"):
                        st.session_state.show_new_entity_input = idx
                # Second row: Entity names
                cols[0].write("Word")
                for i, entity in enumerate(entity_list):
                    if st.session_state.editing_entity == i:
                        new_name = cols[i+1].text_input("", value=entity, key=f"edit_entity_{idx}_{i}")
                        if new_name != entity:
                            entity_list[i] = new_name
                            update_entities(st.session_state.current_file, idx, entity_list)
                            st.session_state.editing_entity = None
                            st.rerun()
                    else:
                        cols[i+1].write(entity)
                # New entity input row
                if st.session_state.get('show_new_entity_input') == idx:
                    new_entity = st.text_input("Enter new entity name:", key=f"new_entity_input_{idx}")
                    if new_entity and new_entity not in entity_list:
                        entity_list.append(new_entity)
                        update_entities(st.session_state.current_file, idx, entity_list)
                        st.session_state.show_new_entity_input = None
                        st.rerun()
                # Matrix content
                for word_idx, word in enumerate(words):
                    cols = st.columns(len(entity_list) + 1)
                    cols[0].write(word)
                    for i, entity in enumerate(entity_list):
                        current_tag = get_tag_for_word(word, entity, st.session_state.current_file, question)
                        unique_key = f"radio_{idx}_{word_idx}_{i}_{word}_{entity}_{st.session_state.current_file}"
                        selected = cols[i+1].radio(
                            unique_key,
                            options=['O', 'B', 'I'],
                            index=['O', 'B', 'I'].index(current_tag),
                            key=unique_key,
                            label_visibility="collapsed"
                        )
                        if selected:
                            update_tag(word, entity, selected, st.session_state.current_file, question)
                st.markdown("---") 