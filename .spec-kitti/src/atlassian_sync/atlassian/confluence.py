"""
Cliente para interactuar con la API de Confluence
"""

import requests
from typing import List, Dict, Optional
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)


class ConfluenceClient:
    """Cliente para la API REST de Confluence"""
    
    def __init__(self, base_url: str, username: str, api_token: str):
        """
        Inicializa el cliente de Confluence
        
        Args:
            base_url: URL base de Confluence (ej: https://tu-dominio.atlassian.net)
            username: Email de usuario de Atlassian
            api_token: Token de API de Atlassian
        """
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/wiki/rest/api"
        self.session = requests.Session()
        self.session.auth = (username, api_token)
        logger.info(f"Cliente Confluence inicializado para {base_url}")
    
    def get_spaces(self, limit: int = 100) -> List[Dict]:
        """
        Obtiene la lista de espacios disponibles
        
        Args:
            limit: Número máximo de espacios a obtener
            
        Returns:
            Lista de espacios
        """
        url = f"{self.api_base}/space"
        params = {
            'limit': limit,
            'expand': 'description.plain,homepage'
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        logger.info(f"Obtenidos {len(data['results'])} espacios")
        return data['results']
    
    def get_page_by_title(self, space_key: str, title: str) -> Dict:
        """
        Busca una página por título exacto en un space usando CQL
        
        Args:
            space_key: Clave del espacio
            title: Título de la página
            
        Returns:
            Datos de la página o None si no se encuentra
        """
        # Intentar primero con búsqueda normal
        url = f"{self.api_base}/content"
        params = {
            'spaceKey': space_key,
            'title': title,
            'expand': 'body.storage,ancestors,version,space'
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        results = data.get('results', [])
        if results:
            logger.info(f"Página '{title}' encontrada en space {space_key}")
            return results[0]
        
        # Si no se encuentra, intentar con CQL (más potente, encuentra páginas intermedias)
        logger.info(f"Buscando '{title}' con CQL...")
        search_url = f"{self.api_base}/content/search"
        cql = f'space.key="{space_key}" AND title="{title}"'
        search_params = {
            'cql': cql,
            'expand': 'body.storage,ancestors,version,space'
        }
        
        response = self.session.get(search_url, params=search_params)
        response.raise_for_status()
        data = response.json()
        
        results = data.get('results', [])
        if results:
            logger.info(f"Página '{title}' encontrada con CQL en space {space_key}")
            return results[0]
        else:
            logger.warning(f"Página '{title}' no encontrada en space {space_key}")
            return None
    
    def get_space_pages(self, space_key: str, limit: int = 100) -> List[Dict]:
        """
        Obtiene todas las páginas de un espacio
        
        Args:
            space_key: Clave del espacio
            limit: Número de páginas por petición
            
        Returns:
            Lista de páginas
        """
        pages = []
        start = 0
        
        while True:
            url = f"{self.api_base}/content"
            params = {
                'spaceKey': space_key,
                'type': 'page',
                'limit': limit,
                'start': start,
                'expand': 'body.storage,ancestors,version,space'
            }
            
            logger.debug(f"Obteniendo páginas: start={start}, limit={limit}")
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            pages.extend(data['results'])
            
            if data['size'] < limit:
                break
                
            start += limit
        
        logger.info(f"Obtenidas {len(pages)} páginas del espacio {space_key}")
        return pages
    
    def get_page_by_id(self, page_id: str) -> Dict:
        """
        Obtiene una página específica por ID
        
        Args:
            page_id: ID de la página
            
        Returns:
            Datos de la página
        """
        url = f"{self.api_base}/content/{page_id}"
        params = {
            'expand': 'body.storage,ancestors,version,space'
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_page_children(self, page_id: str, limit: int = 100) -> List[Dict]:
        """
        Obtiene las páginas hijas de una página
        
        Args:
            page_id: ID de la página padre
            limit: Número de páginas por petición
            
        Returns:
            Lista de páginas hijas
        """
        url = f"{self.api_base}/content/{page_id}/child/page"
        params = {
            'expand': 'body.storage,ancestors,version,space',
            'limit': limit
        }
        
        children = []
        start = 0
        
        while True:
            params['start'] = start
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            children.extend(data['results'])
            
            if data['size'] < params['limit']:
                break
                
            start += params['limit']
        
        logger.debug(f"Obtenidas {len(children)} páginas hijas de {page_id}")
        return children
    
    def get_page_attachments(self, page_id: str) -> List[Dict]:
        """
        Obtiene los adjuntos de una página
        
        Args:
            page_id: ID de la página
            
        Returns:
            Lista de adjuntos
        """
        url = f"{self.api_base}/content/{page_id}/child/attachment"
        response = self.session.get(url)
        response.raise_for_status()
        data = response.json()
        
        logger.debug(f"Obtenidos {len(data['results'])} adjuntos de {page_id}")
        return data['results']
    
    def download_attachment(self, download_url: str) -> bytes:
        """
        Descarga un adjunto
        
        Args:
            download_url: URL de descarga del adjunto
            
        Returns:
            Contenido del archivo en bytes
        """
        full_url = urljoin(self.base_url, download_url)
        response = self.session.get(full_url)
        response.raise_for_status()
        return response.content


