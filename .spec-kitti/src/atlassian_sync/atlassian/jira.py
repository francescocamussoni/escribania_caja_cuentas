"""
Cliente para interactuar con la API de Jira
"""

import requests
from typing import List, Dict, Optional
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)


class JiraClient:
    """Cliente para la API REST de Jira"""
    
    def __init__(self, base_url: str, username: str, api_token: str):
        """
        Inicializa el cliente de Jira
        
        Args:
            base_url: URL base de Jira (ej: https://tu-dominio.atlassian.net)
            username: Email de usuario de Atlassian
            api_token: Token de API de Atlassian (mismo que Confluence)
        """
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/rest/api/2"
        self.api_base_v3 = f"{self.base_url}/rest/api/3"  # API v3 para endpoints modernos
        self.session = requests.Session()
        self.session.auth = (username, api_token)
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        logger.info(f"Cliente Jira inicializado para {base_url}")
    
    def get_projects(self) -> List[Dict]:
        """
        Obtiene la lista de proyectos disponibles
        
        Returns:
            Lista de proyectos
        """
        url = f"{self.api_base}/project"
        params = {
            'expand': 'description,lead'
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        projects = response.json()
        
        logger.info(f"Obtenidos {len(projects)} proyectos")
        return projects
    
    def get_project_by_key(self, project_key: str) -> Dict:
        """
        Obtiene información de un proyecto específico
        
        Args:
            project_key: Clave del proyecto (ej: PROJ)
            
        Returns:
            Datos del proyecto
        """
        url = f"{self.api_base}/project/{project_key}"
        
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_epics(self, project_key: str) -> List[Dict]:
        """
        Obtiene todas las épicas de un proyecto
        
        Args:
            project_key: Clave del proyecto
            
        Returns:
            Lista de épicas
        """
        jql = f'project = {project_key} AND type = Epic ORDER BY created DESC'
        
        return self.search_issues(jql)
    
    def get_subtasks_for_issue(self, parent_key: str) -> List[Dict]:
        """
        Obtiene las subtareas (issue type 'Sub-task') de un issue padre.

        Usa el campo 'subtasks' del endpoint /issue/{key}, que devuelve solo
        issues de tipo Sub-task que cuelgan directamente del issue padre.
        Es decir, NO devuelve historias/tareas vinculadas a una épica vía
        Epic Link — para eso se usa get_issues_by_epic.

        Típicamente se llama con la key de una historia o tarea, no de una épica.

        Args:
            parent_key: Key del issue padre (ej: PROJ-456 — una historia)

        Returns:
            Lista de subtareas con todos sus campos
        """
        try:
            url = f"{self.api_base}/issue/{parent_key}"
            params = {
                'fields': 'subtasks'
            }

            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            subtasks = data.get('fields', {}).get('subtasks', [])

            if not subtasks:
                logger.debug(f"No se encontraron subtareas para {parent_key}")
                return []

            detailed_issues = []
            for subtask_ref in subtasks:
                subtask_key = subtask_ref.get('key')
                if subtask_key:
                    try:
                        full_issue = self.get_issue_by_key(subtask_key)
                        detailed_issues.append(full_issue)
                        logger.debug(f"Descargada subtarea: {subtask_key}")
                    except Exception as e:
                        logger.warning(f"No se pudo descargar subtarea {subtask_key}: {e}")

            logger.info(f"Obtenidas {len(detailed_issues)} subtareas para {parent_key}")
            return detailed_issues

        except Exception as e:
            logger.error(f"Error obteniendo subtareas de {parent_key}: {e}")
            return []

    # Alias retrocompatible — algunos consumidores externos pueden seguir
    # usando el nombre antiguo. Marcado como deprecated en favor del nuevo nombre.
    def get_child_issues(self, parent_key: str) -> List[Dict]:
        """DEPRECATED: usar get_subtasks_for_issue. Mantenido por compatibilidad."""
        logger.debug("get_child_issues está deprecated, usar get_subtasks_for_issue")
        return self.get_subtasks_for_issue(parent_key)

    def get_issues_by_epic(self, epic_key: str) -> List[Dict]:
        """
        Obtiene todas las historias/tareas vinculadas a una épica.

        Una épica tiene como hijos típicamente issues de tipo Story/Task que se
        vinculan vía 'parent' (Team-Managed) o 'Epic Link' (Company-Managed).
        Las Sub-tasks NO son hijos directos de la épica — son hijos de las
        historias/tareas. Para obtener las subtareas usar get_subtasks_for_issue.

        Usa múltiples estrategias para máxima compatibilidad con distintas
        configuraciones de Jira (Cloud Next-gen, Cloud Classic, Server, etc.).

        Args:
            epic_key: Key de la épica (ej: PROJ-123)

        Returns:
            Lista de issues hijos de la épica (Story, Task, Bug, etc.)
        """
        # MÉTODO 1: JQL parent = epic_key (Next-gen / Team-managed projects)
        # Es el método moderno y el más común en Jira Cloud actual.
        try:
            logger.debug(f"Método 1: JQL parent = {epic_key}")

            jql = f'parent = {epic_key}'
            issues = self.search_issues(jql)

            if issues:
                logger.info(f"Método parent JQL: Obtenidos {len(issues)} issues para épica {epic_key}")
                return issues

        except Exception as e:
            logger.warning(f"Método parent JQL falló: {e}")

        # MÉTODO 2: JQL "Epic Link" = epic_key (company-managed projects clásicos)
        try:
            logger.debug(f"Método 2: JQL 'Epic Link' = {epic_key}")

            jql = f'"Epic Link" = {epic_key}'
            issues = self.search_issues(jql)

            if issues:
                logger.info(f"Método 'Epic Link': Obtenidos {len(issues)} issues para épica {epic_key}")
                return issues

        except Exception as e:
            logger.warning(f"Método 'Epic Link' falló: {e}")

        # MÉTODO 3: issueFunction in epicsOf (algunas instancias soportan esto)
        try:
            logger.debug(f"Método 3: Buscando issues con issueFunction")

            project_key = epic_key.split('-')[0]
            jql = f'project = {project_key} AND issueFunction in epicsOf("key = {epic_key}")'

            logger.debug(f"JQL issueFunction: {jql}")
            issues = self.search_issues(jql)

            if issues:
                logger.info(f"Método issueFunction: Obtenidos {len(issues)} issues para épica {epic_key}")
                return issues

        except Exception as e:
            logger.warning(f"Método issueFunction falló: {e}")

        # MÉTODO 4: JQL "Epic Link" con custom field IDs (algunas instancias antiguas)
        try:
            logger.debug(f"Método 4: JQL cf[10014] = {epic_key}")

            jql = f'"cf[10014]" = {epic_key} OR "cf[10008]" = {epic_key}'
            issues = self.search_issues(jql)

            if issues:
                logger.info(f"Método cf[]: Obtenidos {len(issues)} issues para épica {epic_key}")
                return issues

        except Exception as e:
            logger.warning(f"Método cf[] falló: {e}")

        # MÉTODO 5: Filtrado manual sobre todos los issues del proyecto
        try:
            logger.debug(f"Método 5: Filtrado manual por parent en todos los issues del proyecto")

            project_key = epic_key.split('-')[0]
            jql = f'project = {project_key} AND type != Epic ORDER BY created DESC'

            all_issues = self.search_issues(jql)

            filtered_issues = []
            for issue in all_issues:
                fields = issue.get('fields', {})

                parent = fields.get('parent', {})
                if parent and parent.get('key') == epic_key:
                    filtered_issues.append(issue)
                    continue

                for field_key, field_value in fields.items():
                    if field_key.startswith('customfield_'):
                        if isinstance(field_value, str) and field_value == epic_key:
                            filtered_issues.append(issue)
                            break
                        elif isinstance(field_value, dict) and field_value.get('key') == epic_key:
                            filtered_issues.append(issue)
                            break

            if filtered_issues:
                logger.info(f"Método filtrado manual: Obtenidos {len(filtered_issues)} issues para épica {epic_key}")
                return filtered_issues

        except Exception as e:
            logger.warning(f"Método filtrado manual falló: {e}")

        # MÉTODO 6: API Agile (puede fallar en algunas configuraciones)
        try:
            logger.debug(f"Método 6: API Agile")
            epic = self.get_issue_by_key(epic_key)
            epic_id = epic['id']

            agile_url = f"{self.base_url}/rest/agile/1.0/epic/{epic_id}/issue"
            issues = []
            start_at = 0
            max_results = 50

            while True:
                params = {'startAt': start_at, 'maxResults': max_results}
                response = self.session.get(agile_url, params=params)
                response.raise_for_status()
                data = response.json()

                page_issues = data.get('issues', [])
                issues.extend(page_issues)

                total = data.get('total', 0)
                if start_at + max_results >= total:
                    break
                start_at += max_results

            if issues:
                logger.info(f"API Agile: Obtenidos {len(issues)} issues para épica {epic_key}")
                return issues

        except Exception as e:
            logger.warning(f"API Agile falló: {e}")

        logger.warning(f"No se encontraron issues vinculados a la épica {epic_key}")
        return []

    def get_subtasks_for_issues(self, issues: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Descarga las subtareas para una lista de issues.

        Itera sobre cada issue y, si tiene subtareas referenciadas en el campo
        'subtasks', descarga el detalle completo de cada una.

        Optimización: si el issue ya viene con el campo 'subtasks' poblado
        (porque fue obtenido vía search_issues con ese campo), reutiliza la
        lista de referencias para evitar una llamada extra a /issue/{key}.

        Args:
            issues: Lista de issues de Jira (típicamente historias/tareas)

        Returns:
            Diccionario {parent_key: [subtareas]} con las subtareas detalladas
            por cada issue padre. Si un issue no tiene subtareas, no aparece
            en el diccionario.
        """
        result: Dict[str, List[Dict]] = {}

        for issue in issues:
            parent_key = issue.get('key')
            if not parent_key:
                continue

            fields = issue.get('fields', {}) or {}
            subtask_refs = fields.get('subtasks')

            if subtask_refs is None:
                detailed = self.get_subtasks_for_issue(parent_key)
                if detailed:
                    result[parent_key] = detailed
                continue

            if not subtask_refs:
                continue

            detailed_subtasks: List[Dict] = []
            for ref in subtask_refs:
                subtask_key = ref.get('key')
                if not subtask_key:
                    continue
                try:
                    full = self.get_issue_by_key(subtask_key)
                    detailed_subtasks.append(full)
                    logger.debug(f"Descargada subtarea {subtask_key} de {parent_key}")
                except Exception as e:
                    logger.warning(f"No se pudo descargar subtarea {subtask_key} de {parent_key}: {e}")

            if detailed_subtasks:
                result[parent_key] = detailed_subtasks
                logger.info(f"{parent_key}: {len(detailed_subtasks)} subtareas descargadas")

        total_subtasks = sum(len(v) for v in result.values())
        logger.info(f"Total subtareas descargadas: {total_subtasks} (de {len(result)} issues con subtareas)")
        return result
    
    def get_all_issues(self, project_key: str, issue_types: Optional[List[str]] = None) -> List[Dict]:
        """
        Obtiene todos los issues de un proyecto
        
        Args:
            project_key: Clave del proyecto
            issue_types: Lista de tipos de issues (Story, Bug, Task, etc.) o None para todos
            
        Returns:
            Lista de issues
        """
        # Simplificado para compatibilidad
        jql = f'project = "{project_key}" ORDER BY created DESC'
        
        return self.search_issues(jql)
    
    def search_issues(self, jql: str, max_results: int = 1000, use_v3: bool = True) -> List[Dict]:
        """
        Busca issues usando JQL (Jira Query Language).
        Intenta primero con GET /search (v3 → v2) y, si ambos devuelven 410,
        usa el nuevo endpoint POST /search/jql que devuelve solo IDs y luego
        descarga cada issue individualmente.
        
        Args:
            jql: Query JQL
            max_results: Número máximo de resultados
            use_v3: Usar API v3 (más moderno, default True)
            
        Returns:
            Lista de issues
        """
        # Intentar primero con API v3
        api_base = self.api_base_v3 if use_v3 else self.api_base
        url = f"{api_base}/search"
        issues = []
        start_at = 0
        page_size = 100
        
        while len(issues) < max_results:
            params = {
                'jql': jql,
                'startAt': start_at,
                'maxResults': page_size
            }
            
            logger.debug(f"Buscando issues con API {'v3' if use_v3 else 'v2'}: {jql}, start={start_at}")
            
            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                page_issues = data.get('issues', [])
                issues.extend(page_issues)
                
                total = data.get('total', 0)
                
                if start_at + page_size >= total:
                    break
                    
                start_at += page_size
                
            except requests.exceptions.HTTPError as e:
                if use_v3 and e.response.status_code in [400, 410]:
                    logger.warning(f"API v3 falló, reintentando con v2...")
                    return self.search_issues(jql, max_results, use_v3=False)
                elif not use_v3 and e.response.status_code == 410:
                    # Ambas versiones devolvieron 410 → usar nuevo endpoint POST
                    logger.warning(f"API v2 también devolvió 410, usando endpoint POST /search/jql...")
                    return self._search_issues_post(jql, max_results)
                else:
                    raise
        
        logger.info(f"Obtenidos {len(issues)} issues para JQL: {jql}")
        return issues

    def _search_issues_post(self, jql: str, max_results: int = 1000) -> List[Dict]:
        """
        Búsqueda usando el nuevo endpoint POST /rest/api/3/search/jql
        (reemplaza el GET /search deprecado en instancias modernas).
        Devuelve solo IDs, por lo que descarga cada issue individualmente.
        
        Args:
            jql: Query JQL
            max_results: Número máximo de resultados
            
        Returns:
            Lista de issues con todos sus campos
        """
        url = f"{self.api_base_v3}/search/jql"
        all_issue_refs = []
        next_page_token = None

        while len(all_issue_refs) < max_results:
            payload: dict = {
                'jql': jql,
                'maxResults': min(100, max_results - len(all_issue_refs)),
                'fields': [
                    'summary', 'status', 'priority', 'assignee', 'description',
                    'components', 'customfield_10016', 'issuelinks', 'parent',
                    'issuetype', 'labels', 'fixVersions', 'subtasks'
                ],
            }
            if next_page_token:
                payload['nextPageToken'] = next_page_token

            logger.debug(f"POST /search/jql: {jql}, nextPageToken={next_page_token}")
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            page_issues = data.get('issues', [])
            all_issue_refs.extend(page_issues)

            # Si tiene campos completos (no solo id), devolver directamente
            if page_issues and page_issues[0].get('fields'):
                is_last = data.get('isLast', True)
                if is_last or not data.get('nextPageToken'):
                    break
                next_page_token = data.get('nextPageToken')
                continue

            # Solo IDs — descargar cada uno individualmente
            is_last = data.get('isLast', True)
            if is_last or not data.get('nextPageToken'):
                break
            next_page_token = data.get('nextPageToken')

        # Si los issues solo tienen 'id', descargar detalles individualmente
        if all_issue_refs and not all_issue_refs[0].get('fields'):
            logger.info(f"Descargando detalles de {len(all_issue_refs)} issues individualmente...")
            detailed = []
            for ref in all_issue_refs:
                issue_id = ref.get('id') or ref.get('key')
                if issue_id:
                    try:
                        issue = self.get_issue_by_key(issue_id)
                        detailed.append(issue)
                    except Exception as e:
                        logger.warning(f"No se pudo descargar issue {issue_id}: {e}")
            logger.info(f"Obtenidos {len(detailed)} issues via POST /search/jql")
            return detailed

        logger.info(f"Obtenidos {len(all_issue_refs)} issues via POST /search/jql")
        return all_issue_refs
    
    def get_issue_by_key(self, issue_key: str) -> Dict:
        """
        Obtiene un issue específico por su key
        
        Args:
            issue_key: Key del issue (ej: PROJ-123)
            
        Returns:
            Datos del issue
        """
        url = f"{self.api_base}/issue/{issue_key}"
        params = {
            'fields': '*all'
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_issue_comments(self, issue_key: str) -> List[Dict]:
        """
        Obtiene los comentarios de un issue
        
        Args:
            issue_key: Key del issue
            
        Returns:
            Lista de comentarios
        """
        url = f"{self.api_base}/issue/{issue_key}/comment"
        
        response = self.session.get(url)
        response.raise_for_status()
        data = response.json()
        
        return data.get('comments', [])
    
    def get_issue_attachments(self, issue_key: str) -> List[Dict]:
        """
        Obtiene los adjuntos de un issue
        
        Args:
            issue_key: Key del issue
            
        Returns:
            Lista de adjuntos
        """
        issue = self.get_issue_by_key(issue_key)
        return issue.get('fields', {}).get('attachment', [])
    
    def download_attachment(self, attachment_url: str) -> bytes:
        """
        Descarga un adjunto
        
        Args:
            attachment_url: URL del adjunto
            
        Returns:
            Contenido del archivo en bytes
        """
        response = self.session.get(attachment_url)
        response.raise_for_status()
        return response.content

