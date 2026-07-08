# Backend Specification: Data Transformation Layer (`data_transformer.py`)

This document serves as the absolute technical blueprint, algorithmic breakdown, and system prompt specification for the data transformation layer of the Codeforces companion platform. 

The primary goal of this layer is to ingest raw public data feeds from the Codeforces API and process them into structured, high-fidelity **Data Contracts** (via Pydantic models) that power downstream services: the Analytics Dashboard, the Problem of the Day (POTD) Engine, and the AI-driven Personalized Roadmap Builder.

---

## 1. Architectural Strategy: The Hybrid Approach

To build a high-performance system capable of scaling, this platform leverages a hybrid computational model:
* **Deterministic Computations (Python Backend):** Tasks requiring perfect mathematical accuracy, array de-duplication, filter passes, and thresholding are handled strictly in Python. This runs in less than 2 milliseconds, eliminates LLM miscounting hallucinations, and drops token footprint by up to 95%.
* **Probabilistic Computations (LLM / Gemini RAG):** Contextual reasoning, behavioral analysis, synthesis of curriculum goals, and pedagogical structuring are delegated to the generative AI layer using the highly compressed data payloads provided by Python.

---

## 2. The Data Dependency Matrix

Different downstream features consume different structural facets of a user's competitive programming history. The transformation layer segments data into three distinct targets to preserve network bandwith and prevent context window pollution.

| Data Point | 📊 Analytics Summary | 🎯 POTD Engine | 🗺️ Roadmap Builder |
| :--- | :---: | :---: | :---: |
| **Rank / Current Rating / Peak** | ✅ | ✅ *(Determines Tier)* | ✅ *(Sets Baseline)* |
| **Contest Trend (Rating Graph)** | ✅ | ❌ | ❌ |
| **Overall Acceptance Rate** | ✅ | ❌ | ❌ |
| **Top Issue (WA / TLE / RE)** | ✅ | ❌ | ✅ *(Guides Optimization Advice)* |
| **Problems Solved by Rating** | ✅ | ❌ | ✅ *(Identifies Comfort Zone)* |
| **Weak Tags (High Failure Index)**| ✅ | ✅ *(50% Core Focus Allocation)*| ✅ *(Primary Syllabus Targets)* |
| **Strong Tags (Low Failure Index)**| ✅ | ✅ *(20% Conditioning Allocation)*| ✅ *(Used for Maintenance)* |
| **Untried Tags** | ✅ | ❌ | ✅ *(Breadth Expansion)* |
| **Solved Problem IDs** | ❌ | ✅ *(Exclusion Filter)* | ✅ *(Exclusion Filter)* |
| **Unsolved / Failed Problem IDs**| ❌ | ✅ *(Retry Queue Candidate)* | ✅ *(Targeted Practice)* |
| **Target Rating Goal (User Input)**| ❌ | ❌ | ✅ *(Sets Curriculum Timeline)* |

---

## 3. Detailed Algorithmic Logic & Filtering Strategy

To minimize computational overhead when evaluating accounts with thousands of historical entries, the processing pipeline implements a strict **Single-Pass State Machine** operating at $O(N)$ time complexity.

### Phase 1: In-Memory Data Structure Initialization
Before iterating over the submission array, the processor allocates standard hash maps and sets to enable $O(1)$ mutation and retrieval operations:
* `problem_states`: Map tracking unique problems by structural keys.
* `tag_aggregates`: Map tracking analytical counts (attempts, passes, errors) aggregated under unique tag identifiers.
* `verdict_counts`: High-speed accumulator tracking raw structural execution verdicts (`OK`, `WRONG_ANSWER`, `TIME_LIMIT_EXCEEDED`, etc.).

### Phase 2: The Core Optimization Loop
The engine iterates through the raw historical submission stream exactly once. For each individual submission node, it processes data through the following conditional execution branch:

1. **Unique Key Generation:** Combines the contest identification string and the specific problem matrix index to form a unique workspace key:
   $$\text{Problem ID} = \text{str}(\text{submission['contestId']}) + \text{str}(\text{submission['problem']['index']})$$

