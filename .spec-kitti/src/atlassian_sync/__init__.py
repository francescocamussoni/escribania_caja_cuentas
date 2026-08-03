"""
Spec-Kitti Atlassian Sync Module
Sincronización de Jira y Confluence para generar especificaciones
"""

__version__ = "0.2.0"
__author__ = "Spec-Kitti Team"

# Exports principales
from .atlassian.config import AtlassianConfig
from .atlassian.jira import JiraClient
from .atlassian.confluence import ConfluenceClient
from .generators.spec import SpecGenerator

__all__ = [
    'AtlassianConfig',
    'JiraClient',
    'ConfluenceClient',
    'SpecGenerator'
]
