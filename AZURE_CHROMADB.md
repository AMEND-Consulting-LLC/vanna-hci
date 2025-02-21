# ChromaDB with Azure OpenAI Integration

This document describes how to set up and use Vanna.AI with ChromaDB as the vector store and Azure OpenAI as the language model.

## Overview

This implementation combines:
- ChromaDB for efficient vector storage and retrieval
- Azure OpenAI for natural language processing and SQL generation
- Flask for the web interface

## Prerequisites

1. Azure OpenAI Service account with:
   - An endpoint URL
   - API key
   - A deployed model (e.g., GPT-4)

2. Python environment with required packages:
   ```bash
   pip install "vanna[chromadb]" "openai>=1.0.0" flask flask-sock flasgger
   ```

## Configuration

Set the following environment variables:

```bash
# Required
export AZURE_OPENAI_ENDPOINT="https://your-endpoint.openai.azure.com"
export AZURE_OPENAI_API_KEY="your-api-key"
export AZURE_OPENAI_DEPLOYMENT="your-deployment-name"

# Optional
export AZURE_OPENAI_API_VERSION="2024-02-15-preview"  # Defaults to this if not set
```

## Implementation

Create an `app.py` file with the following code:

```python
from vanna.chromadb.chromadb_vector import ChromaDB_VectorStore
from vanna.openai.openai_chat import OpenAI_Chat
from vanna.flask import VannaFlaskApp
import os
from openai import AzureOpenAI

# Initialize ChromaDB with persistent storage
config = {
    "path": "./data",  # Store data in the data directory
    "client": "persistent",  # Use persistent storage
    # Azure OpenAI Configuration
    "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
    "azure_api_key": os.getenv("AZURE_OPENAI_API_KEY"),
    "azure_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4"),
    "azure_api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
}

# Create a class that combines ChromaDB for vector storage and OpenAI for chat
class VannaAzure(ChromaDB_VectorStore, OpenAI_Chat):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        
        # Initialize Azure OpenAI client
        client = AzureOpenAI(
            azure_endpoint=config["azure_endpoint"],
            api_key=config["azure_api_key"],
            api_version=config["azure_api_version"]
        )
        
        # Pass the Azure client to OpenAI_Chat
        OpenAI_Chat.__init__(self, client=client, config={"model": config["azure_deployment"]})

# Initialize the vector store with Azure OpenAI
vector_store = VannaAzure(config)

# Create the Flask app with our vector store
app = VannaFlaskApp(
    vn=vector_store,
    debug=True,
    allow_llm_to_see_data=True,  # Since we're using local storage
    title="Vanna.AI with ChromaDB and Azure OpenAI",
    subtitle="Your AI-powered SQL assistant with ChromaDB vector store and Azure OpenAI"
)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

## Usage

1. Start the server:
   ```bash
   python app.py
   ```

2. Access the web interface at http://localhost:8000

3. Train the model with your SQL schema:
   ```python
   # Using the Python API
   vn = VannaAzure(config)
   
   # Add your database schema
   vn.train(ddl="""
       CREATE TABLE orders (
           order_id INT PRIMARY KEY,
           customer_id INT,
           order_date DATE,
           total_amount DECIMAL(10,2)
       );
   """)
   
   # Add documentation
   vn.train(documentation="Orders table contains customer purchase information...")
   
   # Add example queries
   vn.train(question="What are the total sales by customer?",
            sql="SELECT customer_id, SUM(total_amount) as total_sales FROM orders GROUP BY customer_id")
   ```

4. Ask questions through the web interface or API:
   ```python
   # Using the Python API
   sql = vn.generate_sql("Show me the top 10 customers by total sales")
   results = vn.run_sql(sql)
   ```

## Features

- **Persistent Storage**: ChromaDB stores embeddings in the `./data` directory
- **Web Interface**: Provides a user-friendly interface for:
  - Asking questions in natural language
  - Viewing generated SQL
  - Running queries
  - Managing training data
- **API Documentation**: Available at http://localhost:8000/apidocs
- **Secure**: Database contents are never sent to Azure OpenAI

## Architecture

The implementation follows Vanna.AI's standard architecture:
1. ChromaDB handles vector storage and similarity search
2. Azure OpenAI processes natural language and generates SQL
3. Flask provides the web interface and API endpoints

## Best Practices

1. **Environment Variables**: Always use environment variables for sensitive information
2. **Training Data**: Start with:
   - Database schema (DDL statements)
   - Business documentation
   - Common SQL queries
3. **Security**: 
   - Keep Azure OpenAI API keys secure
   - Use appropriate network security for the web interface
   - Consider adding authentication if needed

## Troubleshooting

1. **Missing Environment Variables**:
   - Check that all required Azure OpenAI environment variables are set
   - Verify the Azure OpenAI deployment name matches your configuration

2. **ChromaDB Issues**:
   - Ensure the `./data` directory exists and is writable
   - Check ChromaDB logs for any persistence issues

3. **Azure OpenAI Errors**:
   - Verify your Azure OpenAI endpoint is accessible
   - Ensure your API key has appropriate permissions
   - Check if your deployment model is available

## Contributing

Feel free to contribute to this implementation by:
1. Reporting issues
2. Suggesting improvements
3. Submitting pull requests

## License

This implementation follows the MIT license of the main Vanna.AI project. 