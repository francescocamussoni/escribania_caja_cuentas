"""
Utilidades compartidas para procesamiento de Jira y Confluence
"""

from datetime import datetime
from typing import Any, Dict, List


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    Limpia un nombre de archivo para que sea válido en el sistema de archivos
    
    Args:
        filename: Nombre original
        max_length: Longitud máxima
        
    Returns:
        Nombre sanitizado
    """
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename[:max_length].strip()


def extract_text_from_adf(adf_content: Any) -> str:
    """
    Extrae texto plano desde el formato ADF (Atlassian Document Format) de Jira
    
    Args:
        adf_content: Contenido en formato ADF (dict, str o None)
        
    Returns:
        Texto extraído
    """
    if not adf_content:
        return ""
    
    if isinstance(adf_content, str):
        return adf_content
    
    if not isinstance(adf_content, dict):
        return str(adf_content)
    
    text_parts = []
    
    def extract_from_node(node):
        """Extrae texto de un nodo ADF recursivamente"""
        if isinstance(node, dict):
            node_type = node.get('type', '')
            
            # Nodos de texto
            if node_type == 'text':
                text_parts.append(node.get('text', ''))
            
            # Nodos con contenido hijo
            if 'content' in node:
                for child in node['content']:
                    extract_from_node(child)
                
                # Agregar saltos de línea después de párrafos y headings
                if node_type in ['paragraph', 'heading']:
                    text_parts.append('\n\n')
                elif node_type == 'listItem':
                    text_parts.append('\n')
        
        elif isinstance(node, list):
            for item in node:
                extract_from_node(item)
    
    extract_from_node(adf_content)
    return ''.join(text_parts).strip()


def format_date(date_str: str, format_str: str = '%Y-%m-%d %H:%M') -> str:
    """
    Formatea una fecha ISO a formato legible
    
    Args:
        date_str: Fecha en formato ISO
        format_str: Formato de salida
        
    Returns:
        Fecha formateada
    """
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime(format_str)
    except Exception:
        return date_str


def extract_acceptance_criteria(issue: Dict) -> List[str]:
    """
    Extrae acceptance criteria de un issue de Jira
    
    Args:
        issue: Issue de Jira
        
    Returns:
        Lista de criterios de aceptación
    """
    fields = issue.get('fields', {})
    criteria = []
    
    # Buscar en campos personalizados comunes
    for field_key, field_value in fields.items():
        if field_key.startswith('customfield_') and field_value:
            # Intentar extraer si es ADF
            if isinstance(field_value, dict):
                text = extract_text_from_adf(field_value)
                if text and ('acceptance' in field_key.lower() or 'criteria' in text.lower()):
                    criteria.append(text)
            elif isinstance(field_value, str) and 'criteria' in field_value.lower():
                criteria.append(field_value)
    
    # Buscar en descripción
    description = extract_text_from_adf(fields.get('description'))
    if description:
        # Buscar secciones de acceptance criteria en la descripción
        lines = description.split('\n')
        in_criteria_section = False
        for line in lines:
            line_lower = line.lower()
            if 'acceptance criteria' in line_lower or 'criterios de aceptación' in line_lower:
                in_criteria_section = True
                continue
            if in_criteria_section:
                if line.strip().startswith(('-', '*', '•')):
                    criteria.append(line.strip()[1:].strip())
                elif line.strip() == '':
                    in_criteria_section = False
    
    return criteria


def get_issue_priority(issue: Dict) -> str:
    """Obtiene la prioridad de un issue"""
    priority = issue.get('fields', {}).get('priority')
    if priority:
        return priority.get('name', 'None')
    return 'None'


def get_issue_status(issue: Dict) -> str:
    """Obtiene el estado de un issue"""
    status = issue.get('fields', {}).get('status')
    if status:
        return status.get('name', 'Unknown')
    return 'Unknown'


def get_issue_type(issue: Dict) -> str:
    """Obtiene el tipo de un issue"""
    issue_type = issue.get('fields', {}).get('issuetype')
    if issue_type:
        return issue_type.get('name', 'Unknown')
    return 'Unknown'


def get_story_points(issue: Dict) -> int:
    """
    Extrae story points de un issue
    
    Args:
        issue: Issue de Jira
        
    Returns:
        Story points o 0 si no tiene
    """
    fields = issue.get('fields', {})
    
    # Buscar en campos comunes de story points
    story_point_fields = [
        'customfield_10016',  # Cloud común
        'customfield_10004',  # Server común
        'customfield_10002',
        'story_points',
        'storyPoints'
    ]
    
    for field in story_point_fields:
        value = fields.get(field)
        if value is not None:
            try:
                return int(float(value))
            except (ValueError, TypeError):
                continue
    
    return 0


def get_epic_link(issue: Dict) -> str:
    """
    Obtiene el epic link de un issue
    
    Args:
        issue: Issue de Jira
        
    Returns:
        Epic key o empty string
    """
    fields = issue.get('fields', {})
    
    # Buscar en campos comunes de epic link
    epic_link_fields = [
        'customfield_10014',  # Cloud común
        'customfield_10008',  # Server común
        'parent'
    ]
    
    for field in epic_link_fields:
        value = fields.get(field)
        if value:
            if isinstance(value, str):
                return value
            elif isinstance(value, dict):
                return value.get('key', '')
    
    return ''


def split_issues_by_type(issues: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Separa una lista de issues en historias, tareas y otros tipos.

    Refleja el modelo de jerarquía esperado en este proyecto:
      Épica
        ├── Tarea       (Task — hijo directo, sin subtareas)
        └── Historia    (Story — hijo directo, con subtareas)

    Tipos soportados:
      - 'stories': issues de tipo Story / Historia / User Story
      - 'tasks':   issues de tipo Task / Tarea
      - 'other':   cualquier otro tipo (Bug, Improvement, Spike, etc.)

    Args:
        issues: Lista de issues hijos de una épica

    Returns:
        Diccionario con tres listas:
            {'stories': [...], 'tasks': [...], 'other': [...]}
    """
    story_aliases = {'story', 'historia', 'user story', 'historia de usuario'}
    task_aliases = {'task', 'tarea'}

    result: Dict[str, List[Dict]] = {'stories': [], 'tasks': [], 'other': []}

    for issue in issues:
        type_name = (get_issue_type(issue) or '').strip().lower()
        if type_name in story_aliases:
            result['stories'].append(issue)
        elif type_name in task_aliases:
            result['tasks'].append(issue)
        else:
            result['other'].append(issue)

    return result


def group_issues_by_component(issues: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Agrupa issues por componente
    
    Args:
        issues: Lista de issues
        
    Returns:
        Diccionario {componente: [issues]}
    """
    grouped = {}
    
    for issue in issues:
        components = issue.get('fields', {}).get('components', [])
        
        if not components:
            component_name = 'Sin componente'
        else:
            # Usar el primer componente
            component_name = components[0].get('name', 'Sin componente')
        
        if component_name not in grouped:
            grouped[component_name] = []
        grouped[component_name].append(issue)
    
    return grouped


def sort_issues_by_priority(issues: List[Dict]) -> List[Dict]:
    """
    Ordena issues por prioridad
    
    Args:
        issues: Lista de issues
        
    Returns:
        Lista ordenada
    """
    priority_order = {
        'Highest': 0,
        'High': 1,
        'Medium': 2,
        'Low': 3,
        'Lowest': 4,
        'None': 5
    }
    
    def get_priority_order(issue):
        priority = get_issue_priority(issue)
        return priority_order.get(priority, 99)
    
    return sorted(issues, key=get_priority_order)

