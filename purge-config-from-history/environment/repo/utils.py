"""Utility functions for the application"""

def format_response(data):
    """Format API response data"""
    return {
        'status': 'success',
        'data': data
    }

def validate_input(data):
    """Validate input data"""
    if not data:
        raise ValueError("Input data cannot be empty")
    return True
