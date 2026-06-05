# IntentGuard: AI-Powered Smart Home Automation Framework

A Python implementation of the IntentGuard framework from the SANER/ERA 2026 paper. This replaces the Flowise visual workflow with clean, maintainable Python code.

## 🏗️ Architecture

The framework implements a **3-layer architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                    Layer 2: Agentic AI                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Gemini 2.0-Flash + LangChain Agent                   │   │
│  │ • Orchestrates workflow                              │   │
│  │ • Calls tools autonomously                           │   │
│  │ • Makes decisions                                    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           ↕
┌─────────────────────────────────────────────────────────────┐
│              Layer 1: RAG Knowledge Base                     │
│  ┌──────────────────┐        ┌──────────────────┐          │
│  │  SmartThings     │        │  Generated       │          │
│  │  Capabilities    │        │  Rules           │          │
│  │  (306 chunks)    │        │  (Dynamic)       │          │
│  └──────────────────┘        └──────────────────┘          │
│           Pinecone Vector Database                           │
│           • Google text-embedding-004                        │
│           • Cosine similarity search                         │
└─────────────────────────────────────────────────────────────┘
                           ↕
┌─────────────────────────────────────────────────────────────┐
│            Layer 3: Conflict Detection                       │
│  • Direct Contradictions                                     │
│  • Temporal Illogicality                                     │
│  • Condition Overlaps                                        │
└─────────────────────────────────────────────────────────────┘
```

## 📋 Features

- ✅ **Natural Language Input**: No need to photograph devices or write JSON manually
- ✅ **Automatic Conflict Detection**: Semantic search identifies 3 conflict types before deployment
- ✅ **Explainable AI**: Clear explanations with real-world impact descriptions
- ✅ **Platform-Specific Output**: Generates valid SmartThings JSON
- ✅ **Automated Workflow**: Complete pipeline from request to deployment-ready JSON

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.9+
- Google AI API key (for Gemini and embeddings)
- Pinecone API key (free tier works)

### 2. Installation

```bash
# Clone or download the repository
cd intentguard

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.template .env
```

### 3. Configuration

Edit `.env` and add your API keys:

```bash
GOOGLE_API_KEY=your-google-api-key-here
PINECONE_API_KEY=your-pinecone-api-key-here
PINECONE_INDEX_NAME=flowise
```

**How to get API keys:**
- **Google AI**: https://makersuite.google.com/app/apikey
- **Pinecone**: https://app.pinecone.io/ (free tier: 100k vectors)

### 4. Data Ingestion

First, ingest your SmartThings capabilities and test rules:

```bash
# Make sure you have smartthings_data.txt and test_rules.json
python ingest_data.py
```

This will:
1. Create a Pinecone index named "flowise"
2. Embed and upload 306 SmartThings capability chunks
3. Embed and upload your test automation rules
4. Verify the ingestion with test searches

Expected output:
```
Creating index 'flowise'...
Found 134 capabilities in file
Created 306 chunks
✓ Successfully ingested 306 capability chunks to Pinecone
✓ Successfully ingested 39 rule chunks to Pinecone
```

### 5. Usage

#### Option A: Command Line Interface (Recommended)

```bash
# Create a single rule
python cli.py create "Turn off the living room fan when motion is no longer detected"

# List all saved rules
python cli.py list

# View a specific rule
python cli.py view rule_001

# Interactive chat mode
python cli.py interactive
```

#### Option B: Python Script

```python
from smart_home_agent import SmartHomeAgent
import os

# Initialize agent
agent = SmartHomeAgent(
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    pinecone_api_key=os.getenv("PINECONE_API_KEY")
)

# Process request
result = agent.process_request(
    "Turn off the living room fan when motion is no longer detected"
)

print(result["response"])

# Save if JSON was generated
if result["has_json"]:
    agent.save_rule(result["generated_json"])
    agent.upsert_rules_to_pinecone()
