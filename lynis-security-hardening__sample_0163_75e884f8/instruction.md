## Task: System Security Hardening with Lynis

Install and run Lynis to audit system security on an Ubuntu container, then implement the top 5 security recommendations to harden the system.

**Technical Requirements:**
- Environment: Ubuntu container with apt package manager
- Tool: Lynis security auditing tool
- Shell: Bash or compatible shell

**Task Steps:**

1. **Install Lynis**
   - Update package manager cache
   - Install Lynis from official repositories

2. **Run Initial Security Audit**
   - Execute a full Lynis system audit
   - Save the complete audit report to `/app/lynis_initial_report.txt`
   - Ensure the report includes security recommendations with their test IDs

3. **Identify Top 5 Recommendations**
   - Extract the top 5 security recommendations from the Lynis report
   - Document these recommendations in `/app/recommendations.txt` with the following format for each:
     ```
     Recommendation #: [number]
     Test ID: [test-id]
     Category: [category]
     Description: [description]
     Suggested Action: [action]
     ```

4. **Backup Configuration Files**
   - Create backups of all system configuration files that will be modified
   - Store backups in `/app/backups/` directory with original filenames plus `.backup` extension

5. **Implement Security Recommendations**
   - Apply all 5 identified security recommendations
   - Each implementation must address the specific issue identified by Lynis
   - Common categories include: kernel parameters, file permissions, authentication settings, SSH configuration, firewall/network settings

6. **Verify Improvements**
   - Re-run Lynis audit after implementing changes
   - Save the final audit report to `/app/lynis_final_report.txt`
   - Create a summary file `/app/improvements_summary.txt` showing:
     - Initial security score (if available)
     - Final security score (if available)
     - Number of warnings before and after
     - List of implemented recommendations with their test IDs

**Output Files:**
- `/app/lynis_initial_report.txt` - Initial Lynis audit output
- `/app/recommendations.txt` - Top 5 recommendations extracted from report
- `/app/backups/` - Directory containing backup files
- `/app/lynis_final_report.txt` - Final Lynis audit output after hardening
- `/app/improvements_summary.txt` - Summary of security improvements made

**Success Criteria:**
- Lynis successfully installed and executed
- All 5 security recommendations properly identified and documented
- Configuration backups created before modifications
- All 5 recommendations implemented correctly
- Final audit shows measurable security improvements
