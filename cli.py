#!/usr/bin/env python3
"""
IntentGuard CLI - Command Line Interface for Smart Home Automation

Usage:
    python cli.py create "Turn off lights when motion stops"
    python cli.py list
    python cli.py interactive
"""

import os
import sys
import json
import argparse
from dotenv import load_dotenv
from smart_home_agent import SmartHomeAgent


class IntentGuardCLI:
    """Command line interface for IntentGuard"""
    
    def __init__(self):
        """Initialize CLI"""
        load_dotenv()
        
        # Get API keys
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        
        if not openrouter_api_key or not pinecone_api_key:
            print("ERROR: API keys not found!")
            print("Please create a .env file with OPENROUTER_API_KEY and PINECONE_API_KEY")
            sys.exit(1)
        
        # Initialize agent
        print("Initializing IntentGuard Agent...")
        self.agent = SmartHomeAgent(
            openrouter_api_key=openrouter_api_key,
            pinecone_api_key=pinecone_api_key
        )
        print("✓ Agent initialized\n")
    
    def create_rule(self, request: str):
        """Create a new automation rule"""
        print("="*80)
        print(f"REQUEST: {request}")
        print("="*80 + "\n")
        
        # Process request
        result = self.agent.process_request(request)
        
        if not result["success"]:
            print(f"❌ ERROR: {result.get('error')}")
            return
        
        # Display response
        print("AGENT RESPONSE:")
        print("-"*80)
        print(result["response"])
        print("-"*80 + "\n")
        
        # Check if JSON was generated
        if result["has_json"]:
            print("✓ Automation rule generated!")
            print("\nGENERATED JSON:")
            print(json.dumps(result["generated_json"], indent=2))
            
            # Ask to save
            save = input("\n💾 Save this rule? (y/n): ").strip().lower()
            if save == 'y':
                save_result = self.agent.save_rule(result["generated_json"])
                if save_result["success"]:
                    print(f"✓ Rule saved as {save_result['rule_id']}")
                    print(f"  Total rules: {save_result['total_rules']}")
                    
                    # Ask to upsert to Pinecone
                    upsert = input("\n🔄 Update Pinecone index for conflict detection? (y/n): ").strip().lower()
                    if upsert == 'y':
                        upsert_result = self.agent.upsert_rules_to_pinecone()
                        if upsert_result["success"]:
                            print(f"✓ {upsert_result['message']}")
                        else:
                            print(f"❌ Upsert failed: {upsert_result.get('error')}")
                else:
                    print(f"❌ Save failed: {save_result.get('error')}")
        else:
            print("ℹ️  No JSON generated (conflict detected or invalid request)")
    
    def list_rules(self):
        """List all saved rules"""
        rules_file = "generated_rules.json"
        
        if not os.path.exists(rules_file):
            print("No rules found. Create your first rule with: python cli.py create \"your request\"")
            return
        
        with open(rules_file, 'r') as f:
            data = json.load(f)
        
        rules = data.get("rules", [])
        
        if not rules:
            print("No rules found.")
            return
        
        print("="*80)
        print(f"SAVED AUTOMATION RULES ({len(rules)} total)")
        print("="*80 + "\n")
        
        for i, rule in enumerate(rules, 1):
            print(f"{i}. {rule.get('rule_id', 'N/A')}")
            print(f"   Name: {rule.get('name', 'No name')}")
            print(f"   Created: {rule.get('created_at', 'Unknown')}")
            print()
    
    def interactive_mode(self):
        """Interactive chat mode"""
        print("="*80)
        print("INTERACTIVE MODE")
        print("="*80)
        print("\nEnter automation requests, type 'quit' to exit.\n")
        
        while True:
            try:
                request = input("You: ").strip()
                
                if not request:
                    continue
                
                if request.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye!")
                    break
                
                if request.lower() == 'list':
                    self.list_rules()
                    continue
                
                # Process request
                print("\nAgent: ", end="", flush=True)
                result = self.agent.process_request(request)
                
                if result["success"]:
                    print(result["response"])
                    
                    if result["has_json"]:
                        print("\n📋 JSON Generated:")
                        print(json.dumps(result["generated_json"], indent=2))
                        
                        save = input("\n💾 Save? (y/n): ").strip().lower()
                        if save == 'y':
                            save_result = self.agent.save_rule(result["generated_json"])
                            print(save_result.get('message', 'Saved!'))
                else:
                    print(f"Error: {result.get('error')}")
                
                print()
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}\n")
    
    def view_rule(self, rule_id: str):
        """View a specific rule"""
        rules_file = "generated_rules.json"
        
        if not os.path.exists(rules_file):
            print("No rules found.")
            return
        
        with open(rules_file, 'r') as f:
            data = json.load(f)
        
        rule = next((r for r in data.get("rules", []) if r.get("rule_id") == rule_id), None)
        
        if not rule:
            print(f"Rule '{rule_id}' not found.")
            return
        
        print("="*80)
        print(f"RULE: {rule_id}")
        print("="*80 + "\n")
        print(json.dumps(rule, indent=2))


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="IntentGuard - AI-Powered Smart Home Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py create "Turn off lights when motion stops"
  python cli.py list
  python cli.py view rule_001
  python cli.py interactive
        """
    )
    
    parser.add_argument(
        'command',
        choices=['create', 'list', 'view', 'interactive'],
        help='Command to execute'
    )
    
    parser.add_argument(
        'args',
        nargs='*',
        help='Command arguments'
    )
    
    args = parser.parse_args()
    
    # Initialize CLI
    cli = IntentGuardCLI()
    
    # Execute command
    if args.command == 'create':
        if not args.args:
            print("Error: Please provide an automation request")
            print("Example: python cli.py create \"Turn off lights when motion stops\"")
            sys.exit(1)
        request = ' '.join(args.args)
        cli.create_rule(request)
    
    elif args.command == 'list':
        cli.list_rules()
    
    elif args.command == 'view':
        if not args.args:
            print("Error: Please provide a rule ID")
            print("Example: python cli.py view rule_001")
            sys.exit(1)
        cli.view_rule(args.args[0])
    
    elif args.command == 'interactive':
        cli.interactive_mode()


if __name__ == "__main__":
    main()