```

## 📁 Project Structure

```
intentguard/
├── smart_home_agent.py      # Main agent implementation (Layer 2 + 3)
├── ingest_data.py            # Data ingestion script (Layer 1 setup)
├── cli.py                    # Command-line interface
├── requirements.txt          # Python dependencies
├── .env.template             # Environment variables template
├── .env                      # Your API keys (create this)
├── smartthings_data.txt      # SmartThings capabilities (from your files)
├── test_rules.json           # Initial automation rules (from your files)
└── generated_rules.json      # Saved automation rules (auto-generated)
```

## 🔍 How It Works

### Workflow Steps

1. **User Input**: Natural language automation request
   ```
   "Turn off the living room fan when motion is no longer detected"
   ```

2. **Capability Retrieval** (Layer 1)
   - Agent searches Pinecone for relevant device capabilities
   - Returns SmartThings specifications for motion sensors and switches

3. **Conflict Detection** (Layer 3)
   - Agent searches existing rules using semantic similarity
   - Identifies conflicts across 3 categories:
     - **Direct Contradictions**: Same trigger, opposite actions
     - **Temporal Illogicality**: Rapid cycling (< 1 minute)
     - **Condition Overlaps**: Overlapping conditions with different actions

4. **Decision Point**
   - **If conflicts found**: Explain issue + suggest 3 resolutions → STOP
   - **If no conflicts**: Proceed to JSON generation

5. **JSON Generation**
   - Constructs SmartThings-compatible JSON using:
     - Retrieved capabilities
     - User's device IDs
     - Proper schema structure

6. **Persistence**
   - Save to `generated_rules.json`
   - Upsert to Pinecone for future conflict detection

## 🎯 Example Scenarios

### Example 1: Successful Rule Creation

**Input:**
```bash
python cli.py create "Turn off bedroom lights at 11 PM"
```

**Output:**
```json
{
  "name": "Turn off bedroom lights at 11 PM",
  "actions": [
    {
      "if": {
        "time": {
          "at": "23:00"
        }
      },
      "then": [
        {
          "command": {
            "devices": ["bedroom-light-id"],
            "commands": [
              {
                "component": "main",
                "capability": "switch",
                "command": "off"
              }
            ]
          }
        }
      ]
    }
  ]
}
```

### Example 2: Conflict Detection

**Input:**
```bash
python cli.py create "Turn ON bedroom lights at 11 PM"
```

**Agent Response:**
```
⚠️ CONFLICT DETECTED: Direct Contradiction

I found an existing rule that conflicts with your request:
- Existing: "Turn off bedroom lights at 11 PM"
- Your request: "Turn ON bedroom lights at 11 PM"

Impact: Your lights will flicker on and off repeatedly at 11 PM, 
causing confusion and potential damage.

Suggested resolutions:
1. Change the time to 11 AM instead
2. Change the action to "dim" instead of "on"
3. Delete the existing rule first

JSON generation blocked until conflict is resolved.
```

## 🔧 Customization

### Adding New Device Capabilities

1. Update `smartthings_data.txt` with new capabilities
2. Run: `python ingest_data.py`

### Modifying Conflict Detection Logic

Edit the system prompt in `smart_home_agent.py`:

```python
# Around line 130 in smart_home_agent.py
system_prompt = """
...
STEP 3: CONFLICT DETECTION (MANDATORY)
- Use the 'generated_rules' tool to search for similar existing rules
- Analyze for THREE conflict types:
  
  A) DIRECT CONTRADICTIONS
     [your custom logic here]
...
"""
```

### Using Different LLMs

Replace Gemini with another model:

```python
from langchain_openai import ChatOpenAI

self.llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.7
)
```

## 📊 Comparison: Flowise vs Python

| Aspect | Flowise | Python Implementation |
|--------|---------|----------------------|
| **Setup** | Visual drag-and-drop | Code + CLI |
| **Debugging** | Limited logs | Full stack traces |
| **Customization** | UI constraints | Full control |
| **Version Control** | JSON export | Git-friendly |
| **Testing** | Manual UI testing | Unit tests possible |
| **Automation** | Manual re-upsert | `upsert_rules_to_pinecone()` |
| **Deployment** | Cloud/self-hosted | Any Python environment |

## 🐛 Troubleshooting

### "No capabilities found"
- Verify `smartthings_data.txt` exists
- Re-run `python ingest_data.py`
- Check Pinecone index statistics

### "API key error"
- Verify `.env` file exists
- Check API keys are valid
- Ensure no extra spaces in `.env`

### "Index not found"
- Run `python ingest_data.py` first
- Check Pinecone dashboard for index status

### Agent not detecting conflicts
- Verify rules were upserted: `agent.upsert_rules_to_pinecone()`
- Check namespace: should be "generated-rules"
- Try more specific rule descriptions

## 📈 Performance

- **Embedding**: ~500ms per query (Google text-embedding-004)
- **LLM Response**: 2-5 seconds (Gemini 2.0-Flash)
- **Conflict Detection**: <1 second (Pinecone search)
- **Total Request Time**: 3-7 seconds average

## 🔒 Security Notes

- Store API keys in `.env`, never commit to Git
- Add `.env` to `.gitignore`
- Use environment-specific keys for prod/dev
- Consider using secret management (AWS Secrets Manager, etc.)

## 📚 Additional Resources

- **Paper**: SANER/ERA 2026 - "An Agentic AI Framework for Conflict-Aware Smart Home Automation"
- **SmartThings API**: https://developer.smartthings.com/
- **LangChain Docs**: https://python.langchain.com/
- **Pinecone Docs**: https://docs.pinecone.io/

## 🤝 Contributing

This is a research implementation. For production use:

1. Add comprehensive unit tests
2. Implement error recovery
3. Add rate limiting
4. Create deployment scripts
5. Add monitoring/logging

## 📝 License

MIT License - See LICENSE file

## 🙏 Acknowledgments

Based on research by Sayyada Aisha Mehvish and Manar H. Alalfi at Toronto Metropolitan University.

---

**Note**: This implementation prioritizes code clarity and educational value. For production deployment, additional engineering (error handling, testing, monitoring) is required.