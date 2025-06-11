"""
Document Processing Module

This module provides functionalities for PDF document processing, embedding generation,
and vector database operations using LangChain's ecosystem. It uses the BAAI/bge-large-en-v1.5 
model for generating high-quality text embeddings and ChromaDB for efficient vector storage.

Key components:
- PDF Processing: Uses PyPDFLoader for document loading and splitting
- Embeddings: Leverages HuggingFace embeddings with the BGE model
- Vector Storage: Implements ChromaDB for persistent vector storage and retrieval
"""

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
import os

def load_cv(file_path: str) -> list:
    """
    Load and split a PDF document into semantically meaningful chunks.
    
    Args:
        file_path (str): Path to the PDF file to process. Must be a valid PDF file.
        
    Returns:
        list: A list of document chunks, where each chunk contains:
            - page_content: The text content of the chunk
            - metadata: Associated metadata including page numbers and filename
            
    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        ValueError: If the file is not a valid PDF
    """
    loader = PyPDFLoader(file_path)
    documents = loader.load_and_split()
    
    # Add filename to metadata
    filename = os.path.basename(file_path)
    for doc in documents:
        doc.metadata['filename'] = filename
        
    return documents

# Initialize the embedding model using BAAI's BGE model
# BGE (BAAI General Embedding) model is specifically optimized for 
# semantic similarity tasks and information retrieval
model_name = "BAAI/bge-large-en-v1.5"
embedding_model = HuggingFaceEmbeddings(model_name=model_name)

def create_db(documents: list, db_path: str = "chroma_db") -> Chroma:
    """
    Create a new Chroma vector database from documents and persist it to disk.
    
    This function processes the input documents, generates embeddings using the BGE model,
    and stores them in a ChromaDB database. The database is persisted to disk for later use.
    
    Args:
        documents (list): List of document chunks to store in the database.
                         Each document should have page_content and metadata.
        db_path (str): Directory path where the database will be persisted.
                      Defaults to "chroma_db".
        
    Returns:
        Chroma: A Chroma vector store instance containing the document embeddings.
                This can be used for similarity search and retrieval.
                
    Raises:
        OSError: If unable to create the database directory
        ValueError: If documents are not in the correct format
    """
    if not os.path.exists(db_path):
        os.makedirs(db_path)
    db = Chroma.from_documents(
        documents,
        embedding_model,
        persist_directory=db_path
    )
    return db

def load_db(db_path: str = "chroma_db") -> Chroma:
    """
    Load an existing Chroma vector database from disk.
    
    This function connects to a previously created ChromaDB database and initializes
    it with the same embedding model used for creation, ensuring consistency in
    vector representations.
    
    Args:
        db_path (str): Directory path where the database is stored.
                      Defaults to "chroma_db".
        
    Returns:
        Chroma: A Chroma vector store instance connected to the existing database.
                Ready for similarity search and retrieval operations.
                
    Raises:
        FileNotFoundError: If the database directory doesn't exist
        RuntimeError: If the database is corrupted or incompatible
    """
    return Chroma(
        persist_directory=db_path,
        embedding_function=embedding_model
    )
