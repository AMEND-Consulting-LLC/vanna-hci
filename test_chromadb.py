from vanna.chromadb.chromadb_vector import ChromaDB_VectorStore

class TestChromaDB(ChromaDB_VectorStore):
    def assistant_message(self, message: str) -> None:
        print(f"Assistant: {message}")

    def system_message(self, message: str) -> None:
        print(f"System: {message}")

    def user_message(self, message: str) -> None:
        print(f"User: {message}")

    def submit_prompt(self, prompt: str) -> str:
        print(f"Prompt: {prompt}")
        return "Test response"

def test_chromadb():
    # Initialize ChromaDB with persistent storage in the data directory
    config = {
        "path": "./data",  # Store data in the data directory
        "client": "persistent"  # Use persistent storage
    }
    
    vector_store = TestChromaDB(config)
    
    # Test adding documentation
    doc_id = vector_store.add_documentation(
        "This is a test documentation about customer orders. The orders table contains customer_id, order_date, and total_amount."
    )
    print(f"Added documentation with ID: {doc_id}")
    
    # Test adding DDL
    ddl_id = vector_store.add_ddl("""
    CREATE TABLE orders (
        order_id INT PRIMARY KEY,
        customer_id INT,
        order_date DATE,
        total_amount DECIMAL(10,2),
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    );
    """)
    print(f"Added DDL with ID: {ddl_id}")
    
    # Test adding question-SQL pair
    sql_id = vector_store.add_question_sql(
        question="What is the total amount of orders for each customer?",
        sql="SELECT customer_id, SUM(total_amount) as total_orders FROM orders GROUP BY customer_id;"
    )
    print(f"Added question-SQL pair with ID: {sql_id}")
    
    # Test similarity search
    print("\nTesting similarity search:")
    
    # Search for related DDL
    print("\nRelated DDL for query 'Show me the schema for customer orders':")
    related_ddl = vector_store.get_related_ddl("Show me the schema for customer orders")
    print(related_ddl)
    
    # Search for similar questions
    print("\nSimilar questions for query 'How much has each customer spent?':")
    similar_questions = vector_store.get_similar_question_sql("How much has each customer spent?")
    print(similar_questions)
    
    # Search for related documentation
    print("\nRelated documentation for query 'Tell me about the orders table':")
    related_docs = vector_store.get_related_documentation("Tell me about the orders table")
    print(related_docs)

if __name__ == "__main__":
    test_chromadb() 