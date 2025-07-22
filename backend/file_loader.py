import pdfplumber
from typing import List

def load_text_from_pdf(path: str) -> str:
    """Load text from PDF file"""
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error loading PDF: {e}")
    return text

def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # If not the last chunk, try to end at a sentence boundary
        if end < len(text):
            # Look for sentence endings
            sentence_ends = ['.', '!', '?', '\n']
            for i in range(len(chunk) - 1, max(0, len(chunk) - 100), -1):
                if chunk[i] in sentence_ends:
                    chunk = chunk[:i + 1]
                    break
        
        chunks.append(chunk.strip())
        start = max(start + chunk_size - overlap, start + 1)
        
        if start >= len(text):
            break
    
    return [chunk for chunk in chunks if chunk]
