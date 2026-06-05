"""
Data Ingestion Script for IntentGuard - OpenRouter Version
Uses your $10 OpenRouter credits
"""

import os
import json
import hashlib
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv


class DataIngestion:
    """Handles ingestion of capabilities and rules into Pinecone"""
    
    def __init__(self, openrouter_api_key: str, pinecone_api_key: str):
        """Initialize ingestion components"""
        
        # OpenRouter embeddings (uses your $10 credit)
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1"
        )
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=pinecone_api_key)
        
        # Text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    def create_index_if_not_exists(
        self, 
        index_name: str = "intentguard",
        dimension: int = 1536,  # text-embedding-3-small dimension
        metric: str = "cosine"
    ):
        """Create Pinecone index if it doesn't exist"""
        
        existing_indexes = [index.name for index in self.pc.list_indexes()]
        
        if index_name not in existing_indexes:
            print(f"Creating index '{index_name}'...")
            self.pc.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(cloud='aws', region='us-east-1')
            )
            print(f"Index '{index_name}' created successfully!")
        else:
            print(f"Index '{index_name}' already exists.")
        
        return self.pc.Index(index_name)
    
    def ingest_smartthings_capabilities(
        self,
        capabilities_file: str,
        index_name: str = "intentguard"
    ):
        """Ingest SmartThings capabilities from file to Pinecone"""
        
        print(f"\n{'='*80}")
        print("INGESTING SMARTTHINGS CAPABILITIES")
        print(f"{'='*80}\n")
        
        with open(capabilities_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        capabilities = content.split('\n---\n')
        print(f"Found {len(capabilities)} capabilities in file")
        
        documents = []
        for i, cap in enumerate(capabilities):
            if cap.strip():
                doc = Document(
                    page_content=cap.strip(),
                    metadata={"source": "smartthings_capabilities", "chunk_id": i}
                )
                documents.append(doc)
        
        print(f"Created {len(documents)} documents")
        print("Splitting documents into chunks...")
        chunks = self.text_splitter.split_documents(documents)
        print(f"Created {len(chunks)} chunks")
        
        index = self.create_index_if_not_exists(index_name)
        
        print("Embedding and uploading to Pinecone...")
        vector_store = PineconeVectorStore(
            index=index,
            embedding=self.embeddings,
            namespace="smartthings-capabilities"
        )
        
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            vector_store.add_documents(batch)
            print(f"Uploaded batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}")
        
        print(f"\n✓ Successfully ingested {len(chunks)} capability chunks to Pinecone")
        print(f"  Namespace: smartthings-capabilities\n")
        
        return len(chunks)
    
    def ingest_generated_rules(
        self,
        rules_file: str,
        index_name: str = "intentguard"
    ):
        """Ingest generated automation rules from JSON to Pinecone"""
        
        print(f"\n{'='*80}")
        print("INGESTING GENERATED RULES")
        print(f"{'='*80}\n")
        
        with open(rules_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        rules = data.get("rules", [])
        print(f"Found {len(rules)} rules in file")
        
        if not rules:
            print("No rules to ingest.")
            return 0
        
        documents = []
        ids = []
        for rule in rules:
            text = f"""
Rule ID: {rule.get('rule_id', 'unknown')}
Created: {rule.get('created_at', 'unknown')}
Name: {rule.get('name', 'No name')}
Actions: {json.dumps(rule.get('actions', []), indent=2)}
"""
            rule_id = rule.get("rule_id")
            if not rule_id:
                rule_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
                rule_id = f"rule_hash_{rule_hash}"

            doc = Document(
                page_content=text,
                metadata={
                    "rule_id": rule_id,
                    "name": rule.get('name'),
                    "created_at": rule.get('created_at'),
                    "source": "generated_rules"
                }
            )
            documents.append(doc)
            ids.append(rule_id)
        
        print(f"Prepared {len(documents)} rule documents")
        
        index = self.create_index_if_not_exists(index_name)
        
        print("Embedding and uploading to Pinecone...")
        vector_store = PineconeVectorStore(
            index=index,
            embedding=self.embeddings,
            namespace="generated-rules"
        )
        
        # Replace namespace contents so repeated ingestion does not create duplicates.
        index.delete(delete_all=True, namespace="generated-rules")
        vector_store.add_documents(documents, ids=ids)
        
        print(f"\n✓ Successfully ingested {len(documents)} rules to Pinecone")
        print(f"  Namespace: generated-rules\n")

        return len(documents)
    
    def verify_ingestion(self, index_name: str = "intentguard"):
        """Verify that data was ingested correctly"""
        
        print(f"\n{'='*80}")
        print("VERIFICATION")
        print(f"{'='*80}\n")
        
        index = self.pc.Index(index_name)
        stats = index.describe_index_stats()
        
        print(f"Index: {index_name}")
        print(f"Total vectors: {stats.total_vector_count}")
        print(f"\nNamespace statistics:")
        
        for namespace, data in stats.namespaces.items():
            print(f"  - {namespace}: {data.vector_count} vectors")
        
        print(f"\n{'='*80}")
        print("TESTING SEARCHES")
        print(f"{'='*80}\n")
        
        print("Testing capabilities search (query: 'motion sensor')...")
        cap_store = PineconeVectorStore(
            index=index,
            embedding=self.embeddings,
            namespace="smartthings-capabilities"
        )
        cap_results = cap_store.similarity_search("motion sensor", k=3)
        print(f"  Found {len(cap_results)} results")
        if cap_results:
            print(f"  Top result preview: {cap_results[0].page_content[:100]}...")
        
        print("\nTesting rules search (query: 'turn off fan')...")
        rules_store = PineconeVectorStore(
            index=index,
            embedding=self.embeddings,
            namespace="generated-rules"
        )
        rule_results = rules_store.similarity_search("turn off fan", k=3)
        print(f"  Found {len(rule_results)} results")
        if rule_results:
            print(f"  Top result preview: {rule_results[0].page_content[:100]}...")
        
        print(f"\n{'='*80}")
        print("VERIFICATION COMPLETE")
        print(f"{'='*80}\n")


def main():
    """Main ingestion pipeline"""
    
    load_dotenv()
    
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "intentguard")
    
    if not OPENROUTER_API_KEY or not PINECONE_API_KEY:
        print("ERROR: Please set OPENROUTER_API_KEY and PINECONE_API_KEY in .env file")
        return
    
    print("="*80)
    print("INTENTGUARD - OpenRouter Version")
    print("Using your $10 OpenRouter credits")
    print("="*80 + "\n")
    
    ingestion = DataIngestion(
        openrouter_api_key=OPENROUTER_API_KEY,
        pinecone_api_key=PINECONE_API_KEY
    )
    
    cap_count = ingestion.ingest_smartthings_capabilities(
        capabilities_file="smartthings_data.txt",
        index_name=PINECONE_INDEX_NAME
    )
    
    rule_count = ingestion.ingest_generated_rules(
        rules_file="generated_rules.json",
        index_name=PINECONE_INDEX_NAME
    )
    
    ingestion.verify_ingestion(index_name=PINECONE_INDEX_NAME)
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Capabilities ingested: {cap_count} chunks")
    print(f"Rules ingested: {rule_count} chunks")
    print(f"Estimated cost: ~$0.01 from your $10 credit")
    print("\nYou can now use the smart_home_agent.py to create automation rules!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
