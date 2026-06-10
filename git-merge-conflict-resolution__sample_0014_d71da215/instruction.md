## Collaborative Branching & Merge Conflict Resolution

Simulate a team branching strategy with multiple contributors working on a Python package called "tinygraph", introduce intentional merge conflicts, and resolve them through proper Git workflow.

**Technical Requirements:**
- Git version control
- Python 3.x
- Working directory: /app (contains existing git repository)

**Scenario:**
You are Charlie, joining a 3-person team. Alice and Bob have already pushed commits to main. You must create a feature branch, simulate parallel development work, and resolve merge conflicts that arise when integrating changes.

**Required Git Operations:**

1. **Initial Setup:**
   - Configure git user as "Charlie" with email "charlie@tinygraph.dev"
   - Create and switch to branch `charlie/optimise`

2. **Charlie's Work (charlie/optimise branch):**
   - Create file `/app/tinygraph/optim.py` with at least one function
   - Commit with message: "Add optimization module"

3. **Simulate Alice's Work:**
   - Create branch `alice/io` from main
   - Create file `/app/tinygraph/io.py` containing functions `save_graph()` and `load_graph()`
   - Commit with message: "Add I/O module"
   - Merge `alice/io` into `main`

4. **Simulate Bob's Work:**
   - Create branch `bob/algos` from main
   - Create file `/app/tinygraph/algos.py` containing functions `dijkstra()` and `kruskal()`
   - Commit with message: "Add algorithms module"
   - Merge `bob/algos` into `main`

5. **Create Conflict:**
   - On `charlie/optimise` branch, modify `/app/tinygraph/__init__.py` to import from your `optim` module
   - This modification must touch the same lines that were modified in main (by Alice/Bob's merges)
   - Commit with message: "Import optimization module"

6. **Resolve Conflict:**
   - Merge `main` into `charlie/optimise` (this will create a merge conflict in `__init__.py`)
   - Manually resolve the conflict so that ALL imports coexist (optim, io, and algos modules)
   - Complete the merge with message: "Merge main into charlie/optimise"

7. **Final Integration:**
   - Merge `charlie/optimise` into `main`
   - Final `main` branch must contain all four modules: the original code plus `optim.py`, `io.py`, and `algos.py`

**Expected Final State:**
- `/app/tinygraph/__init__.py` imports from all new modules (optim, io, algos)
- `/app/tinygraph/optim.py` exists with optimization functions
- `/app/tinygraph/io.py` exists with `save_graph()` and `load_graph()`
- `/app/tinygraph/algos.py` exists with `dijkstra()` and `kruskal()`
- Git history shows proper branching, merging, and conflict resolution
- All branches (alice/io, bob/algos, charlie/optimise) exist in repository
- Main branch contains all integrated changes
