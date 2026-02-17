"""
Neo4j Configuration
"""

import os
from typing import Dict


def get_neo4j_config() -> Dict[str, str]:
    """
    Get Neo4j connection configuration from environment variables.
    
    Returns:
        Dictionary with uri, user, and password
    """
    return {
        'uri': os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
        'user': os.getenv('NEO4J_USER', 'neo4j'),
        'password': os.getenv('NEO4J_PASSWORD', 'password')
    }
