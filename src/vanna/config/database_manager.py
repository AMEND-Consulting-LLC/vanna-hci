from typing import Optional, Callable
import json
import pandas as pd
from .database_config import DatabaseConfig
from ..exceptions import ImproperlyConfigured

class DatabaseManager:
    def __init__(self, config: DatabaseConfig):
        """
        Initialize the database manager with the provided configuration.
        
        Args:
            config: DatabaseConfig object containing the database configuration
        """
        self.config = config
        self.run_sql_func: Optional[Callable] = None
        self.dialect: str = ""
        self._setup_connection()
    
    def _setup_connection(self):
        """Set up the database connection based on the configuration."""
        if self.config.db_type == 'bigquery':
            self._setup_bigquery()
        elif self.config.db_type == 'sqlserver':
            self._setup_sqlserver()
        else:
            raise ImproperlyConfigured(f"Unsupported database type: {self.config.db_type}")
    
    def _setup_bigquery(self):
        """Set up BigQuery connection."""
        try:
            from google.cloud import bigquery
            from google.oauth2 import service_account
        except ImportError:
            raise ImproperlyConfigured(
                "You need to install required dependencies to use BigQuery, run command:"
                " \npip install google-cloud-bigquery"
            )
        
        if not self.config.bigquery_config:
            raise ImproperlyConfigured("BigQuery configuration is required")
        
        project_id = self.config.bigquery_config.project_id
        cred_file_path = self.config.bigquery_config.cred_file_path
        
        try:
            if cred_file_path:
                with open(cred_file_path, "r") as f:
                    credentials = service_account.Credentials.from_service_account_info(
                        json.loads(f.read()),
                        scopes=["https://www.googleapis.com/auth/cloud-platform"],
                    )
                conn = bigquery.Client(
                    project=project_id,
                    credentials=credentials,
                )
            else:
                conn = bigquery.Client(project=project_id)
            
            def run_sql_bigquery(sql: str) -> pd.DataFrame:
                job = conn.query(sql)
                return job.result().to_dataframe()
            
            self.run_sql_func = run_sql_bigquery
            self.dialect = "BigQuery SQL"
            
        except Exception as e:
            raise ImproperlyConfigured(f"Failed to connect to BigQuery: {str(e)}")
    
    def _setup_sqlserver(self):
        """Set up SQL Server connection."""
        try:
            import pyodbc
            import sqlalchemy as sa
            from sqlalchemy.engine import URL
        except ImportError:
            raise ImproperlyConfigured(
                "You need to install required dependencies to use SQL Server, run commands:"
                "\npip install pyodbc sqlalchemy"
            )
        
        if not self.config.sqlserver_config:
            raise ImproperlyConfigured("SQL Server configuration is required")
        
        try:
            connection_url = URL.create(
                "mssql+pyodbc",
                query={"odbc_connect": self.config.sqlserver_config.odbc_conn_str}
            )
            
            from sqlalchemy import create_engine
            engine = create_engine(connection_url)
            
            def run_sql_mssql(sql: str) -> pd.DataFrame:
                with engine.begin() as conn:
                    df = pd.read_sql_query(sa.text(sql), conn)
                    return df
            
            self.run_sql_func = run_sql_mssql
            self.dialect = "T-SQL / Microsoft SQL Server"
            
        except Exception as e:
            raise ImproperlyConfigured(f"Failed to connect to SQL Server: {str(e)}")
    
    def run_sql(self, sql: str) -> pd.DataFrame:
        """
        Execute a SQL query on the connected database.
        
        Args:
            sql: The SQL query to execute
            
        Returns:
            pandas DataFrame containing the query results
            
        Raises:
            ImproperlyConfigured if no database connection is established
        """
        if not self.run_sql_func:
            raise ImproperlyConfigured("No database connection established")
        
        return self.run_sql_func(sql)
    
    @property
    def is_connected(self) -> bool:
        """Check if a database connection is established."""
        return self.run_sql_func is not None 