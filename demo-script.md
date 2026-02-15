# ACMS Desktop Demo Script - Multi-Tool Context Flow

**Purpose**: Demonstrate context flowing seamlessly between ChatGPT, Cursor, and Claude  
**Duration**: 10 minutes  
**Audience**: You (first user), then colleagues/friends  
**Goal**: Prove ACMS saves time and eliminates context repetition  

---

## 🎬 **SETUP (Before Demo)**

### **Prerequisites:**
```bash
# 1. ACMS Desktop running
open -a "ACMS Desktop"  # macOS
# Or: ACMS Desktop.exe  # Windows

# 2. Check services are up
curl http://localhost:40080/context/status
# Should return: {"total_memories": 0, "connected_tools": []}

# 3. Extensions installed
# - Chrome: ACMS Context Bridge enabled on chat.openai.com
# - Cursor: ACMS extension visible in status bar
# - Chrome: ACMS Context Bridge enabled on claude.ai

# 4. Clear any existing memories (fresh demo)
# Menu Bar → Settings → Clear All Memories → Confirm
```

### **Demo Environment:**
- Browser 1: ChatGPT (https://chat.openai.com)
- Browser 2: Claude (https://claude.ai)
- IDE: Cursor (with a sample project open)
- Menu Bar: ACMS Desktop status visible

---

## 📝 **DEMO SCRIPT**

### **Act 1: The Problem (1 minute)**

**Narrator (you):**
> "Right now, when I use AI tools, I have to repeat context constantly. Watch..."

**Show the pain:**
1. Open ChatGPT
2. Type: *"I'm building a Python web scraper using BeautifulSoup and Selenium. It needs to handle dynamic JavaScript pages and rate limiting."*
3. ChatGPT responds with suggestions
4. Open Cursor
5. **Problem**: Cursor has NO IDEA about your scraper project
6. You'd have to copy-paste the ChatGPT conversation or re-explain everything

**Point made:** *"See? Every tool starts from zero. This is painful."*

---

### **Act 2: ACMS in Action (6 minutes)**

#### **Step 1: Explain Project in ChatGPT (2 min)**

**Action:**
1. Open ChatGPT in Chrome (extension active)
2. Type this query:

```
I'm building a Python web scraper for a real estate website. 
Here are the requirements:

- Target site: example.com/listings
- Dynamic JavaScript content (React-based)
- Need to extract: property title, price, location, description
- Must respect rate limits (max 1 request per 2 seconds)
- Store results in PostgreSQL database

What's the best architecture for this?
```

3. **Before hitting Enter**, notice ACMS badge says: *"No context available (new conversation)"*

4. Hit Enter, let ChatGPT respond

5. **Watch ACMS in action:**
   - Menu Bar notification: *"Stored memory from ChatGPT"*
   - ACMS Desktop shows: *"1 memory stored"*

6. ChatGPT provides architecture suggestions (BeautifulSoup + Selenium + Playwright)

**Checkpoint:** You've now stored your project context in ACMS.

---

#### **Step 2: Write Code in Cursor (2 min)**

**Action:**
1. Switch to Cursor IDE
2. Create new file: `scraper.py`
3. Start typing code (or use Cursor's AI):

```python
import time
from selenium import webdriver
from bs4 import BeautifulSoup

# Start typing here...
```

4. **Click ACMS icon in status bar** (or Cmd+Shift+P → "ACMS: Get Context")

5. **Watch the magic:**
   - ACMS retrieves your ChatGPT conversation
   - New editor opens with context:

```markdown
# Relevant Context from ACMS

## Memory 1 (from ChatGPT, 2 minutes ago)
Web scraper project:
- Target: example.com/listings
- Dynamic content (React)
- Extract: title, price, location, description
- Rate limiting: 1 req / 2 sec
- Database: PostgreSQL

## Memory 2 (from ChatGPT, 2 minutes ago)
Architecture suggestions:
- Use Selenium for JavaScript rendering
- BeautifulSoup for HTML parsing
- Implement exponential backoff
- Connection pooling for PostgreSQL
```

6. Continue coding with this context visible
7. **Cursor's autocomplete is now context-aware** (knows about rate limiting, PostgreSQL, etc.)

**Checkpoint:** Cursor now knows your full project without you explaining anything!

---

#### **Step 3: Ask Claude for Review (2 min)**

**Action:**
1. Switch to Claude in browser
2. Paste your code from Cursor:

```python
import time
from selenium import webdriver
from bs4 import BeautifulSoup
import psycopg2

def scrape_listings():
    driver = webdriver.Chrome()
    driver.get('https://example.com/listings')
    time.sleep(2)  # Wait for JS to load
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    listings = soup.find_all('div', class_='listing-card')
    
    for listing in listings:
        title = listing.find('h2').text
        price = listing.find('span', class_='price').text
        # ... more extraction
        
        # Store in database
        conn = psycopg2.connect("dbname=scraper")
        # ...
```

3. Ask Claude: *"Please review this code and suggest improvements for error handling and rate limiting."*

4. **Watch ACMS inject context AUTOMATICALLY:**
   - Extension badge: *"Context injected (2 memories, 347 tokens)"*
   - Claude's query input now has:

```xml
<context>
<memory>Web scraper project for example.com with rate limiting requirements...</memory>
<memory>Architecture using Selenium + BeautifulSoup + PostgreSQL...</memory>
</context>

Please review this code and suggest improvements for error handling and rate limiting.

[Your code here]
```

5. Claude responds with **context-aware** suggestions:
   - "I see you're implementing the rate limiting requirement from your ChatGPT discussion..."
   - "Given your PostgreSQL setup, consider using connection pooling..."
   - **Claude KNOWS about your project without you explaining!**

**Checkpoint:** Claude reviewed your code with FULL context of your project from ChatGPT and Cursor!

---

### **Act 3: The Reveal (3 minutes)**

#### **Show the Menu Bar App**

**Action:**
1. Click ACMS icon in menu bar
2. **Show statistics:**
   - Total memories: 5 (increased from 0)
   - Connected tools: 3 (ChatGPT, Cursor, Claude)
   - Storage: 12 KB
   - Token savings: 847 tokens (~40% reduction)

3. **Show memory timeline:**
   ```
   2 min ago | ChatGPT | "Web scraper project requirements..."
   1 min ago | ChatGPT | "Architecture suggestions: Selenium + BeautifulSoup..."
   30 sec ago | Cursor  | "scraper.py code saved"
   15 sec ago | Claude  | "Q: Review code for error handling..."
   5 sec ago  | Claude  | "A: Context-aware code review suggestions..."
   ```

4. **Show context injection in real-time:**
   - Go back to ChatGPT
   - Ask: *"What database am I using for this project?"*
   - **Watch:** ACMS badge shows *"Context injected (3 memories, 412 tokens)"*
   - ChatGPT responds: *"You're using PostgreSQL for your web scraper project..."* 
   - **ChatGPT remembered without you explaining!**

---

### **Act 4: The Comparison (1 minute)**

**Split Screen Comparison:**

**Without ACMS:**
```
ChatGPT: Explain project (200 words)
         ↓
Cursor:  Copy-paste context (200 words)
         Write code
         ↓
Claude:  Copy-paste project + code (400 words)
         Review

Total time: 5-10 minutes of copy-pasting
Total tokens: ~2,000 (paying for repeated context)
```

**With ACMS:**
```
ChatGPT: Explain project ONCE (200 words)
         ↓ ACMS stores
Cursor:  Auto-inject context
         Write code
         ↓ ACMS stores
Claude:  Auto-inject everything
         Review

Total time: 30 seconds (context handled automatically)
Total tokens: ~800 (only new content, no repetition)
Savings: 60% less time, 40% fewer tokens
```

---

## 🎯 **DEMO VARIATIONS**

### **Variation A: Code-Heavy Demo (for developers)**
1. ChatGPT: Explain a complex algorithm
2. Cursor: Implement it with ACMS context
3. GitHub Copilot: Auto-complete with full context
4. Claude: Debug with full project knowledge

### **Variation B: Documentation Demo (for writers)**
1. ChatGPT: Brainstorm product features
2. Claude: Write product spec with feature context
3. NotebookLM: Research competitors with spec context
4. Claude: Create marketing copy with all context

### **Variation C: Research Demo (for analysts)**
1. Perplexity: Research topic A
2. ChatGPT: Analyze topic A with Perplexity findings
3. Claude: Cross-reference with topic B
4. Cursor: Write report with all research context

---

## 🐛 **TROUBLESHOOTING**

### **If context NOT injected:**
```bash
# 1. Check ACMS Desktop running
curl http://localhost:40080/context/status

# 2. Check extension installed
# Chrome → Extensions → ACMS Context Bridge enabled

# 3. Check browser console (F12)
# Look for: "ACMS: Context injected (X memories)"

# 4. Manually trigger
# ChatGPT: Click ACMS extension icon → "Inject Context"
```

### **If memories not stored:**
```bash
# 1. Check API logs
# ACMS Desktop → Menu Bar → View Logs

# 2. Test API directly
curl -X POST http://localhost:40080/context/store \
  -H "Content-Type: application/json" \
  -d '{"content": "Test memory", "source": "test"}'

# Should return: {"memory_id": "...", "status": "stored"}
```

### **If demo feels slow:**
```bash
# 1. Check embedding generation time
# Should be < 200ms

# 2. Check Weaviate running
curl http://localhost:8080/v1/.well-known/ready

# 3. Check PostgreSQL connection
docker ps | grep acms_postgres

# 4. Reduce max_tokens in settings
# Menu Bar → Settings → Max Tokens: 1000 (instead of 2000)
```

---

## 📊 **DEMO METRICS TO TRACK**

### **During Demo:**
- [ ] All 3 tools connected successfully
- [ ] Context injected automatically (no manual intervention)
- [ ] Memories visible in Menu Bar app
- [ ] Token count displayed correctly
- [ ] No errors or crashes
- [ ] Demo completed in < 10 minutes

### **After Demo:**
- [ ] Audience impressed (asks "How did you build this?")
- [ ] Questions about privacy (answer: "Local-first, encrypted")
- [ ] Questions about cost (answer: "40% token reduction")
- [ ] Requests to try it themselves
- [ ] Interest from companies/teams

### **Success Criteria:**
✅ Context flows between 3+ tools seamlessly  
✅ Token savings measurable (30-50%)  
✅ No copy-pasting required  
✅ Audience sees clear value proposition  
✅ Demo is reproducible (can run again)  

---

## 🚀 **POST-DEMO: NEXT STEPS**

### **If demo successful:**
1. **Show to 5 friends/colleagues**
2. **Collect feedback** (what worked, what didn't)
3. **Measure actual usage** (use it yourself for 1 week)
4. **Iterate based on feedback**
5. **Prepare for public launch**

### **If demo had issues:**
1. **Debug what went wrong**
2. **Fix issues (Phase 6 refinement)**
3. **Re-run demo**
4. **Don't proceed to launch until demo is solid**

### **Metrics to collect:**
- Time saved per day (measure vs. baseline)
- Token reduction (from API logs)
- Number of context injections (how often it helps)
- Tools used (which integrations most valuable)
- Bugs encountered (prioritize fixes)

---

## 💬 **DEMO SCRIPT (WORD-FOR-WORD)**

If you want to narrate the demo, here's a script:

**Opening (30 seconds):**
> "I use 3 different AI tools daily: ChatGPT for brainstorming, Cursor for coding, and Claude for review. But there's a huge problem: they don't share context. I constantly copy-paste information between them, wasting time and tokens. So I built ACMS Desktop to solve this. Watch."

**ChatGPT Scene (1 min 30 sec):**
> "I'm starting a new project. Let me explain it to ChatGPT once. [Type requirements] See the ACMS icon in the corner? It's capturing this. [ChatGPT responds] Good, now let's write code."

**Cursor Scene (1 min 30 sec):**
> "In Cursor, I'll start coding. But instead of re-explaining the project, I'll just click this ACMS button. [Click] Boom. Cursor now has the full context from ChatGPT. Watch how the autocomplete knows about rate limiting and PostgreSQL. That's because ACMS injected the context. I didn't type a word."

**Claude Scene (1 min 30 sec):**
> "Now let's get a code review from Claude. I'll paste my code and ask for improvements. [Type query] See the badge? ACMS just injected 2 memories with 347 tokens of context. Claude knows about my project from ChatGPT AND my code from Cursor. [Claude responds] Perfect review, fully context-aware."

**Reveal (2 min):**
> "Let me show you what just happened. [Open Menu Bar] ACMS stored 5 memories across 3 tools. Token savings: 847 tokens, which is about 40% less than if I copy-pasted everything. Time saved: probably 5 minutes. And the best part? All of this runs locally. Your data never leaves your computer. Privacy-first, context-rich AI tools. That's ACMS Desktop."

**Closing (30 sec):**
> "This is just the beginning. Imagine every AI tool you use sharing the same memory. No more context amnesia. No more repetition. Just smart, context-aware AI that actually remembers. That's what I built, and I'd love your feedback."

---

## 🎬 **RECORDING THE DEMO**

### **For Video Recording:**
1. **Screen recording**: Use OBS Studio or Loom
2. **Highlight cursor**: Enable macOS pointer highlighting
3. **Show badge notifications**: Make sure ACMS badges visible
4. **Zoom in on key moments**: When context is injected
5. **Add captions**: Explain what's happening

### **For Live Demo:**
1. **Practice 3 times** before showing anyone
2. **Have backup plan**: Pre-recorded video if live fails
3. **Anticipate questions**: "How does it work?" "Is it secure?" "Can I try it?"
4. **Keep it short**: 10 minutes max, people lose attention
5. **End with CTA**: "Want to try it? I'll send you the link."

---

## ✅ **DEMO CHECKLIST**

**Before Demo:**
- [ ] ACMS Desktop installed and running
- [ ] All services healthy (PostgreSQL, Weaviate, Redis, Ollama)
- [ ] Browser extensions installed (ChatGPT, Claude)
- [ ] VS Code extension installed (Cursor)
- [ ] Menu Bar app visible and showing status
- [ ] No existing memories (fresh demo)
- [ ] Internet connection stable (for AI tools)
- [ ] Demo script reviewed and rehearsed

**During Demo:**
- [ ] Explain the problem first (context repetition)
- [ ] Show ChatGPT storing context
- [ ] Show Cursor injecting context automatically
- [ ] Show Claude using combined context
- [ ] Show Menu Bar statistics
- [ ] Compare with/without ACMS
- [ ] Answer questions confidently
- [ ] Stay within 10 minutes

**After Demo:**
- [ ] Collect feedback
- [ ] Note what worked / didn't work
- [ ] Fix any bugs discovered
- [ ] Share recording if available
- [ ] Follow up with interested people

---

**Ready to demo!** 🎬

This demo proves ACMS solves a real problem: context fragmentation across AI tools. When it works smoothly, it's magical. Practice until it's smooth!

**GOOD LUCK!** 🚀
