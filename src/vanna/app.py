from vanna.chromadb.chromadb_vector import ChromaDB_VectorStore
from vanna.flask import VannaFlaskApp

# Initialize ChromaDB with persistent storage
config = {
    "path": "./data",  # Store data in the data directory
    "client": "persistent"  # Use persistent storage
}

# Create our ChromaDB vector store instance
class VannaChromaDB(ChromaDB_VectorStore):
    def assistant_message(self, message: str) -> None:
        print(f"Assistant: {message}")

    def system_message(self, message: str) -> None:
        print(f"System: {message}")

    def user_message(self, message: str) -> None:
        print(f"User: {message}")

    def submit_prompt(self, prompt: str) -> str:
        print(f"Prompt: {prompt}")
        return "Test response"

# Initialize the vector store
vector_store = VannaChromaDB(config)

# Create the Flask app with our vector store
app = VannaFlaskApp(
    vn=vector_store,
    debug=True,
    allow_llm_to_see_data=True,  # Since we're using local storage
    title="Vanna.AI with ChromaDB",
    subtitle="Your AI-powered SQL assistant with ChromaDB vector store"
)

if __name__ == "__main__":
    # Run the Flask app
    app.run(host="0.0.0.0", port=8000) 