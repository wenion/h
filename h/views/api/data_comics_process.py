"""
HTTP/REST API for storage and retrieval of annotation data.

This module contains the views which implement our REST API, mounted by default
at ``/api``. Currently, the endpoints are limited to:

- basic CRUD (create, read, update, delete) operations on annotations
- annotation search
- a handful of authentication related endpoints

It is worth noting up front that in general, authorization for requests made to
each endpoint is handled outside of the body of the view functions. In
particular, requests to the CRUD API endpoints are protected by the Pyramid
authorization system. You can find the mapping between annotation "permissions"
objects and Pyramid ACLs in :mod:`h.traversal`.
"""
import json
import re
from pyramid import i18n
from collections import defaultdict

from h.models_redis import start_user_event_record, finish_user_event_record
from h.models_redis import batch_user_event_record, update_user_event_record, delete_user_event_record
from h.views.api.user_manipultations import batch_steps
from h.security import Permission
from h.views.api.config import api_config

_ = i18n.TranslationStringFactory(__package__)


action_mapping = {
        # action/type + text columns
        ('click', 'Highlight'): 'Click_Highlight',
        ('click', 'Search'): 'Click_Search',
        ('click', 'Upload'): 'Click_Upload',
        ('click', 'k-clip'): 'Click k-clip',
        ('click', 'Post'): 'Click_Post',
        'recording': 'Navigation',
        'click': 'Click',
        'scroll': 'Scroll',
        'select': 'Select',
        'keydown': 'Type',
        'annotate': 'Annotate',
        'upload': 'Upload',
        'drag_and_drop': 'Drag and Drop',
}


process_map = {
        'AP1. Locate/Navigate': ['Navigation', 'Scroll', 'Click', 'Navigation'],
        'AP2. Search': ['Type', 'Query', 'Click_Search'],
        'SP1. Upload resources': ['Navigation', 'Click_Upload'],
        'SP2. Knowledge-clip': ['Scroll', 'Click k-clip'],
        'SP3. Filling information': ['Scroll', 'Type', 'Click_Save'],
        'ShP1. Annotate': ['Scroll', 'Select', 'Click_Annotate', 'Type', 'Click_Post'],
        'ShP2. Highlight': ['Scroll', 'Select', 'Click_Highlight'],
        'ApP1. Using Pushes': ['Push', 'Click_Push_Panel']    
}

    
def map_action_types(action_list, action_mapping):
    """
    Map the 'type' attribute in the action_list to values from the type_mapping dictionary.

    Parameters:
    action_list (list): List of dictionaries containing 'taskName' and 'type'.
    action_mapping (dict): Dictionary mapping original 'type' values to new values.

    Returns:
    list: Updated list with mapped 'type' values.
    """
    for entry in action_list:
        action_text_key = (entry['type'], entry['text'])
        if action_text_key in action_mapping:
            entry['type'] = action_mapping[action_text_key]
        elif entry['type'] in action_mapping:
            entry['type'] = action_mapping[entry['type']]
    return action_list


def ExceptionHandler(action_list):
    
    """
    Resolve/Flag issues such as repetition, interruptions, loops, deviations/variations.

    Parameters:
    action_list (list): List of dictionaries containing 'taskName' and 'type' <- action sequences.

    Returns:
    list: index of flagged enteries in the json file
    """
        
    flagged_entries = []
    previous_type = None

    # Iterate through the list to check for consecutive repeating 'type' values
    for index, entry in enumerate(action_list):
        current_type = entry['type']
        if current_type == previous_type:
            flagged_entries.append({
                'index': index,
                'taskName': entry['taskName'],
                'type': current_type,
                'flag': 'Consecutive repeating type'
            })
        previous_type = current_type

    return flagged_entries


def action_mapper(data):

    # List to store the extracted information
    action_sequence = []

    #1: Iterate through the JSON data to extract key fields
    for entry in data:
        task_name = entry.get('taskName', 'No taskName')
        userid = entry.get('userid', '')
        sessionId = entry.get('sessionId', '')
        
        for step in entry.get('steps', []):
            action_sequence.append({
                'userid': userid,
                'sessionId': sessionId,
                'taskName': task_name,
                'type': step.get('type', 'No type'),
                'text': step.get('text', ''),
                'url': step.get('url', ''),
                'description': step.get('description', ''),
                'image': step.get('image', '')
            })
            
    #2:  Handle & Flag/Fix Exceptions
    flagged_entries = ExceptionHandler(action_sequence)
    ## print(flagged_entries)
    
    #3:  Map actions from ShareFlow with  TAC - Actions Dictionaire 
    # Map the type values
    mapped_action_list = map_action_types(action_sequence, action_mapping)


    return mapped_action_list


