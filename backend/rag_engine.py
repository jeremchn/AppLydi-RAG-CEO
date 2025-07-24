# Contient la logique RAG améliorée
import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from openai_client import get_embedding, get_chat_response, get_embedding_fast
from database import Document, DocumentChunk, User
from file_loader import load_text_from_pdf, chunk_text
from file_generator import FileGenerator

logger = logging.getLogger(__name__)

# Cache simple pour les réponses récentes
_answer_cache = {}

def get_answer_with_files(question: str, user_id: int, db: Session, selected_doc_ids: List[int] = None, agent_type: str = None) -> Dict[str, Any]:
    """Get answer using RAG with file generation capabilities"""
    try:
        # Créer une clé de cache
        cache_key = f"{user_id}_{hash(question)}_{hash(str(selected_doc_ids))}_{agent_type}"
        
        # Vérifier le cache (garde en cache pendant 5 minutes)
        if cache_key in _answer_cache:
            cached_time, cached_result = _answer_cache[cache_key]
            if datetime.now().timestamp() - cached_time < 300:  # 5 minutes
                logger.info("Returning cached answer")
                return cached_result
        
        # Get the regular answer first
        answer = get_answer(question, user_id, db, selected_doc_ids, agent_type)
        
        # Initialize file generator
        file_gen = FileGenerator()
        
        # Detect if user wants file generation
        generation_info = file_gen.detect_generation_request(question, answer)
        
        # If no table detected but user asked for structured data, create sample data
        if (generation_info['generate_csv'] or generation_info['generate_pdf']) and not generation_info['table_data']:
            sample_data = file_gen.create_sample_data(agent_type or 'sales')
            generation_info['table_data'] = sample_data
            generation_info['has_table'] = True
            
        # Format answer with table if needed
        if generation_info['has_table'] and generation_info['table_data']:
            generation_info['formatted_answer'] = file_gen._format_answer_with_table(answer, generation_info['table_data'])
        else:
            generation_info['formatted_answer'] = answer
            
        result = {
            'answer': generation_info['formatted_answer'],
            'generation_info': generation_info
        }
        
        # Mettre en cache le résultat
        _answer_cache[cache_key] = (datetime.now().timestamp(), result)
        
        # Nettoyer le cache (garder seulement les 10 dernières entrées)
        if len(_answer_cache) > 10:
            oldest_key = min(_answer_cache.keys(), key=lambda k: _answer_cache[k][0])
            del _answer_cache[oldest_key]
            
        return result
        
    except Exception as e:
        logger.error(f"Error getting answer with files: {e}")
        raise Exception(f"Erreur lors du traitement de votre question : {str(e)}")

def get_agent_system_prompt(agent_type: str = None) -> str:
    """Get system prompt based on agent type"""
    agent_prompts = {
        'sales': """Vous êtes un assistant IA spécialisé en VENTES. Votre rôle est d'analyser les documents du point de vue commercial et d'aider avec les stratégies de vente, la prospection, et la conversion client.""",
        'marketing': """Vous êtes un assistant IA spécialisé en MARKETING. Votre rôle est d'analyser les documents du point de vue marketing et d'aider avec les campagnes, la communication, et la stratégie de marque.""",
        'hr': """Vous êtes un assistant IA spécialisé en RESSOURCES HUMAINES. Votre rôle est d'analyser les documents du point de vue RH et d'aider avec le recrutement, la gestion des talents, et les politiques d'entreprise.""",
        'purchase': """Vous êtes un assistant IA spécialisé en ACHATS. Votre rôle est d'analyser les documents du point de vue achats et d'aider avec la négociation fournisseurs, l'approvisionnement, et l'optimisation des coûts."""
    }
    
    if agent_type and agent_type in agent_prompts:
        return agent_prompts[agent_type]
    else:
        return "Vous êtes un assistant IA professionnel."

def get_direct_gpt_response(question: str, agent_type: str = None) -> str:
    """Get direct response from GPT without RAG when no documents are available"""
    try:
        # Get agent-specific system prompt
        agent_prompt = get_agent_system_prompt(agent_type)
        
        # Create prompt for direct GPT call
        prompt = f"""{agent_prompt}

L'utilisateur n'a pas encore uploadé de documents. Répondez à sa question en utilisant vos connaissances générales, tout en gardant votre spécialisation à l'esprit.

Question: {question}

Réponse:"""
        
        # Get AI response
        logger.info("Getting direct response from OpenAI (no documents)")
        response = get_chat_response(prompt)
        logger.info("Successfully got direct response from OpenAI")
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting direct GPT response: {e}")
        raise Exception(f"Erreur lors du traitement de votre question : {str(e)}")

