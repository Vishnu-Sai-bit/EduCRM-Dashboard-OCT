# EduCRM Executive Command Center

Enterprise Admissions Intelligence & Operations Command Center (October 2026 Cohort).

### 🚀 Interactive Application
- **Primary Dashboard File**: [`EduCRM_Live_Dashboard.html`](EduCRM_Live_Dashboard.html) (Identical to `index.html`)

---

### 📂 Repository Structure & Included Datasets
This repository contains the complete end-to-end October 2026 EduCRM project package:
1. **Interactive Web Dashboard**:
   - `index.html` & `EduCRM_Live_Dashboard.html`: Full 8-page self-contained CRM dashboard application (Executive Command Center, Leads Workstation, Lead Journey, Counsellors, Courses & Batches, Lead Sources, Finance & Tuition, Executive Reports).
2. **Authentic October Datasets**:
   - `telecrm-leads-2026-10-01_to_2026-10-31.csv`: 2,856 authentic candidate leads with full attribution, status, and telecalling metadata.
   - `telecrm-activities-2026-10-01_to_2026-10-31.csv`: 57,508 authentic telecalling activities, outgoing calls, connected status, and durations.
   - `telecrm-journeys-2026-10-01_to_2026-10-31.json`: Chronological student journey timelines and event logs.
3. **Data Pipeline & Simulation Scripts**:
   - `build_telecrm_dashboard.py`: Python compiler that parses raw TeleCRM CSV/JSON exports and generates the standalone dashboard.
   - `live_crm_streamer.py`: Real-time streaming simulation engine that models automated round-robin lead allocation and conversion cadence.

---

### Key Capabilities
- **Executive Command Center**: High-level institutional operations, 284 active leads queue, conversion velocity, and tuition realization.
- **Leads Intelligence Engine**: Full CRM lifecycle tracking (New Leads, Contacted, In Follow-up, Interested, Free Demo, Paid Enrolments, Lost/Dropped).
- **Omnichannel & WhatsApp Consultation**: Accurately tracks candidates consulted and enrolled via WhatsApp chats and online messaging (6,877 sent, 3,160 received), with automatic stage progression.
- **Individual Lead Journey**: Universal Lead ID lookup (`6ae2ee1e6e3635090da21830`, numeric sequence, or short hex), milestone flowcharts, and complete chronological telecalling/chat timelines.
- **Counsellors Productivity Hub**: 
  - 30-minute first outgoing call attempt SLA for fresh New Lead records only, timed from the assignment activity; leads stay Pending until the 30-minute deadline and then count as Breached if no attempt is recorded. When assignment history is missing, the lead-created timestamp is used.
  - Calling Cadence & Activity pacing across all 7 counsellors.
  - Automated Round-Robin Lead Allotment Engine.
- **Courses & Batches Intelligence**: Program popularity, realization, and batch schedules across all 14 courses.
- **Finance & Tuition Realization**: Fee collection health and 3-tranche installment milestones.
- **Auditing & Executive Reporting**: Performance scorecards and telecalling analytics.

---

### Optional Whole-Journey AI Summaries
- `Start_EduCRM_Local_AI_Dashboard.bat` starts the local summary server and opens `EduCRM_Live_Dashboard.html`. It can also serve `EduCRM_Live_Dashboard.html` at `http://127.0.0.1:8765/EduCRM_Live_Dashboard.html`.
- Requires Python 3, Ollama, and the local `qwen2.5:3b` model (`ollama pull qwen2.5:3b` if it is not installed). The server binds only to `127.0.0.1` and starts Ollama when needed.
- The model reads the lead's call notes and WhatsApp message text across the full history, then creates a grounded 1–2 sentence summary. Long histories are processed in chunks and combined so all source text is considered.
- The journey timeline keeps communication markers separated by calendar date; notes and WhatsApp messages are grouped only within the same date. The full-history summary remains a separate overview.
- Communication text is sent only to the local Ollama service on the same computer. If the local AI service is unavailable, the dashboard keeps its offline extractive NLP preview and lets the user retry.

### How to Run Locally
1. Download [`EduCRM_Live_Dashboard.html`](EduCRM_Live_Dashboard.html) or clone the repository.
2. Double-click the file to open it in any modern web browser (Chrome, Edge, Firefox, Safari).
3. No installation, server, or database connection required—100% self-contained.