2. **Deduplication State Resolution:** * If the generated Problem ID has never been encountered, initialize its state tracking block.
   * If the current iteration reveals a verdict of `"OK"`, mutate the global flag to `"solved": True`. 
   * If the verdict is non-passing (e.g., `"WRONG_ANSWER"`), increment the specific code failure counter. If the problem has not yet achieved an `"OK"` status across any historical node, increment the local problem tracking failure counter.

3. **Tag Multi-Mapping Acceleration:**
   For every computational tag associated with the parsed problem node, update the global analytical collection:
   * Push the unique Problem ID into the tag's `unique_attempted` set.
   * If the verdict evaluates to `"OK"`, push the unique Problem ID into the tag's `unique_solved` set.
   * If the verdict evaluates to a non-passing state, increment the tag's `raw_failures` baseline counter.

### Phase 3: Mathematical Post-Processing & Normalization
Once the primary loop terminates, tag lists are evaluated. To remove data noise caused by accidental click-ins or single-time tries, any tag containing fewer than 3 unique problem attempts is systematically dropped from the weakness/strength ranking system.

For all valid tags, the system calculates the mathematical **Unique Failure Index**:
$$\text{Failure Index}_{\text{tag}} = 1.0 - \left(\frac{|\text{Unique Problems Solved Set}|}{|\text{Unique Problems Attempted Set}|}\right)$$

* **`weak_tags` Extraction:** Generated by sorting verified tags in descending order of their Unique Failure Index.
* **`strong_tags` Extraction:** Generated by sorting verified tags in ascending order of their Unique Failure Index.
* **`untried_tags` Extraction:** Computed by evaluating the asymmetric set difference between a hardcoded master list of all valid platform tags and the active keys compiled inside the local aggregation array.

---

## 4. The 50-30-20 Learning Balance Rule

To protect users from cognitive fatigue and prevent peripheral skills from degrading due to over-focusing on isolated weak spots, the data transformation engine processes the skill profile into a mathematically sound **Training Load Matrix**:

* **50% Core Focus (Targeted Weakness Intervention):** Derived from the highest-ranked `weak_tags`. Problems are mapped out at an elevated target difficulty tier:
  $$\text{Target Difficulty} = \text{Current Rating} + 100 \text{ to } +200$$
* **30% Breadth & Maintenance (General Skill Upkeep):** Sourced from neutral, mid-tier tags or general topics. Problems are targeted directly at the user's equilibrium:
  $$\text{Target Difficulty} = \text{Current Rating}$$
* **20% Conditioning & Velocity (Streak Protection & Confidence):** Sourced from low-error `strong_tags`. Designed to drill implementation speed and maintain psychological momentum:
  $$\text{Target Difficulty} = \text{Current Rating} - 100 \text{ to } -200$$

---

## 5. Edge Cases & Safeguards

To survive production deployments, the processing script implements three strict fallback guards:
1. **The Cold Start Guard:** If a user profile registers fewer than 5 unique problem attempts across their entire operational footprint, the script bypasses index calculation, marks execution status flags as `"insufficient_data"`, and generates balanced placeholder configurations populated with platform fundamentals (`implementation`, `brute force`, `math`).
2. **The Zero-Division Firewall:** Before computing any proportional trends or failure thresholds, all denominator variables must be verified ($>0$) to guarantee the math layer never triggers a critical crash state.
3. **Data Anomaly Tolerations:** Optional metadata fields (like problem difficulty integers or tag lists) are parsed defensively using safe lookups (`.get()`) to guarantee that unrated entries or untagged contests do not interrupt execution.

---

## 6. The Production System Prompt

Copy and paste the exact system prompt sequence below into your backend AI generation framework to produce the target `data_transformer.py` execution asset.