def get_answer(question: str, user_id: int, db: Session, selected_doc_ids: List[int] = None, agent_type: str = None) -> str:
    """Get answer using RAG for specific user with OpenAI - always using embeddings"""
    try:
        # Get user's documents (filter by selected documents if provided)
        if selected_doc_ids:
            user_docs = db.query(Document).filter(
                Document.user_id == user_id,
                Document.id.in_(selected_doc_ids)
            ).all()
            logger.info(f"Using {len(user_docs)} selected documents: {selected_doc_ids}")
        else:
            user_docs = db.query(Document).filter(Document.user_id == user_id).all()
            logger.info(f"Using all {len(user_docs)} user documents")
            
        if not user_docs:
            if selected_doc_ids:
                return "Aucun des documents sélectionnés n'a été trouvé. Veuillez vérifier votre sélection."
            else:
                # No documents available - use direct GPT call
                logger.info("No documents found, using direct GPT call")
                return get_direct_gpt_response(question, agent_type)
        
        # Always get question embedding with retry
        logger.info(f"Getting embedding for question: {question}")
        query_embedding = get_embedding(question)
        logger.info("Successfully got query embedding")
        
        # Search similar chunks for this user (with optional document filtering)
        logger.info(f"Searching similar texts for user {user_id}")
        context_results = search_similar_texts_for_user(query_embedding, user_id, db, top_k=8, selected_doc_ids=selected_doc_ids)
        
        if not context_results:
            return "Je n'ai pas trouvé d'informations pertinentes dans vos documents pour répondre à cette question."
        
        # Get complete document information
        documents_info = get_documents_summary(user_id, db, selected_doc_ids)
        
        # Prepare context with document attribution
        context_by_document = {}
        for result in context_results:
            doc_name = result['document_name']
            if doc_name not in context_by_document:
                context_by_document[doc_name] = []
            context_by_document[doc_name].append(result['text'])
        
        # Build enhanced context string
        enhanced_context = ""
        for doc_name, contexts in context_by_document.items():
            enhanced_context += f"\n--- Extraits du document '{doc_name}' ---\n"
            for i, context in enumerate(contexts, 1):
                enhanced_context += f"Extrait {i}: {context}\n"
        
        # Check if user is asking for a summary of multiple documents
        is_summary_request = any(word in question.lower() for word in ['résumé', 'résume', 'synthèse', 'présente', 'parle de quoi', 'contenu'])
        is_multiple_docs = len(documents_info) > 1
        
        if is_summary_request and is_multiple_docs:
            # Special handling for document summaries
            documents_content = ""
            for i, doc in enumerate(documents_info, 1):
                documents_content += f"\n=== Document {i}: {doc['filename']} ===\n"
                documents_content += f"Contenu: {doc['content']}\n"
            
            prompt = f"""Vous êtes un assistant IA spécialisé dans l'analyse de documents. L'utilisateur vous demande de faire un résumé de {len(documents_info)} documents.

DOCUMENTS À ANALYSER:
{documents_content}

CONSIGNES:
- Créez {len(documents_info)} paragraphes distincts, un pour chaque document
- Commencez chaque paragraphe par "Document [X] - [nom du fichier]:"
- Faites un résumé concis mais informatif de chaque document
- Gardez l'ordre des documents tel que présenté
- Utilisez un style professionnel et structuré

Question de l'utilisateur: {question}

Réponse:"""
        else:
            # Get agent-specific system prompt
            agent_prompt = get_agent_system_prompt(agent_type)
            
            # Standard RAG response with document attribution
            prompt = f"""{agent_prompt} Utilisez les extraits de documents ci-dessous pour répondre à la question de l'utilisateur.

CONTEXTE DES DOCUMENTS ({len(documents_info)} document(s) sélectionné(s)):
{enhanced_context}

CONSIGNES:
- Basez votre réponse uniquement sur les informations fournies dans les extraits
- Mentionnez de quel(s) document(s) proviennent les informations (ex: "Selon le document 'nom_fichier'...")
- Si la réponse nécessite des informations de plusieurs documents, organisez votre réponse clairement
- Si vous ne trouvez pas d'information pertinente, dites-le clairement
- Soyez précis et professionnel

Question: {question}

Réponse:"""
        
        # Always get AI response with retry
        logger.info("Getting response from OpenAI")
        response = get_chat_response(prompt)
        logger.info("Successfully got response from OpenAI")
        
        return response
    
    except Exception as e:
        logger.error(f"Error getting answer: {e}")
        # Re-raise the exception to propagate to the API endpoint for proper error handling
        raise Exception(f"Erreur lors du traitement de votre question avec l'API OpenAI : {str(e)}")

def search_similar_texts_for_user(query_embedding: List[float], user_id: int, db: Session, top_k: int = 3, selected_doc_ids: List[int] = None) -> List[dict]:
    """Search similar texts for a specific user - returns structured data with document info"""
    try:
        # Get all chunks for user's documents (filter by selected documents if provided)
        query = db.query(DocumentChunk, Document).join(Document).filter(
            Document.user_id == user_id
        )
        
        if selected_doc_ids:
            query = query.filter(Document.id.in_(selected_doc_ids))
            
        chunks_with_docs = query.all()
        
        if not chunks_with_docs:
            return []
        
        # Simple similarity search with document info
        similarities = []
        for chunk, document in chunks_with_docs:
            if chunk.embedding:
                chunk_embedding = json.loads(chunk.embedding)
                similarity = cosine_similarity(query_embedding, chunk_embedding)
                similarities.append({
                    'similarity': similarity,
                    'text': chunk.chunk_text,
                    'document_id': document.id,
                    'document_name': document.filename,
                    'created_at': document.created_at.isoformat()
                })
        
        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:top_k]
    
    except Exception as e:
        logger.error(f"Error searching similar texts: {e}")
        return []

