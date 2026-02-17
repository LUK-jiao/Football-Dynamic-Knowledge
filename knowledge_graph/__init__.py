"""
Knowledge Graph Package
"""

from knowledge_graph.neo4j_writer import Neo4jWriter
from knowledge_graph.config import get_neo4j_config

__all__ = ['Neo4jWriter', 'get_neo4j_config']
