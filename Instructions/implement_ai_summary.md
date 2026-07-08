Here is the complete, self-contained implementation prompt documentation for your AI agent. You can copy the entire markdown block below and hand it directly to your agent to build out the **Give Summary** execution layer.

---

```markdown
# System Prompt: Implement the AI Coach "Give Summary" Feature Layer

You are an expert backend engineer specializing in FastAPI and LLM orchestrations (specifically using the Google Gemini SDK). Your task is to implement the execution layer for the **Give Summary** feature in the backend. 

### Context & Existing Architecture
1. `data_transformer.py`: Computes high-fidelity data contracts. The `AnalyticsSummaryResponse` Pydantic model is already built and contains filtered arrays of `weak_tags`, `strong_tags`, and calculated metadata like `top_issue_verdict`.
2. `server.py`: Contains a global `SERVER_CACHE` dictionary mapping user handles to their processed Pydantic data contracts with a 15-minute TTL window.

### Objective
Create a service module (`summary_service.py`) and expose a specialized endpoint `/api/v1/summary/{handle}/ai-coach` in `server.py`. This endpoint will pull the pre-calculated, filtered `AnalyticsSummaryResponse` data directly from the in-memory cache, structure it into an engineered prompt, and send it to the Gemini API (`gemini-2.5-flash` or `gemini-1.5-flash`) to generate a highly specific, realistic performance summary from the perspective of an elite Competitive Programming Coach.

---

## 1. Architectural Strategy: The Compressed Injection Pattern
Do not send thousands of lines of raw submission arrays to the LLM. Instead, read the cached Pydantic data layer, convert its calculated metrics into a small JSON payload string, and pass it into the prompt template. This keeps context tokens minimal, costs low, and ensures sub-second processing speeds.

---

## 2. Implementation Steps Required

### Step A: Create `summary_service.py`
Implement a standalone asynchronous function `generate_coach_summary(analytics_data: AnalyticsSummaryResponse) -> str`. 
* Initialize the Gemini client using the official `google-genai` or standard `google-generativeai` SDK, retrieving the API key securely from environmental variables (`os.environ["GEMINI_API_KEY"]`).
* Construct the precise prompt layout below, injecting the typed variables directly from the Pydantic model object.

### Step B: The Core LLM Engine Prompt Template
Your function must feed the following system configuration and instruction template into the Gemini model call:

```text
You are an elite, world-class Competitive Programming Coach. Your job is to analyze a student's pre-calculated performance metrics and compile an incisive, highly personalized diagnostic executive summary. 

Do not repeat raw numbers or percentages back to the user point-blank. Instead, translate what those numbers reveal about their coding behaviors, cognitive blocks, and implementation style.

### THE STUDENT TELEMETRY DATA (JSON):
{analytics_json}

### OUTPUT FORMAT REQUIREMENTS:
Generate a beautifully formatted Markdown response divided into exactly three distinct sections with the specified headings. Keep the tone professional, direct, analytical, and encouraging yet firm.

### SECTION INSTRUCTIONS:

## 🤖 Coach's Diagnostic Summary

### 1. Executive Position Analysis
Assess their competitive programming equilibrium using their 'current_rating', 'max_rating', and platform 'rank'. Look at their 'overall_acceptance_rate'. A low acceptance rate (e.g., under 45%) with many submissions points to a reckless "submit-and-pray" habit. A high acceptance rate with static ratings suggests over-cautiousness. Provide a razor-sharp assessment of their mental pacing.

### 2. Primary Bottleneck & Code Failure Analysis
Examine their highest-ranked 'weak_tags' alongside their 'top_issue_verdict' (e.g., TIME_LIMIT_EXCEEDED, WRONG_ANSWER, RUNTIME_ERROR). Explain the precise conceptual or structural programming mistakes causing this exact combination. 
- If 'TIME_LIMIT_EXCEEDED' is paired with topics like graphs/dp, call out poor time complexity awareness, accidental nested loops, or failure to use efficient data structures like Adjacency Lists.
- If 'WRONG_ANSWER' dominates, highlight poor edge-case tracking, lack of dry-running inputs, or weak mathematical invariant handling.

### 3. The 2D Skill Reality Check
Scan the 'weak_tags' and 'strong_tags' arrays for any item marked with the status flag `"status": "under_explored_needs_depth"`. 
If found, issue a critical reality check. Explicitly warn them that their low failure index on this topic is an illusion of mastery caused by a low problem count (sample size bias). Tell them exactly what kind of advanced sub-topics or harder rating tiers they need to tackle to genuinely stress-test their skills in that category.

```

### Step C: Update `server.py` to Route and Cache the Request

Create the router endpoint to connect the frontend to the service layer.

```python
@router.get("/api/v1/summary/{handle}/ai-coach", response_model=Dict[str, str])
async def get_ai_coach_summary(handle: str):
    import time
    current_time = time.time()
    
    # 1. Verify primary cache exists and is fresh
    if handle not in SERVER_CACHE or (current_time - SERVER_CACHE[handle]['timestamp'] > 900):
        raise HTTPException(
            status_code=400, 
            detail="Analytics data missing or expired. Please request base summary first to populate cache."
        )
        
    cached_entry = SERVER_CACHE[handle]
    
    # 2. Check if the AI coach response itself is already cached to save LLM API costs
    if "ai_coach_summary" in cached_entry:
        return {"summary": cached_entry["ai_coach_summary"]}
        
    # 3. Cache Miss for AI text: Pull cached Pydantic summary object
    analytics_data = cached_entry["processed_objects"]["summary"]
    
    try:
        # 4. Trigger the Gemini orchestration pass
        ai_summary_text = await generate_coach_summary(analytics_data)
        
        # 5. Commit the generated text back into the handle's cache payload
        SERVER_CACHE[handle]["ai_coach_summary"] = ai_summary_text
        
        return {"summary": ai_summary_text}
        
    except Exception as e:
        logger.error(f"Gemini Generation Error: {str(e)}")
        raise HTTPException(status_code=503, detail="AI Coaching generation temporarily unavailable.")

```

### Technical Quality Controls

* **Sanitize Inputs:** Before dumping the Pydantic dictionary into the prompt payload template, ensure it is safely converted using `.model_dump_json()` or a clean dict string mapping to avoid schema initialization symbols leaking into the LLM payload.
* **Non-blocking Operations:** Ensure the Gemini call is properly awaited (`await`) so the server loop can process adjacent client traffic while waiting for the model response stream.

```
***

```