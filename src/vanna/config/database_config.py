from typing import Dict, Optional, Union
from dataclasses import dataclass
from ..exceptions import ImproperlyConfigured

@dataclass
class BigQueryConfig:
    project_id: str
    cred_file_path: Optional[str] = None

@dataclass
class SQLServerConfig:
    odbc_conn_str: str

@dataclass
class DatabaseConfig:
    db_type: str  # 'bigquery' or 'sqlserver'
    bigquery_config: Optional[BigQueryConfig] = None
    sqlserver_config: Optional[SQLServerConfig] = None

    def __post_init__(self):
        if self.db_type not in ['bigquery', 'sqlserver']:
            raise ImproperlyConfigured("db_type must be either 'bigquery' or 'sqlserver'")
        
        if self.db_type == 'bigquery' and not self.bigquery_config:
            raise ImproperlyConfigured("BigQuery configuration is required when db_type is 'bigquery'")
        
        if self.db_type == 'sqlserver' and not self.sqlserver_config:
            raise ImproperlyConfigured("SQL Server configuration is required when db_type is 'sqlserver'")

def create_database_config(config: Dict[str, Union[str, Dict]]) -> DatabaseConfig:
    """
    Create a DatabaseConfig object from a dictionary configuration.
    
    Args:
        config: A dictionary containing database configuration.
            For BigQuery:
            {
                'db_type': 'bigquery',
                'project_id': 'your-project-id',
                'cred_file_path': 'path/to/credentials.json'  # optional
            }
            
            For SQL Server:
            {
                'db_type': 'sqlserver',
                'odbc_conn_str': 'your-connection-string'
            }
    
    Returns:
        DatabaseConfig object
    """
    db_type = config.get('db_type')
    if not db_type:
        raise ImproperlyConfigured("db_type is required in configuration")

    if db_type == 'bigquery':
        project_id = config.get('project_id')
        if not project_id:
            raise ImproperlyConfigured("project_id is required for BigQuery configuration")
        
        return DatabaseConfig(
            db_type='bigquery',
            bigquery_config=BigQueryConfig(
                project_id=project_id,
                cred_file_path=config.get('cred_file_path')
            )
        )
    
    elif db_type == 'sqlserver':
        odbc_conn_str = config.get('odbc_conn_str')
        if not odbc_conn_str:
            raise ImproperlyConfigured("odbc_conn_str is required for SQL Server configuration")
        
        return DatabaseConfig(
            db_type='sqlserver',
            sqlserver_config=SQLServerConfig(
                odbc_conn_str=odbc_conn_str
            )
        )
    
    else:
        raise ImproperlyConfigured(f"Unsupported database type: {db_type}") 