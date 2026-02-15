# What Changed: Universal Context API Plan

## 🎯 **Core Vision Shift**

**FROM:** ACMS as a standalone AI assistant with memory  
**TO:** ACMS as the universal memory API that connects ALL AI tools

## 📊 **What This Means**

### **Old Positioning:**
> "An AI assistant that remembers your context"
- Competing with ChatGPT, Claude, Mem, Rewind
- Hard to differentiate
- Single-tool lock-in

### **NEW Positioning:**
> "The universal memory layer for all your AI tools"
- Not competing with ChatGPT/Claude - ENABLING them
- Clear infrastructure play
- Network effects (more tools = more value)
- Enterprise sell is obvious

---

## 🔄 **What Changed in the Plan**

### **✅ Phases 0-3: UNCHANGED**

These phases are PERFECT for the new direction:
- **Phase 0**: Bootstrap memory (ACMS-Lite) ✅ DONE
- **Phase 1**: Infrastructure (Docker, databases) ✅ DONE
- **Phase 2**: Storage Layer (PostgreSQL, Weaviate, encryption)
- **Phase 3**: Core Memory Engine (CRS, ingestion, tiering)

**Why unchanged?** The memory system is the SAME. The difference is how it's EXPOSED.

### **🔄 Phase 4: UPDATED**

**OLD: "Rehydration + LLM Integration"**
- Build single-assistant flow
- Integrate with one LLM (Ollama)
- Context injection for that assistant

**NEW: "Universal Context API"**
- RESTful API for ANY tool to connect
- Tool-agnostic context formatting
- OpenAPI documentation
- Python client library

**Key Addition:**
```python
POST /api/v1/context/store     # Any tool stores memory
POST /api/v1/context/retrieve  # Any tool retrieves context
POST /api/v1/context/feedback  # Outcome learning
```

### **🔄 Phase 5: UPDATED**

**OLD: "Outcome Learning System"**
- Build feedback mechanisms
- Improve CRS over time

**NEW: "Connector Framework"**
- SDK for building connectors
- 5 pre-built connectors:
  1. ChatGPT (browser extension)
  2. Claude / Claude Code (MCP integration)
  3. Cursor (VS Code extension)
  4. GitHub Copilot (VS Code extension)
  5. Glean (API integration)
- Browser extension (Chrome)
- VS Code extension package

**Why the change?**  
Outcome learning is STILL there (in the API), but Phase 5 now focuses on making ACMS usable across multiple tools immediately.

### **✅ Phase 6: MOSTLY UNCHANGED**

- Still production hardening
- Still security (JWT, rate limiting)
- Still self-service web app
- Still documentation

**Addition:**
- Connector marketplace architecture
- More focus on API-first business model

---

## 🎨 **New Architecture Diagram**

```
     ChatGPT ←→ ┌──────────────┐ ←→ Claude
     Cursor  ←→ │     ACMS     │ ←→ Claude Code
     Glean   ←→ │  Universal   │ ←→ Copilot
     Custom  ←→ │  Context API │ ←→ Any AI Tool
                └──────────────┘
                       ↕
            [PostgreSQL + Weaviate]
            [CRS + Memory Engine]
```

**Key insight:** ACMS sits BENEATH all AI tools as the shared memory layer.

---

## 💡 **Why This Is Better**

### **Stronger Value Prop:**
- ❌ "Another AI assistant with memory" (crowded)
- ✅ "The memory fabric for ALL your AI tools" (unique)

### **Clearer Enterprise Sell:**
- ❌ "Try our AI assistant instead of ChatGPT"
- ✅ "Connect ALL your company's AI tools to one memory layer"

### **Better Network Effects:**
- Single tool: Linear value growth
- Multi-tool platform: Exponential value growth
- Each new connector benefits all users

### **Easier GTM:**
- Don't need to convince users to switch AI tools
- Just enhance the tools they already use
- Lower friction = faster adoption

### **Defensible Moat:**
- Not competing on AI quality (that's LLM's job)
- Competing on integration breadth
- Hard to replicate once you have 10+ connectors

---

## 📝 **What to Tell Claude Code**

### **High-Level:**
"We're building the universal memory API that connects all AI tools. Think of ACMS as the 'Stripe for AI context' - any tool can plug in and share memory through our API."

### **Technical:**
"Phases 0-3 remain the same (memory engine). Phase 4 builds a REST API instead of single-LLM integration. Phase 5 builds connector SDK + 5 connectors (ChatGPT, Claude, Cursor, Copilot, Glean) instead of just outcome learning."

### **Strategic:**
"We're not building another AI assistant. We're building the infrastructure layer BENEATH all AI assistants. We make ChatGPT, Claude, and Cursor smarter by giving them shared context."

---

## ✅ **Approval Checklist**

Before proceeding, confirm you agree with:

- [x] **Vision**: Universal memory API (not standalone assistant)
- [x] **Positioning**: "Context Bridge" for all AI tools
- [x] **Phase 0-3**: Keep as planned
- [x] **Phase 4**: Build REST API (not single LLM integration)
- [x] **Phase 5**: Build connectors (ChatGPT, Claude, Cursor, Copilot, Glean)
- [x] **GTM**: Self-published, prosumer → enterprise
- [x] **Timeline**: Still 68 hours (slight extension to Phase 5)

---

## 🚀 **Next Steps**

1. **Review the full build plan** (artifact above)
2. **Confirm you approve** the direction
3. **Tell Claude Code:**
   - Continue with Phase 2 (Storage Layer) as planned
   - Reference updated Phase 4-5 when reaching those phases
   - Key message: "We're building universal context API for all AI tools"

4. **Start building!**
   ```bash
   # Phase 2 begins with:
   python3 acms_lite.py query "PostgreSQL schema requirements"
   # Then proceed with implementation
   ```

---

## ❓ **Questions for You**

1. **Do you approve this direction?** (Context Bridge vs Personal Assistant)
2. **Are there other AI tools** you use that we should add connectors for?
3. **Enterprise vs Consumer first?** 
   - My recommendation: Consumer first (easier validation)
   - Then pivot to enterprise once proven
4. **Which connector to prioritize?**
   - My recommendation: Browser extension first (ChatGPT, Claude, Perplexity)
   - Easiest to demo, biggest reach

Let me know if you want any changes before we proceed! 🚀
