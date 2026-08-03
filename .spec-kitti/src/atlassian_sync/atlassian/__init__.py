"""
Atlassian integration module (Jira + Confluence)
"""

from .config import AtlassianConfig
from .jira import JiraClient
from .confluence import ConfluenceClient

__all__ = [
    'AtlassianConfig',
    'JiraClient',
    'ConfluenceClient'
]

