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
        'navigate': 'Navigation',
        'click': 'Click',
        'scroll': 'Scroll',
        'select': 'Select',
        'keydown': 'Type',
        'annotate': 'Annotate',
        'upload': 'Upload',
        'drag_and_drop': 'Drag and Drop',

        #Additional
        'keyup': 'Type',
}


process_map = {
        'AP1. Locate/Navigate': ['Navigation', 'Scroll', 'Click', 'Navigation'],
        'AP2. Search': ['Type', 'Query', 'Click_Search'],
        'SP1. Upload resources': ['Navigation', 'Click_Upload'],
        'SP2. Knowledge-clip': ['Scroll', 'Click k-clip'],
        'SP3. Filling information': ['Scroll', 'Type', 'Click_Save'],
        'ShP1. Annotate': ['Scroll', 'Select', 'Click_Annotate', 'Type', 'Click_Post'],
        'ShP2. Highlight': ['Scroll', 'Select', 'Click_Highlight'],
        'ApP1. Using Pushes': ['Push', 'Click_Push_Panel'],

        # Additional Generic
        'AP1.1a Locate/Navigate': ['Navigation', 'Navigation', 'Navigation'],
        'AP1.3a Locate/Navigate': ['Navigation', 'Click', 'Click'],
        'AP1.3b Locate/Navigate': ['Navigation', 'Click'],
        'AP1.9a Locate/Navigate': [ 'Click', 'Click', 'Click'],
        'AP1.9b Locate/Navigate': [ 'Click', 'Click'],

        'SP3.7a Filling information': ['Type', 'Click'],
        'SP3.7b Filling information': ['Click', 'Type'],
        'SP3.9a Filling information': ['Type', 'Type', 'Type', 'Type'],
        'SP3.10a Filling information': ['Click', 'Type', 'Type', 'Click'],
        'SP3.10b Filling information': ['Click', 'Type', 'Type', 'Type', 'Click'],
        'SP3.10c Filling information': ['Click', 'Type', 'Click'],
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
                'image': step.get('image', ''),
                'title': step.get('title', '')
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


def reformat_to_nested(data):
    # Use defaultdict to organize the data
    data = process_serialize(data)
    users = defaultdict(lambda: defaultdict(list))

    for entry in data:
        user_key = (entry["userid"], entry["sessionId"], entry["taskName"], entry["seq_counter"])
        process_name = entry["KM_Process"]
        step = {
            "type": entry["type"],
            "text": entry["text"],
            "title": entry["title"],  #new Field S.S
            "url": entry["url"],
            "description": entry["description"],
            "image": entry["image"]
        }
        users[user_key][process_name].append(step)

    # Build the final structured list
    km_process = []
    for (userid, sessionId, taskName, seq_counter), processes in users.items():
        for name, steps in processes.items():
            metadata = {
                "image": get_last_non_empty_image(steps), #new Field S.S TODO
                "name": name.split(" ", 1)[1],
                "code" : name.split(" ", 1)[0], #new Field S.S
                "title" : "", #new Field S.S
                "steps": set_all_images_to_empty(steps)
            }
            km_process.append(metadata)

    return {
        "userid": userid,
        "sessionId": sessionId,
        "taskName": taskName,
        "dataComicsID": "dc-" + sessionId,
        "KM_Process": km_process
    }


def set_all_images_to_empty(data):
    # Loop through each item in the array
    for item in data:
        # Set the image field to an empty string
        item["image"] = ""

    return data


def process_serialize(data):
    # Ensure data is a list of dictionaries
    if not isinstance(data, list):
        raise ValueError("Data should be a list of dictionaries")

    # Initialize variables to track the last KM_Process and image value
    last_km_process = None
    seq_counter = 0

    for entry in data:
        current_km_process = entry.get("KM_Process")

        # Increment image_counter if KM_Process changes
        if current_km_process != last_km_process:
            seq_counter += 1
            last_km_process = current_km_process

        # Update the image value in the entry
        entry["seq_counter"] = seq_counter

    return data


def get_last_non_empty_image(data):
    # Initialize the variable to store the last non-empty image value
    last_non_empty_image = ""

    # Loop through each item in the array
    for item in data:
        # Check if the image field is non-empty
        if item.get("image"):
            last_non_empty_image = item["image"]

    return last_non_empty_image


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
