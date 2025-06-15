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
import pdf2image
import pytesseract
from PIL import Image
import io
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document

def extract_text_with_ocr(pdf_path: str) -> list:
    """Extract text from PDF using OCR when needed."""
    try:
        # First try to convert PDF pages to images
        images = pdf2image.convert_from_path(pdf_path)
        text_content = []
        
        for i, image in enumerate(images):
            # Extract text from image using Tesseract OCR
            text = pytesseract.image_to_string(image, lang='eng')
            if text.strip():
                text_content.append({
                    'content': text,
                    'page': i + 1
                })
        
        return text_content
    except Exception as e:
        print(f"OCR processing error: {str(e)}")
        return []

def load_cv(file_path: str) -> list:
    """
    Load and split a PDF document into semantically meaningful chunks.
    Attempts regular PDF text extraction first, falls back to OCR if needed.
    
    Args:
        file_path (str): Path to the PDF file to process. Must be a valid PDF file.
        
    Returns:
        list: A list of document chunks with text content and metadata.
        
    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        ValueError: If no text could be extracted by any method
    """
    
    def ensure_metadata(doc, source_filename):
        """Ensure document has all required metadata fields."""
        if not hasattr(doc, 'metadata'):
            doc.metadata = {}
        doc.metadata['filename'] = source_filename
        doc.metadata['source'] = 'pdf'
        doc.metadata['page'] = doc.metadata.get('page', 1)
        doc.metadata['extraction_method'] = doc.metadata.get('extraction_method', 'regular')
        return doc
    print(f"\n=== Processing PDF: {file_path} ===")
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        raise FileNotFoundError(f"PDF file not found at {file_path}")
    
    # Try regular PDF text extraction first
    loader = PyPDFLoader(file_path)
    documents = []
    try:
        print("Attempting regular PDF text extraction...")
        documents = loader.load_and_split()
        print(f"Regular extraction found {len(documents)} document chunks")
    except Exception as e:
        print(f"Regular PDF extraction failed: {str(e)}")
    
    # Check if we got valid text content
    valid_documents = []
    filename = os.path.basename(file_path)
    
    print("\nValidating extracted content...")
    for i, doc in enumerate(documents):
        if doc.page_content.strip():
            doc = ensure_metadata(doc, filename)
            valid_documents.append(doc)
            print(f"Valid chunk {i+1}: {len(doc.page_content)} chars from page {doc.metadata.get('page', 'unknown')}")
        else:
            print(f"Skipping empty chunk {i+1}")
    
    # If no valid text found, try OCR
    if not valid_documents:
        print("\nNo valid text found with regular extraction, attempting OCR...")
        try:
            ocr_results = extract_text_with_ocr(file_path)
            print(f"OCR extracted {len(ocr_results)} pages of text")
            
            if ocr_results:
                # Create documents from OCR results
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200
                )
                
                for i, result in enumerate(ocr_results):
                    print(f"\nProcessing OCR result {i+1}...")
                    chunks = text_splitter.split_text(result['content'])
                    print(f"Split into {len(chunks)} chunks")
                    
                    for j, chunk in enumerate(chunks):
                        if chunk.strip():
                            doc = Document(
                                page_content=chunk,
                                metadata={
                                    'filename': filename,
                                    'page': result['page'],
                                    'extraction_method': 'ocr',
                                    'chunk': j+1,
                                    'source': 'pdf'
                                }
                            )
                            doc = ensure_metadata(doc, filename)
                            valid_documents.append(doc)
                            print(f"Added valid OCR chunk {j+1}: {len(chunk)} chars")
                        else:
                            print(f"Skipping empty OCR chunk {j+1}")
            else:
                print("OCR extraction returned no results")
        except Exception as e:
            print(f"OCR processing failed: {str(e)}")
    
    if not valid_documents:
        print("\nError: No valid text content could be extracted from PDF")
        raise ValueError(f"Could not extract any valid text content from {file_path}")
    
    print(f"\nSuccessfully processed PDF. Total valid chunks: {len(valid_documents)}")
    return valid_documents

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

def get_processed_pdfs_stats(uploads_dir: str = "uploads") -> dict:
    """
    Get statistics about processed PDF files.
    
    Args:
        uploads_dir (str): Directory containing uploaded PDFs
        
    Returns:
        dict: Statistics about the processed PDFs including:
            - total_count: Total number of PDFs
            - files: List of PDF files with their sizes
    """
    stats = {
        'total_count': 0,
        'files': []
    }
    
    if not os.path.exists(uploads_dir):
        return stats
        
    for file in os.listdir(uploads_dir):
        if file.lower().endswith('.pdf'):
            file_path = os.path.join(uploads_dir, file)
            file_size = os.path.getsize(file_path)
            stats['files'].append({
                'name': file,
                'size': file_size,
                'size_formatted': f"{file_size / 1024:.1f} KB"
            })
            stats['total_count'] += 1
            
    # Sort files by name
    stats['files'].sort(key=lambda x: x['name'])
    return stats
