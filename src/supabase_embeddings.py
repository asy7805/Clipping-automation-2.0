#!/usr/bin/env python3
"""
Supabase embeddings integration with pgvector support.
This module provides functions to interact with clip embeddings stored in Supabase.
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from supabase import create_client, Client

class SupabaseEmbeddings:
    """Class to handle clip embeddings in Supabase with pgvector support."""
    
    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        """Initialize Supabase client for embeddings."""
        self.supabase_url = supabase_url or os.getenv('SUPABASE_URL')
        self.supabase_key = supabase_key or os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase URL and key must be provided or set as environment variables")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        self.table_name = "clip_embeddings_vector"  # Updated to use pgvector table
    
    def upload_embedding(self, clip_id: str, embedding: np.ndarray, model: str = "openai") -> bool:
        """
        Upload a single embedding to Supabase.
        
        Args:
            clip_id: Unique identifier for the clip
            embedding: Embedding vector as numpy array
            model: Name of the embedding model used
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            data = {
                "clip_id": clip_id,
                "embedding": embedding.tolist(),  # Convert to list for pgvector
                "model": model,
                "created_at": datetime.now().isoformat()
            }
            
            result = self.client.table(self.table_name).insert(data).execute()
            return True
        except Exception as e:
            print(f"❌ Error uploading embedding for {clip_id}: {e}")
            return False
    
    def upload_embeddings_batch(self, embeddings_data: List[Dict]) -> Tuple[int, int]:
        """
        Upload multiple embeddings in batches.
        
        Args:
            embeddings_data: List of dictionaries with clip_id, embedding, and model
            
        Returns:
            Tuple[int, int]: (successful_uploads, failed_uploads)
        """
        successful = 0
        failed = 0
        
        for data in embeddings_data:
            try:
                # Convert numpy array to list if needed
                if isinstance(data['embedding'], np.ndarray):
                    data['embedding'] = data['embedding'].tolist()
                
                # Add timestamp if not present
                if 'created_at' not in data:
                    data['created_at'] = datetime.now().isoformat()
                
                result = self.client.table(self.table_name).insert(data).execute()
                successful += 1
            except Exception as e:
                print(f"❌ Error uploading embedding for {data.get('clip_id', 'unknown')}: {e}")
                failed += 1
        
        return successful, failed
    
    def get_embedding(self, clip_id: str, model: str = "openai") -> Optional[np.ndarray]:
        """
        Retrieve an embedding by clip_id.
        
        Args:
            clip_id: Unique identifier for the clip
            model: Name of the embedding model used
            
        Returns:
            np.ndarray or None: Embedding vector if found
        """
        try:
            result = self.client.table(self.table_name) \
                .select("embedding") \
                .eq("clip_id", clip_id) \
                .eq("model", model) \
                .execute()
            
            if result.data:
                return np.array(result.data[0]['embedding'])
            return None
        except Exception as e:
            print(f"❌ Error retrieving embedding for {clip_id}: {e}")
            return None
    
    def get_embeddings_batch(self, clip_ids: List[str], model: str = "openai") -> Dict[str, np.ndarray]:
        """
        Retrieve multiple embeddings by clip_ids.
        
        Args:
            clip_ids: List of clip identifiers
            model: Name of the embedding model used
            
        Returns:
            Dict[str, np.ndarray]: Dictionary mapping clip_id to embedding
        """
        embeddings = {}
        
        try:
            result = self.client.table(self.table_name) \
                .select("clip_id, embedding") \
                .in_("clip_id", clip_ids) \
                .eq("model", model) \
                .execute()
            
            for row in result.data:
                embeddings[row['clip_id']] = np.array(row['embedding'])
                
        except Exception as e:
            print(f"❌ Error retrieving embeddings batch: {e}")
        
        return embeddings
    
    def find_similar_clips(self, query_embedding: np.ndarray, 
                          similarity_threshold: float = 0.7, 
                          limit: int = 10,
                          model: str = "openai") -> List[Dict]:
        """
        Find similar clips using pgvector similarity search.
        
        Args:
            query_embedding: Query embedding vector
            similarity_threshold: Minimum similarity score (0-1)
            limit: Maximum number of results
            model: Name of the embedding model to search in
            
        Returns:
            List[Dict]: List of similar clips with clip_id and similarity score
        """
        try:
            # Use the pgvector similarity search function
            result = self.client.rpc('find_similar_clips', {
                'query_embedding': query_embedding.tolist(),
                'similarity_threshold': similarity_threshold,
                'limit_count': limit
            }).execute()
            
            # Filter by model if specified
            if model != "openai":  # Default model
                result.data = [clip for clip in result.data if clip['model'] == model]
            
            return result.data
            
        except Exception as e:
            print(f"❌ Error in similarity search: {e}")
            return []
    
    def get_all_embeddings(self, model: str = "openai") -> Tuple[np.ndarray, List[str]]:
        """
        Retrieve all embeddings for a specific model.
        
        Args:
            model: Name of the embedding model
            
        Returns:
            Tuple[np.ndarray, List[str]]: (embeddings_matrix, clip_ids)
        """
        try:
            result = self.client.table(self.table_name) \
                .select("clip_id, embedding") \
                .eq("model", model) \
                .execute()
            
            if not result.data:
                return np.array([]), []
            
            embeddings = []
            clip_ids = []
            
            for row in result.data:
                embeddings.append(row['embedding'])
                clip_ids.append(row['clip_id'])
            
            return np.array(embeddings), clip_ids
            
        except Exception as e:
            print(f"❌ Error retrieving all embeddings: {e}")
            return np.array([]), []
    
    def get_embeddings_count(self, model: str = "openai") -> int:
        """
        Get the total number of embeddings for a model.
        
        Args:
            model: Name of the embedding model
            
        Returns:
            int: Number of embeddings
        """
        try:
            total_result = self.client.table(self.table_name).select("clip_id", count="exact").execute()
            
            if model != "openai":  # Filter by model if not default
                labeled_result = self.client.table(self.table_name) \
                    .select("clip_id", count="exact") \
                    .eq("model", model) \
                    .execute()
                return labeled_result.count
            
            return total_result.count
            
        except Exception as e:
            print(f"❌ Error getting embeddings count: {e}")
            return 0
    
    def delete_embedding(self, clip_id: str, model: str = "openai") -> bool:
        """
        Delete an embedding by clip_id.
        
        Args:
            clip_id: Unique identifier for the clip
            model: Name of the embedding model
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.client.table(self.table_name) \
                .delete() \
                .eq("clip_id", clip_id) \
                .eq("model", model) \
                .execute()
            
            return True
        except Exception as e:
            print(f"❌ Error deleting embedding for {clip_id}: {e}")
            return False
    
    def get_embeddings_for_training(self, model: str = "openai") -> Tuple[np.ndarray, List[str]]:
        """
        Get embeddings specifically formatted for ML training.
        
        Args:
            model: Name of the embedding model
            
        Returns:
            Tuple[np.ndarray, List[str]]: (embeddings_matrix, clip_ids)
        """
        try:
            result = self.client.table(self.table_name) \
                .select("clip_id, embedding") \
                .eq("model", model) \
                .order("created_at") \
                .execute()
            
            if not result.data:
                return np.array([]), []
            
            embeddings = []
            clip_ids = []
            
            for row in result.data:
                embeddings.append(row['embedding'])
                clip_ids.append(row['clip_id'])
            
            return np.array(embeddings), clip_ids
            
        except Exception as e:
            print(f"❌ Error retrieving embeddings for training: {e}")
            return np.array([]), []
    
    def test_connection(self) -> bool:
        """
        Test the connection to Supabase and pgvector functionality.
        
        Returns:
            bool: True if connection and functionality are working
        """
        try:
            # Test basic connection
            result = self.client.table(self.table_name).select("count", count="exact").execute()
            print(f"✅ Connected to {self.table_name}: {result.count} records")
            
            # Test similarity search function
            test_embedding = np.random.rand(1536)
            similar_clips = self.find_similar_clips(test_embedding, similarity_threshold=0.5, limit=5)
            print(f"✅ Similarity search working: {len(similar_clips)} results")
            
            return True
            
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False

# Convenience functions for backward compatibility
def upload_embedding_to_supabase(clip_id: str, embedding: np.ndarray, model: str = "openai") -> bool:
    """Upload a single embedding to Supabase."""
    supabase_emb = SupabaseEmbeddings()
    return supabase_emb.upload_embedding(clip_id, embedding, model)

def find_similar_clips_supabase(query_embedding: np.ndarray, 
                               similarity_threshold: float = 0.7, 
                               limit: int = 10) -> List[Dict]:
    """Find similar clips using Supabase pgvector."""
    supabase_emb = SupabaseEmbeddings()
    return supabase_emb.find_similar_clips(query_embedding, similarity_threshold, limit)

def get_embeddings_from_supabase(model: str = "openai") -> Tuple[np.ndarray, List[str]]:
    """Get all embeddings from Supabase for training."""
    supabase_emb = SupabaseEmbeddings()
    return supabase_emb.get_embeddings_for_training(model) 