```text
You are an expert backend engineer specializing in Python, FastAPI, and optimized data aggregation algorithms. Your task is to build a high-performance Data Transformation Service for a competitive programming companion platform.

### Objective
Create a single Python file (`data_transformer.py`) containing strictly typed Pydantic models and a core data processor class (`CodeforcesDataProcessor`). This processor must ingest raw data payloads from the Codeforces API, execute a highly optimized single-pass filtering algorithm, and generate three distinct data contracts optimized for an Analytics Dashboard, a Problem of the Day (POTD) engine, and an AI-driven Roadmap Generator.

### Global Configuration & Domain Constants
Define a constant set of all official Codeforces tags to use for untried topic analysis:
ALL_CODEFORCES_TAGS = {
    "data structures", "dp", "geometry", "graphs", "math", "matrices", 
    "strings", "combinatorics", "constructive algorithms", "dfs and similar", 
    "greedy", "implementation", "number theory", "probabilities", 
    "two pointers", "binary search", "bitmasks", "brute force", "sortings"
}

### Output Data Contracts (Pydantic Models)

1. AnalyticsSummaryResponse (For Dashboard Visualization):
   - handle: str
   - current_rating: int
   - max_rating: int
   - rank: str
   - overall_acceptance_rate: float (Total OK verdicts / Total Submissions)
   - top_issue_verdict: str (The non-OK verdict with the highest absolute count)
   - problems_solved_by_rating: Dict[int, int] (e.g., {1200: 14, 1300: 8})
   - weak_tags: List[Dict[str, Any]] (Top 5 tags sorted by highest unique failure index)
   - strong_tags: List[Dict[str, Any]] (Top 5 tags sorted by lowest unique failure index)
   - untried_tags: List[str] (Tags present in ALL_CODEFORCES_TAGS but never attempted)

2. POTDContextResponse (For Lean, Real-Time Filtering Logic):
   - current_rating: int
   - target_training_load: Dict[str, List[str]] (Mapped allocation groups following the 50-30-20 rule)
   - solved_problem_ids: Set[str] (Format: "contestId+index", used for absolute exclusion filtering)
   - failed_problem_ids: Set[str] (Format: "contestId+index", problems attempted but never passed, for retry scheduling)

3. RoadmapContextResponse (For Downstream LLM Prompt Contextualization):
   - current_rating: int
   - target_rating_goal: Optional[int]
   - primary_weakness: str
   - top_issue_verdict: str
   - learning_matrix_profile: Dict[str, Any] (Aggregated tag profiles, counts, and calculated difficulties for downstream injection)

### Algorithmic & Processing Requirements

Your code must process the raw data via a single-pass O(N) algorithmic state machine over the submission history array ('user_status').

1. Unique Problem De-duplication Map:
   - Construct an intermediate dictionary mapping unique problem IDs (str(contestId) + str(index), e.g., "1520F") to an internal state object tracking:
     {"solved": bool, "rating": Optional[int], "tags": List[str], "failed_attempts": int}
   - If any historical submission for a problem ID has a verdict of "OK", its state is permanently set to solved = True. 
   - If the verdict is not "OK", increment 'failed_attempts' and track the raw error type.

2. Tag Accumulation Metrics:
   - For every tag found within a unique problem, track:
     a) Unique Problems Attempted (Set of unique problem IDs)
     b) Unique Problems Solved (Set of unique problem IDs)
     c) Raw Submission Failures (Total count of non-OK submissions)

3. Mathematical Formulations:
   - Calculate the Unique Failure Index for every tag that has a minimum baseline of 3 unique problem attempts (to eliminate analytical noise):
     Failure Index = 1.0 - (Size of Unique Problems Solved Set / Size of Unique Problems Attempted Set)

4. The 50-30-20 Learning Balance Allocation:
   - Mapped out inside the processor logic to divide categories:
     - 50% Core Focus (Target Focus): Selected from 'weak_tags'. Target Difficulty = Current Rating + 100 to +200.
     - 30% Breadth & Maintenance: Selected from neutral/mid-tier failure tags. Target Difficulty = Current Rating.
     - 20% Conditioning & Speed: Selected from 'strong_tags'. Target Difficulty = Current Rating - 100 to -200.

### Edge Case Handling & Defensive Programming
- Zero/Low Submission Profiles: If total unique problems attempted < 5, bypass index sorting, tag data status as "insufficient_data", and return placeholder arrays populated with fundamental categories ("implementation", "brute force", "math").
- Division by Zero: Ensure all percentage and index calculations explicitly verify denominator values (> 0) before performing operations to prevent runtime crashes.
- Missing Values: Gracefully handle missing "rating" keys or empty "tags" arrays within Codeforces submission JSON nodes without breaking the primary execution loop.

Provide the complete, clean, modular, and fully typed Python script inside a single block. Ensure comprehensive documentation comments accompany the main state loop.