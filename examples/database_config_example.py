from vanna import VannaBase

# Example configuration for BigQuery
bigquery_config = {
    "database": {
        "db_type": "bigquery",
        "project_id": "your-project-id",
        "cred_file_path": "path/to/credentials.json"  # optional if using default credentials
    }
}

# Example configuration for SQL Server
sqlserver_config = {
    "database": {
        "db_type": "sqlserver",
        "odbc_conn_str": "Driver={ODBC Driver 17 for SQL Server};Server=your-server;Database=your-database;UID=your-username;PWD=your-password"
    }
}

def main():
    # Initialize Vanna with BigQuery
    print("Connecting to BigQuery...")
    vn_bigquery = VannaBase(config=bigquery_config)
    
    if vn_bigquery.run_sql_is_set:
        print(f"Successfully connected to {vn_bigquery.dialect}")
        # Example query
        try:
            result = vn_bigquery.run_sql("SELECT 1")
            print("BigQuery test query result:", result)
        except Exception as e:
            print("Error running BigQuery query:", str(e))
    
    # Initialize Vanna with SQL Server
    print("\nConnecting to SQL Server...")
    vn_sqlserver = VannaBase(config=sqlserver_config)
    
    if vn_sqlserver.run_sql_is_set:
        print(f"Successfully connected to {vn_sqlserver.dialect}")
        # Example query
        try:
            result = vn_sqlserver.run_sql("SELECT 1")
            print("SQL Server test query result:", result)
        except Exception as e:
            print("Error running SQL Server query:", str(e))

if __name__ == "__main__":
    main() 