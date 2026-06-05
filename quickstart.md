# IntentGuard: Quick Start Guide

## 🚀 5-Minute Setup

### Step 1: Get API Keys (2 minutes)

1. **Google AI API Key**
   - Visit: https://makersuite.google.com/app/apikey
   - Click "Create API Key"
   - Copy the key

2. **Pinecone API Key**
   - Visit: https://app.pinecone.io/
   - Sign up (free tier is fine)
   - Go to API Keys
   - Copy the key

### Step 2: Setup Environment (1 minute)

```bash
# Copy environment template
cp .env.template .env

# Edit .env and paste your API keys
nano .env  # or use any text editor
```

Your `.env` should look like:
```
GOOGLE_API_KEY=AIzaSyC...your-key-here
PINECONE_API_KEY=pcsk_...your-key-here
PINECONE_INDEX_NAME=flowise
```

### Step 3: Install Dependencies (1 minute)

```bash
pip install -r requirements.txt
```

### Step 4: Load Data (1 minute)

```bash
# Make sure smartthings_data.txt and test_rules.json are in the directory
python ingest_data.py
```

You should see:
```
✓ Successfully ingested 306 capability chunks to Pinecone
✓ Successfully ingested 39 rule chunks to Pinecone
```

### Step 5: Create Your First Rule! 🎉

```bash
python cli.py create "Turn off the living room fan when motion is no longer detected"
```

## 📋 Common Commands

```bash
# Create a rule
python cli.py create "your automation request"

# List all rules
python cli.py list

# View a specific rule
python cli.py view rule_001

# Interactive chat mode
python cli.py interactive

# Run tests
python test_suite.py
```

## 🧪 Try These Examples

### Example 1: Motion-Based Automation
```bash
python cli.py create "Turn off bedroom lights when no motion detected for 5 minutes"
```

### Example 2: Time-Based Automation
```bash
python cli.py create "Turn on kitchen lights at 7:00 AM on weekdays"
```

### Example 3: Temperature-Based Automation
```bash
python cli.py create "Turn on AC when temperature exceeds 75 degrees"
```

### Example 4: Door Automation
```bash
python cli.py create "Lock the front door at 11 PM every night"
```

## ⚠️ Testing Conflict Detection

Try creating a conflicting rule:

```bash
# First, create a rule
python cli.py create "Turn off all lights at 10 PM"

# Then try the opposite
python cli.py create "Turn on all lights at 10 PM"
```

The agent should detect the conflict and explain the issue!

## 🐛 Troubleshooting

### "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

### "Index not found"
```bash
python ingest_data.py
```

### "No API key"
Check your `.env` file exists and has valid keys

### "No capabilities found"
Make sure `smartthings_data.txt` exists in the directory

## 📚 Next Steps

1. Read the full `README.md` for detailed documentation
2. Check `FLOWISE_VS_PYTHON.md` for comparison with Flowise
3. Run `python test_suite.py` to see all test cases
4. Start building your smart home automations!

## 💡 Pro Tips

1. **Use specific device IDs**: Replace "bedroom-light-id" with your actual SmartThings device IDs
2. **Be descriptive**: "Turn off the living room fan" is better than "Turn off fan"
3. **Check for conflicts**: Always run the agent before deploying to actual devices
4. **Save your work**: The agent automatically saves rules and updates conflict detection

## 🎯 Key Features

✅ Natural language input (no JSON required)  
✅ Automatic conflict detection  
✅ Explainable AI responses  
✅ SmartThings-compatible output  
✅ Persistent storage  
✅ Conflict resolution suggestions  

## 🤝 Need Help?

- Check the `README.md` for full documentation
- Review error messages carefully
- Make sure all data files are present
- Verify API keys are valid

Happy automating! 🏠🤖