def process_labeller (action_list):
    
    """
    Scan through the 'action_list' for specified consecutive action values in
    in the 'type' column and map them with the corresponding value from the process_mapping dictionary.

    Parameters:
    action_list (list): List of dictionaries containing 'taskName' and 'type'.
    process_map (dict): Dictionary mapping sequences of 'type' values to labels.

    Returns:
    list: Updated list with an additional attribute showing the process label where the pattern was matched.
    """ 
    # Convert patterns dictionary for easier access
    pattern_keys = list(process_map.keys())
    pattern_values = list(process_map.values())

    # Iterate through the list to check for pattern matches
    i = 0
    while i < len(action_list):
        match_found = False
        for pattern_key, pattern_value in zip(pattern_keys, pattern_values):
            pattern_length = len(pattern_value)
            if i + pattern_length <= len(action_list):
                if all(action_list[i + j]['type'] == pattern_value[j] for j in range(pattern_length)):
                    for k in range(pattern_length):
                        action_list[i + k]['KM_Process'] = pattern_key
                    i += pattern_length - 1
                    match_found = True
                    break
        if not match_found:
            action_list[i]['KM_Process'] = "NO MATCH"
        i += 1                
                        
    return action_list


def process_labeller_re(action_list):
    """
    Scan through the 'action_list' for specified consecutive action values in the 'type' column
    and map them with the corresponding value from the process_map dictionary.

    Parameters:
    action_list (list): List of dictionaries containing 'taskName' and 'type'.
    process_map (dict): Dictionary mapping sequences of 'type' values to labels.

    Returns:
    list: Updated list with an additional attribute showing the process label where the pattern was matched.
    """
    
    # Create a string representation of the 'type' column
    type_sequence = ' '.join(entry['type'] for entry in action_list)
    
    # Create a dictionary to store the matches and their positions
    matches = {}
    
    for pattern_key, pattern_value in process_map.items():
        pattern_str = ' '.join(pattern_value)
        for match in re.finditer(pattern_str, type_sequence):
            start, end = match.span()
            start_index = len(type_sequence[:start].split())
            end_index = len(type_sequence[:end].split())
            matches[(start_index, end_index)] = pattern_key
    
    # Label the actions based on the matched patterns
    for (start, end), pattern_key in matches.items():
        for i in range(start, end):
            action_list[i]['KM_Process'] = pattern_key
    
    # Label remaining actions as "NO MATCH"
    for entry in action_list:
        if 'KM_Process' not in entry:
            entry['KM_Process'] = "NO MATCH"
    
    return action_list


def reformat_to_nested(flat_data):
    nested_data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

    for entry in flat_data:
        userid = entry["userid"]
        sessionId = entry["sessionId"]
        taskName = entry["taskName"]
        KM_Process = entry["KM_Process"]
        step = {
            "type": entry["type"],
            "text": entry["text"],
            "url": entry["url"],
            "description": entry["description"],
            "image": entry["image"]
        }
        nested_data[userid][sessionId][taskName][KM_Process].append(step)

    # Convert nested defaultdicts to normal dicts
    nested_data = {userid: {sessionId: {taskName: dict(KM_Process) for taskName, KM_Process in session.items()} for sessionId, session in user.items()} for userid, user in nested_data.items()}
    
    # Transform to desired format
    formatted_data = []
    for userid, sessions in nested_data.items():
        for sessionId, tasks in sessions.items():
            for taskName, KM_Processes in tasks.items():
                formatted_entry = {
                    'userid': userid,
                    'sessionId': sessionId,
                    'taskName': taskName,
                    'KM_Process': KM_Processes
                }
                formatted_data.append(formatted_entry)

    return formatted_data


# @api_config(
#     versions=["v1", "v2"],
#     route_name="api.data_comics",
#     request_method="GET",
#     link_name="data_comics",
#     description="Get the data comics",
# )
def data_commics_process(share_flow_data):
    action_list = action_mapper(share_flow_data)

    # Scan and label KM Process
    updated_process_map_flat_data = process_labeller(action_list)

    # Reformat the flat data into nested JSON
    nested_data = reformat_to_nested(updated_process_map_flat_data)
    return nested_data

    # print(json.dumps(nested_data, indent=4))
