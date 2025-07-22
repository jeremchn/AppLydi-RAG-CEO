import faiss
import numpy as np

# Stocke embeddings localement dans un index FAISS
dimension = 1536  # taille embeddings OpenAI

index = faiss.IndexFlatL2(dimension)
texts = []  # Liste parallèle des docs

def add_to_index(embedding, text):
    index.add(np.array([embedding]).astype("float32"))
    texts.append(text)

def search_similar_texts(query_embedding, top_k=3):
    D, I = index.search(np.array([query_embedding]).astype("float32"), top_k)
    return [texts[i] for i in I[0] if i != -1]
