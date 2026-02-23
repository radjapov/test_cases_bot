import json
from typing import Optional, Tuple, Dict

def parse_endpoint_string(text: str) -> Optional[Tuple[str, str, Optional[Dict]]]:
    """
    Parses a string containing an HTTP method, endpoint, and optional JSON body.

    Args:
        text: The input string, e.g., "POST /users/create
{"name": "John"}"

    Returns:
        A tuple containing the method, endpoint, and JSON body dict, or None if parsing fails.
    """
    lines = text.strip().split('\n')
    
    if not lines:
        return None

    # Parse the first line for method and endpoint
    first_line_parts = lines[0].strip().split()
    if len(first_line_parts) != 2:
        return None
        
    method, endpoint = first_line_parts
    
    # Check for a JSON body
    json_body = None
    if len(lines) > 1:
        json_string = "".join(lines[1:])
        try:
            json_body = json.loads(json_string)
        except json.JSONDecodeError:
            # If it's not valid json, we can just ignore it or handle as an error
            # For now, we'll just ignore it.
            pass
            
    return method.upper(), endpoint, json_body
