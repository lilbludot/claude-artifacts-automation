import os
import json
import datetime
from typing import Dict, List, Any, Optional
import uuid

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

class FirestoreClient:
    """Client for interacting with Firestore to store and retrieve Claude conversations and artifacts."""
    
    def __init__(self, service_account_path: str = "config/firebase-credentials.json"):
        """Initialize the Firestore client.
        
        Args:
            service_account_path: Path to the Firebase service account JSON file
        """
        if not firebase_admin._apps:
            # Initialize the app if it hasn't been initialized
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
        
        self.db = firestore.client()
        self.conversations_ref = self.db.collection('conversations')
    
    def save_conversation(self, prompt: str, response: Dict, anthropic_message_id: Optional[str] = None) -> str:
        """Save a conversation to Firestore.
        
        Args:
            prompt: The user's prompt
            response: The Claude response object
            anthropic_message_id: The message ID from Anthropic API
            
        Returns:
            str: The Firestore conversation ID
        """
        # Generate a unique ID for the conversation
        conversation_id = str(uuid.uuid4())
        
        # Create the conversation document
        conversation_data = {
            'created_at': firestore.SERVER_TIMESTAMP,
            'prompt': prompt,
            'response': response,
            'anthropic_message_id': anthropic_message_id
        }
        
        # Save to Firestore
        self.conversations_ref.document(conversation_id).set(conversation_data)
        
        return conversation_id
    
    def save_artifacts(self, conversation_id: str, artifacts: List[Dict]) -> List[str]:
        """Save artifacts from a conversation to Firestore.
        
        Args:
            conversation_id: The Firestore conversation ID
            artifacts: List of artifact dictionaries
            
        Returns:
            List[str]: List of artifact IDs
        """
        artifact_ids = []
        
        # Get reference to the artifacts subcollection
        artifacts_ref = self.conversations_ref.document(conversation_id).collection('artifacts')
        
        for artifact in artifacts:
            # Generate a unique ID for the artifact
            artifact_id = str(uuid.uuid4())
            
            # Add created_at timestamp
            artifact_data = artifact.copy()
            artifact_data['created_at'] = firestore.SERVER_TIMESTAMP
            
            # Save to Firestore
            artifacts_ref.document(artifact_id).set(artifact_data)
            artifact_ids.append(artifact_id)
        
        return artifact_ids
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get a conversation by ID.
        
        Args:
            conversation_id: The Firestore conversation ID
            
        Returns:
            Optional[Dict]: The conversation data, or None if not found
        """
        doc_ref = self.conversations_ref.document(conversation_id)
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()
        else:
            return None
    
    def get_artifacts(self, conversation_id: str) -> List[Dict]:
        """Get all artifacts for a conversation.
        
        Args:
            conversation_id: The Firestore conversation ID
            
        Returns:
            List[Dict]: List of artifact dictionaries
        """
        artifacts_ref = self.conversations_ref.document(conversation_id).collection('artifacts')
        artifacts = []
        
        for doc in artifacts_ref.stream():
            artifact = doc.to_dict()
            artifact['id'] = doc.id
            artifacts.append(artifact)
        
        return artifacts
    
    def get_artifact(self, conversation_id: str, artifact_id: str) -> Optional[Dict]:
        """Get a specific artifact by ID.
        
        Args:
            conversation_id: The Firestore conversation ID
            artifact_id: The artifact ID
            
        Returns:
            Optional[Dict]: The artifact data, or None if not found
        """
        doc_ref = self.conversations_ref.document(conversation_id).collection('artifacts').document(artifact_id)
        doc = doc_ref.get()
        
        if doc.exists:
            artifact = doc.to_dict()
            artifact['id'] = doc.id
            return artifact
        else:
            return None
    
    def list_recent_conversations(self, limit: int = 10) -> List[Dict]:
        """List recent conversations.
        
        Args:
            limit: Maximum number of conversations to retrieve
            
        Returns:
            List[Dict]: List of conversation dictionaries
        """
        query = self.conversations_ref.order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit)
        conversations = []
        
        for doc in query.stream():
            conversation = doc.to_dict()
            conversation['id'] = doc.id
            conversations.append(conversation)
        
        return conversations
    
    def search_artifacts_by_content(self, search_term: str, limit: int = 10) -> List[Dict]:
        """Search for artifacts containing the search term.
        Note: This is a simple implementation that retrieves artifacts and filters in Python.
        For production use with large datasets, consider using a proper search solution.
        
        Args:
            search_term: The term to search for
            limit: Maximum number of results to return
            
        Returns:
            List[Dict]: List of matching artifact dictionaries with conversation IDs
        """
        # This is an inefficient implementation for demo purposes
        # In production, use Algolia, Elasticsearch, or Firebase's full-text search extensions
        search_term = search_term.lower()
        results = []
        
        # Get all conversations (this would be problematic with large datasets)
        for conv_doc in self.conversations_ref.stream():
            conv_id = conv_doc.id
            
            # Get artifacts for this conversation
            artifacts_ref = self.conversations_ref.document(conv_id).collection('artifacts')
            
            for art_doc in artifacts_ref.stream():
                artifact = art_doc.to_dict()
                artifact['id'] = art_doc.id
                
                # Check if search term is in content
                if 'content' in artifact and search_term in artifact['content'].lower():
                    # Add conversation ID to the artifact
                    artifact['conversation_id'] = conv_id
                    results.append(artifact)
                    
                    # Respect the limit
                    if len(results) >= limit:
                        return results
        
        return results