# EduCRM-Dashboard-OCT

Enterprise Admissions Intelligence & Operations Command Center (October 2026 Cohort).

### 🚀 Live Interactive Application
- **Primary Dashboard File**: [`EduCRM_Live_Dashboard.html`](EduCRM_Live_Dashboard.html) (Identical to `index.html`)
- **Instant Live Website (GitHub Pages)**: [https://vishnu-sai-bit.github.io/EduCRM-Dashboard-OCT/](https://vishnu-sai-bit.github.io/EduCRM-Dashboard-OCT/)

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
  - 30-Min Lead Response SLA compliance monitoring.
  - Calling Cadence & Activity pacing across all 7 counsellors.
  - Automated Round-Robin Lead Allotment Engine.
- **Courses & Batches Intelligence**: Program popularity, realization, and batch schedules across all 14 courses.
- **Finance & Tuition Realization**: Fee collection health and 3-tranche installment milestones.
- **Auditing & Executive Reporting**: Performance scorecards and telecalling analytics.

---

### How to Run Locally
1. Download [`EduCRM_Live_Dashboard.html`](EduCRM_Live_Dashboard.html) or clone the repository.
2. Double-click the file to open it in any modern web browser (Chrome, Edge, Firefox, Safari).
3. No installation, server, or database connection required—100% self-contained.
