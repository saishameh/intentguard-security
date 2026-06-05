"""
IntentGuard: AI-Powered Smart Home Automation Framework
3-Layer Architecture: RAG + Agentic AI + Conflict Detection

This implementation replaces the Flowise visual workflow with pure Python code.
"""

import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

# LangChain imports
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.tools import Tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.schema import Document

# Pinecone
from pinecone import Pinecone


@dataclass
class ConflictResult:
    """Result of conflict detection"""
    has_conflict: bool
    conflict_type: Optional[str] = None
    conflicting_rule: Optional[Dict] = None
    explanation: Optional[str] = None
    resolution_strategies: Optional[List[str]] = None


class SmartHomeAgent:
    """
    Main agent class implementing the 3-layer architecture:
    - Layer 1: RAG Knowledge Base (Pinecone + OpenAI Embeddings via OpenRouter)
    - Layer 2: Agentic AI Orchestration (Gemini 2.0 via OpenRouter + LangChain Agent)
    - Layer 3: Conflict Detection (Vector similarity search)
    """
    
    def __init__(
        self,
        openrouter_api_key: str,
        pinecone_api_key: str,
        pinecone_index_name: str = "intentguard"
    ):
        """Initialize the agent with API keys"""
        
        self.openrouter_api_key = openrouter_api_key

        # Layer 1: Initialize RAG components (embeddings via OpenRouter)
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1"
        )
        
        # Initialize Pinecone
        pc = Pinecone(api_key=pinecone_api_key)
        self.index = pc.Index(pinecone_index_name)
        
        # Create vector stores for both namespaces
        self.capabilities_store = PineconeVectorStore(
            index=self.index,
            embedding=self.embeddings,
            namespace="smartthings-capabilities"
        )
        
        self.rules_store = PineconeVectorStore(
            index=self.index,
            embedding=self.embeddings,
            namespace="generated-rules"
        )
        
        # Layer 2: Initialize LLM via OpenRouter
        self.llm = ChatOpenAI(
            model=os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash"),
            openai_api_key=openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.7
        )
        
        # Initialize memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Create tools for the agent
        self.tools = self._create_tools()
        
        # Create agent with system prompt
        self.agent = self._create_agent()
        
        # Path to store generated rules
        self.rules_file = "generated_rules.json"
        
    def _create_tools(self) -> List[Tool]:
        """Create tools for the agent to use"""
        
        # Tool 1: SmartThings Capabilities Retriever
        capabilities_tool = Tool(
            name="smartthings_capabilities",
            description=(
                "Retrieve SmartThings device capabilities and specifications. "
                "Use this to find device attributes, commands, and schemas. "
                "Input should be a natural language query like 'motion sensor capability' "
                "or 'switch commands'."
            ),
            func=self._search_capabilities
        )
        
        # Tool 2: Generated Rules Retriever (for conflict detection)
        rules_tool = Tool(
            name="generated_rules",
            description=(
                "Search existing automation rules to detect conflicts. "
                "Use this BEFORE generating any new rule. "
                "Input should be a description of the intended automation rule."
            ),
            func=self._search_existing_rules
        )
        
        return [capabilities_tool, rules_tool]
    
    def _search_capabilities(self, query: str) -> str:
        """Search SmartThings capabilities using semantic search"""
        docs = self.capabilities_store.similarity_search(query, k=5)
        
        if not docs:
            return "No capabilities found for this query."
        
        results = []
        for i, doc in enumerate(docs, 1):
            results.append(f"Result {i}:\n{doc.page_content}\n")
        
        return "\n".join(results)
    
    def _search_existing_rules(self, query: str) -> str:
        """Search existing rules for potential conflicts"""
        docs = self.rules_store.similarity_search(query, k=5)
        
        if not docs:
            return "No similar existing rules found. No conflicts detected."
        
        results = ["EXISTING RULES FOUND - CHECK FOR CONFLICTS:"]
        for i, doc in enumerate(docs, 1):
            results.append(f"\nRule {i}:\n{doc.page_content}")
        
        return "\n".join(results)
    
    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent with structured prompt"""
        
        system_prompt = """You are an expert IoT automation assistant specializing in SmartThings automation rules.

Your role is to help users create safe, conflict-free automation rules following this MANDATORY workflow:

STEP 1: UNDERSTAND THE REQUEST
- Parse the user's natural language automation request
- Identify the trigger (condition) and action

STEP 2: RETRIEVE CAPABILITIES (MANDATORY)
- Use the 'smartthings_capabilities' tool to find device specifications
- Identify the correct capability, attribute, and command syntax
- Never guess device capabilities - always search first

STEP 3: CONFLICT DETECTION (MANDATORY)
- Use the 'generated_rules' tool to search for similar existing rules
- Analyze for THREE conflict types:
  
  A) DIRECT CONTRADICTIONS
     - Same device, same trigger, opposite actions
     - Example: "Turn lights ON at 11 PM" vs existing "Turn lights OFF at 11 PM"
     - Impact: "Lights will flicker on/off repeatedly"
  
  B) TEMPORAL ILLOGICALITY
     - Rapid cycling within minutes causing wear/damage
     - Example: "Turn AC ON at 2:00 PM" + "Turn AC OFF at 2:10 PM"
     - Impact: "Pointless rapid cycling may damage equipment"
  
  C) CONDITION OVERLAPS
     - Overlapping conditions with different actions
     - Example: "Turn fan ON when humidity > 60%" + "Turn fan OFF when humidity > 65%"
     - Impact: "At 63%, both rules trigger with opposite actions"