def get_documents_summary(user_id: int, db: Session, selected_doc_ids: List[int] = None) -> List[dict]:
    """Get complete information about user's documents"""
    try:
        if selected_doc_ids:
            documents = db.query(Document).filter(
                Document.user_id == user_id,
                Document.id.in_(selected_doc_ids)
            ).all()
        else:
            documents = db.query(Document).filter(Document.user_id == user_id).all()
        
        doc_info = []
        for doc in documents:
            # Get all chunks for this document
            chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
            content = " ".join([chunk.chunk_text for chunk in chunks])
            
            doc_info.append({
                'id': doc.id,
                'filename': doc.filename,
                'created_at': doc.created_at.isoformat(),
                'content': content[:2000] + "..." if len(content) > 2000 else content,  # Limit content
                'chunk_count': len(chunks)
            })
        
        return doc_info
    
    except Exception as e:
        logger.error(f"Error getting documents summary: {e}")
        return []

def search_text_fallback(question: str, user_id: int, db: Session, top_k: int = 3) -> List[str]:
    """Fallback text search when embeddings are not available"""
    try:
        # Get all chunks for user's documents
        chunks = db.query(DocumentChunk).join(Document).filter(
            Document.user_id == user_id
        ).all()
        
        if not chunks:
            return []
        
        # Simple keyword matching
        question_words = question.lower().split()
        scored_chunks = []
        
        for chunk in chunks:
            chunk_text = chunk.chunk_text.lower()
            score = 0
            
            # Count word matches
            for word in question_words:
                if len(word) > 2:  # Skip very short words
                    score += chunk_text.count(word)
            
            if score > 0:
                scored_chunks.append((score, chunk.chunk_text))
        
        # Sort by score and return top results
        scored_chunks.sort(reverse=True, key=lambda x: x[0])
        return [text for _, text in scored_chunks[:top_k]]
    
    except Exception as e:
        logger.error(f"Error in text fallback search: {e}")
        return []

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    import numpy as np
    
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0
    
    return dot_product / (norm_vec1 * norm_vec2)

def process_document_for_user(filename: str, content: bytes, user_id: int, db: Session, agent_id: int = None) -> int:
    """Process and store document for specific user and optionally for a specific agent"""
    import tempfile
    import os
    
    try:
        logger.info(f"Starting to process document: {filename} for user {user_id}, agent {agent_id}")
        
        # Save document to database first
        document = Document(
            filename=filename,
            content=content.decode('utf-8') if filename.endswith('.txt') else str(content),
            user_id=user_id,
            agent_id=agent_id
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        logger.info(f"Document saved to database with ID: {document.id}")
        
        # Process content based on file type
        if filename.endswith('.pdf'):
            # Save content temporarily to process with pdfplumber
            tmp_file = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp_file = tmp.name
                    tmp.write(content)
                logger.info(f"Processing PDF file: {tmp_file}")
                text_content = load_text_from_pdf(tmp_file)
            finally:
                # Clean up temporary file
                if tmp_file and os.path.exists(tmp_file):
                    os.unlink(tmp_file)
        else:
            text_content = content.decode('utf-8')
        
        logger.info(f"Extracted text length: {len(text_content)} characters")
        
        # Chunk the text
        chunks = chunk_text(text_content)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Process first few chunks with embeddings, save others without embeddings for now
        max_immediate_chunks = 20  # Process only first 20 chunks immediately
        
        for i, chunk in enumerate(chunks):
            if i < max_immediate_chunks:
                logger.info(f"Processing chunk {i+1}/{len(chunks)} with embedding")
                try:
                    # Get embedding for chunk with shorter timeout
                    embedding = get_embedding_fast(chunk)
                except Exception as e:
                    logger.warning(f"Failed to get embedding for chunk {i}, using dummy: {e}")
                    embedding = [0.0] * 1536
            else:
                logger.info(f"Saving chunk {i+1}/{len(chunks)} without embedding (will process later)")
                embedding = None  # Will be processed later
            
            # Save chunk to database
            doc_chunk = DocumentChunk(
                document_id=document.id,
                chunk_text=chunk,
                embedding=json.dumps(embedding) if embedding else None,
                chunk_index=i
            )
            db.add(doc_chunk)
        
        db.commit()
        logger.info(f"Document processed successfully: {filename} for user {user_id}")
        return document.id
    
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        db.rollback()
        raise e