STEP 4: DECISION POINT
- If conflicts detected:
  * Explain the conflict type clearly
  * Describe real-world impact (e.g., "lights will flicker")
  * Suggest 3 resolution strategies
  * DO NOT generate JSON until conflict is resolved
  
- If no conflicts:
  * Proceed to JSON generation

STEP 5: JSON GENERATION (Only if no conflicts)
Generate SmartThings-compatible JSON following this structure:

{{
  "name": "Rule description",
  "actions": [
    {{
      "if": {{
        // Trigger condition
      }},
      "then": [
        {{
          "command": {{
            "devices": ["device-id"],
            "commands": [
              {{
                "component": "main",
                "capability": "capability-name",
                "command": "command-name"
              }}
            ]
          }}
        }}
      ]
    }}
  ]
}}

CRITICAL RULES:
1. ALWAYS use tools before generating JSON
2. NEVER generate JSON if conflicts exist
3. Use actual device IDs from the user's request
4. Follow SmartThings schema exactly
5. Provide helpful, non-technical explanations

Begin!"""

        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create agent
        agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Create executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10
        )
        
        return agent_executor
    
    def process_request(self, user_request: str) -> Dict[str, Any]:
        """
        Main entry point: Process a user automation request
        
        Args:
            user_request: Natural language automation request
            
        Returns:
            Dictionary with response, generated JSON (if any), and conflict info
        """
        try:
            result = self.agent.invoke({"input": user_request})
            response = result["output"]
            generated_json = self._extract_json(response)
            
            return {
                "success": True,
                "response": response,
                "generated_json": generated_json,
                "has_json": generated_json is not None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": f"An error occurred: {str(e)}"
            }
    
    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from agent response"""
        import re
        
        # Try to find JSON in code blocks
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError:
                pass
        
        # Try to find raw JSON
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                potential_json = text[start:end]
                return json.loads(potential_json)
        except (json.JSONDecodeError, ValueError):
            pass
        
        return None
    
    def save_rule(self, rule_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save a generated rule to the database
        
        Args:
            rule_json: The automation rule in JSON format
            
        Returns:
            Dictionary with save status and rule ID
        """
        try:
            if os.path.exists(self.rules_file):
                with open(self.rules_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {"rules": []}
            
            rule_id = f"rule_{str(len(data['rules']) + 1).zfill(3)}"
            rule_json["rule_id"] = rule_id
            rule_json["created_at"] = datetime.now().isoformat()
            data["rules"].append(rule_json)
            
            with open(self.rules_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return {
                "success": True,
                "rule_id": rule_id,
                "total_rules": len(data["rules"]),
                "message": f"Rule {rule_id} saved successfully. Remember to re-index Pinecone for conflict detection."
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def upsert_rules_to_pinecone(self, rules_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Upsert rules from JSON file to Pinecone for conflict detection
        
        Args:
            rules_file: Path to rules JSON file (defaults to self.rules_file)
            
        Returns:
            Dictionary with upsert status
        """
        if rules_file is None:
            rules_file = self.rules_file
        
        try:
            with open(rules_file, 'r') as f:
                data = json.load(f)
            
            rules = data.get("rules", [])
            
            if not rules:
                return {
                    "success": False,
                    "message": "No rules found in file"
                }
            
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
                    # Deterministic fallback ID for legacy rules without a rule_id
                    rule_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
                    rule_id = f"rule_hash_{rule_hash}"

                doc = Document(
                    page_content=text,
                    metadata={
                        "rule_id": rule_id,
                        "name": rule.get('name'),
                        "created_at": rule.get('created_at')
                    }
                )
                documents.append(doc)
                ids.append(rule_id)
            
            # Replace namespace contents so upsert is idempotent and doesn't accumulate duplicates.
            self.index.delete(delete_all=True, namespace="generated-rules")
            self.rules_store.add_documents(documents, ids=ids)
            
            return {
                "success": True,
                "rules_upserted": len(documents),
                "message": (
                    f"Successfully synced {len(documents)} rules to Pinecone "
                    "(generated-rules namespace replaced)"
                )
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


def main():
    """Example usage"""
    from dotenv import load_dotenv
    load_dotenv()

    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

    if not OPENROUTER_API_KEY or not PINECONE_API_KEY:
        print("ERROR: Please set OPENROUTER_API_KEY and PINECONE_API_KEY in .env file")
        return

    agent = SmartHomeAgent(
        openrouter_api_key=OPENROUTER_API_KEY,
        pinecone_api_key=PINECONE_API_KEY
    )
    
    print("=" * 80)
    print("EXAMPLE 1: Creating automation rule")
    print("=" * 80)
    
    result = agent.process_request(
        "Turn off the living room fan when motion is no longer detected"
    )
    
    print(f"\nAgent Response:\n{result['response']}")
    
    if result['has_json']:
        print(f"\nGenerated JSON:\n{json.dumps(result['generated_json'], indent=2)}")
        
        save_result = agent.save_rule(result['generated_json'])
        print(f"\nSave Result: {save_result}")
        
        upsert_result = agent.upsert_rules_to_pinecone()
        print(f"\nUpsert Result: {upsert_result}")
    
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Testing conflict detection")
    print("=" * 80)
    
    result2 = agent.process_request(
        "Turn ON the living room fan when motion is no longer detected"
    )
    
    print(f"\nAgent Response:\n{result2['response']}")


if __name__ == "__main__":
    main()
