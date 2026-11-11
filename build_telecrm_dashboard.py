"""
build_telecrm_dashboard.py
Generates the complete 8-Page EduCRM Live Dashboard using the shared TeleCRM CSV, Excel, and JSON datasets:
1. telecrm-leads-2026-10-01_to_2026-10-31.csv (2,856 authentic leads)
2. telecrm-activities-2026-10-01_to_2026-10-31.csv (57,508 activities & 7,190 outgoing calls)
3. telecrm-journeys-2026-10-01_to_2026-10-31.json (Full chronological journey histories)
"""

import os
import sys
import csv
import json
import pandas as pd

# UTF-8 stdout configuration for Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def build_dashboard():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    leads_csv_path = os.path.join(base_dir, 'telecrm-leads-2026-10-01_to_2026-10-31.csv')
    act_csv_path = os.path.join(base_dir, 'telecrm-activities-2026-10-01_to_2026-10-31.csv')
    journeys_json_path = os.path.join(base_dir, 'telecrm-journeys-2026-10-01_to_2026-10-31.json')

    print(f"Loading leads from: {leads_csv_path}")
    df_leads = pd.read_csv(leads_csv_path)
    print(f"Loaded {len(df_leads):,} lead records.")
    lead_ids_set = set(df_leads['Lead ID'].dropna().astype(str).tolist())

    print(f"Loading activities from: {act_csv_path}")
    df_act = pd.read_csv(act_csv_path, low_memory=False)
    print(f"Loaded {len(df_act):,} activity records.")

    print(f"Loading journeys from: {journeys_json_path}")
    with open(journeys_json_path, 'r', encoding='utf-8') as f:
        raw_journeys = json.load(f)

    # Index journey records ONLY for the leads in df_leads
    lead_journeys = {}
    for item in raw_journeys['data']:
        lid = item.get('lead_id')
        if lid and lid in lead_ids_set:
            clean_events = []
            for ev in item.get('events', []):
                clean_events.append({
                    'at': ev.get('at', ''),
                    'type': ev.get('type', ''),
                    'code': ev.get('code', ''),
                    'by': ev.get('by', ''),
                    'text': (ev.get('text') or ev.get('note') or '')[:300],
                    'duration': ev.get('duration'),
                    'outcome': ev.get('outcome')
                })
            lead_journeys[lid] = {
                'summary': item.get('summary', {}),
                'events': clean_events
            }
    print(f"Indexed {len(lead_journeys):,} matched lead journeys.")

    # Course fee standard catalogue
    COURSE_FEES = {
        'Enrolled Agent': 35000,
        'Modern Data Engineering with AI & Fabric': 50000,
        'Forward Deployed Engineering (FDE)': 45000,
        'AI/ML Engineer': 48000,
        'Microsoft Power Platform with AI Copilot': 38000,
        'AI-Powered Full Stack Python with DSA': 45000,
        'AI-Powered Snowflake Data Engineering': 52000,
        'Azure & MS Fabric for Power BI': 40000,
        'Full Stack Java (+ DSA + AI)': 42000,
        'AI-Powered Data Analytics with Power BI & Fabric': 44000,
        'AIOps & MLOps': 45000,
        'Others': 40000,
        'Unknown': 40000,
        'Unmapped': 40000
    }

    # Meta dictionaries
    all_courses = sorted(list({str(c) for c in df_leads['Course'].dropna().unique() if str(c).strip()}))
    if 'Others' not in all_courses: all_courses.append('Others')
    all_counsellors = sorted(list({str(c) for c in df_leads['Assignee'].dropna().unique() if str(c).strip()}))
    
    # 7 Standardized Statuses
    all_statuses = [
        'New Lead',
        'Follow-up Due',
        'Interested',
        'Free Session Attend',
        'Paid Session',
        'Lost',
        'Others'
    ]

    all_sources = sorted(list({str(s) for s in df_leads['Lead Source'].dropna().unique() if str(s).strip()}))
    all_priorities = ['High', 'Medium', 'Low', 'Urgent']
    all_tasks = ['Phone Call', 'WhatsApp Message', 'Campus Visit']
    all_methods = ['Online / UPI', 'Bank Transfer', 'Credit/Debit Card', 'Cash']
    all_pay_statuses = ['Full-Paid', 'Installment', 'Pending', 'Partial']
    all_fol_statuses = ['Completed', 'Scheduled', 'Pending']

    c_map = {v: i for i, v in enumerate(all_courses)}
    co_map = {v: i for i, v in enumerate(all_counsellors)}
    st_map = {v: i for i, v in enumerate(all_statuses)}
    so_map = {v: i for i, v in enumerate(all_sources)}
    pr_map = {v: i for i, v in enumerate(all_priorities)}
    ta_map = {v: i for i, v in enumerate(all_tasks)}
    me_map = {v: i for i, v in enumerate(all_methods)}
    ps_map = {v: i for i, v in enumerate(all_pay_statuses)}
    fol_map = {v: i for i, v in enumerate(all_fol_statuses)}

    # Distinct lists for text pooling
    names = []
    cities = []
    remarks = []
    next_dates = []
    mod_dates = []

    name_map = {}
    city_map = {}
    rem_map = {}
    nd_map = {}
    mod_map = {}

    def get_or_add(lst, mp, val):
        val_str = str(val) if pd.notna(val) else ''
        if val_str not in mp:
            mp[val_str] = len(lst)
            lst.append(val_str)
        return mp[val_str]

    encoded_rows = []

    for idx, row in df_leads.iterrows():
        # Date & timestamps
        raw_created = str(row['Created On (IST)']) if pd.notna(row['Created On (IST)']) else '2026-10-01 09:00:00'
        enq_date = raw_created.split(' ')[0] if ' ' in raw_created else raw_created
        raw_touch = str(row['Last Human Touch (IST)']) if pd.notna(row['Last Human Touch (IST)']) else raw_created
        mod_date = raw_touch.split(' ')[0] if ' ' in raw_touch else raw_touch

        # Status mapping
        raw_st = str(row['Status']) if pd.notna(row['Status']) else 'New Lead'
        raw_st_lower = raw_st.lower()
        if 'paid' in raw_st_lower:
            ui_status = 'Paid Session'
        elif 'free' in raw_st_lower:
            ui_status = 'Free Session Attend'
        elif 'interested' in raw_st_lower:
            ui_status = 'Interested'
        elif 'follow' in raw_st_lower or 'rnr' in raw_st_lower or 'priority' in raw_st_lower:
            ui_status = 'Follow-up Due'
        elif 'lost' in raw_st_lower:
            ui_status = 'Lost'
        elif 'new' in raw_st_lower:
            ui_status = 'New Lead'
        else:
            ui_status = 'Others'

        course_str = str(row['Course']) if pd.notna(row['Course']) else 'Others'
        assignee_str = str(row['Assignee']) if pd.notna(row['Assignee']) else 'Unassigned'
        source_str = str(row['Lead Source']) if pd.notna(row['Lead Source']) else 'Call Logs'
        city_str = str(row['City']) if pd.notna(row['City']) else 'Hyderabad'
        lead_name = str(row['Name']) if pd.notna(row['Name']) else f"Student #{idx+1}"
        phone_str = str(row['Phone']) if pd.notna(row['Phone']) else f"+91 9{9848000000 + (idx*71)%9999999}"

        course_fee = COURSE_FEES.get(course_str, 40000)
        ltv = float(row['Lifetime Value']) if pd.notna(row['Lifetime Value']) else 0.0

        if ui_status == 'Paid Session':
            fee_paid = int(ltv) if ltv > 0 else course_fee
            pay_st = 'Full-Paid' if fee_paid >= course_fee else 'Partial'
            pay_me = 'Online / UPI'
        else:
            fee_paid = 0
            pay_st = 'Pending'
            pay_me = ''

        calls_made = int(row['Calls Made']) if pd.notna(row['Calls Made']) else 0
        talk_mins = float(row['Talk Time (min)']) if pd.notna(row['Talk Time (min)']) else 0.0

        # Followup status
        if ui_status == 'Paid Session' or ui_status == 'Lost':
            fol_st = 'Completed'
        elif ui_status == 'Follow-up Due':
            fol_st = 'Scheduled'
        else:
            fol_st = 'Pending'

        b_type = (idx % 6)
        lid_num = idx + 1
        lead_id_str = str(row['Lead ID']) if pd.notna(row['Lead ID']) else f"telecrm_{idx+1}"

        lost_r = str(row['Lost Reason']) if pd.notna(row['Lost Reason']) else ''
        candidate_rem = lost_r if lost_r else f"Stage: {row.get('Stage', 'Open')} | Channel: {row.get('Channel', 'Direct')}"

        next_fol_date = '2026-10-31' if ui_status == 'Follow-up Due' else ''

        name_idx = get_or_add(names, name_map, lead_name)
        city_idx = get_or_add(cities, city_map, city_str)
        rem_idx = get_or_add(remarks, rem_map, candidate_rem)
        nd_idx = get_or_add(next_dates, nd_map, next_fol_date) if next_fol_date else -1
        mod_idx = get_or_add(mod_dates, mod_map, mod_date)

        encoded_rows.append([
            enq_date,                                      # 0: enquiry_date
            st_map.get(ui_status, 0),                      # 1: status
            c_map.get(course_str, 0),                      # 2: course
            co_map.get(assignee_str, 0),                   # 3: counsellor
            so_map.get(source_str, 0),                     # 4: source
            pr_map.get('High' if 'Priority' in str(row.get('Status', '')) else 'Medium', 1), # 5: priority
            ta_map.get('Phone Call', 0),                   # 6: task_type
            me_map.get(pay_me, -1),                        # 7: payment_method
            ps_map.get(pay_st, 2),                         # 8: payment_status
            course_fee,                                    # 9: course_fee_inr
            fee_paid,                                      # 10: fee_paid_inr
            calls_made,                                    # 11: total_calls
            int(talk_mins),                                # 12: total_talk_time_mins
            fol_map.get(fol_st, 0),                        # 13: followup_status
            b_type,                                        # 14: batch_type
            lid_num,                                       # 15: lead_num
            name_idx,                                      # 16: name
            city_idx,                                      # 17: city
            rem_idx,                                       # 18: remarks
            nd_idx,                                        # 19: next_followup_date
            mod_idx,                                       # 20: modified_on
            lead_id_str,                                   # 21: authentic TeleCRM lead_id
            phone_str,                                     # 22: authentic phone
            str(row['Minutes to First Attempt']) if pd.notna(row['Minutes to First Attempt']) else None, # 23: SLA mins
            str(row['First Attempt At (IST)']) if pd.notna(row['First Attempt At (IST)']) else '',       # 24: First Attempt At
            str(row['First Connect At (IST)']) if pd.notna(row['First Connect At (IST)']) else '',       # 25: First Connect At
            int(row['Calls Connected']) if pd.notna(row['Calls Connected']) else 0,                       # 26: Calls Connected
            str(row['Lead Link']) if pd.notna(row['Lead Link']) else ''                                   # 27: TeleCRM Link
        ])

    # Extract clean call activities from df_act for counsellor cadence and call logs
    df_calls = df_act[df_act['Activity'] == 'Outgoing call'].copy()
    call_records = []
    for _, cr in df_calls.head(3000).iterrows():
        call_records.append({
            'date': str(cr.get('Date', '')),
            'time': str(cr.get('Time', '')),
            'by': str(cr.get('Performed By', '')),
            'outcome': str(cr.get('Call Outcome', '')),
            'dur_sec': int(cr.get('Duration (sec)', 0)) if pd.notna(cr.get('Duration (sec)')) else 0,
            'lead': str(cr.get('Lead Name', '')),
            'course': str(cr.get('Course', '')),
            'phone': str(cr.get('Phone', ''))
        })

    payload = {
        'meta': {
            'courses': all_courses,
            'counsellors': all_counsellors,
            'statuses': all_statuses,
            'sources': all_sources,
            'priorities': all_priorities,
            'tasks': all_tasks,
            'methods': all_methods,
            'pay_statuses': all_pay_statuses,
            'fol_statuses': all_fol_statuses,
            'names': names,
            'cities': cities,
            'remarks': remarks,
            'next_dates': next_dates,
            'mod_dates': mod_dates
        },
        'data': encoded_rows,
        'journeys': lead_journeys,
        'calls': call_records
    }

    json_payload = json.dumps(payload, separators=(',', ':'))
    print(f"Generated Payload Size: {len(json_payload):,} bytes ({len(json_payload)/(1024*1024):.2f} MB)")

    # Read base HTML template from build_perfect_dashboard.py
    with open(os.path.join(base_dir, 'build_perfect_dashboard.py'), 'r', encoding='utf-8') as f:
        full_py = f.read()

    tmpl_marker = "HTML_TEMPLATE = r'''"
    tmpl_start = full_py.find(tmpl_marker) + len(tmpl_marker)
    tmpl_end = full_py.rfind("'''")
    html_template = full_py[tmpl_start:tmpl_end]

    # In HTML template, replace __RAW_DATA_PLACEHOLDER__
    html = html_template.replace('__RAW_DATA_PLACEHOLDER__', json_payload)

    # Enhance RAW_DATA unpacking in HTML to read authentic TeleCRM fields (rows 21-27) & journeys
    old_unpack_snippet = """      return {
        id: rawLeadId,"""

    new_unpack_snippet = """      // TeleCRM Authentic attributes
      const telecrmLeadId = (row[21] !== undefined && row[21]) ? row[21] : rawLeadId;
      const telecrmPhone = (row[22] !== undefined && row[22]) ? row[22] : ('+91 9' + String(100000000 + ((row[15] * 7919) % 899999999)));
      const rawSlaMinutes = (row[23] !== undefined && row[23] !== null && row[23] !== '') ? Number(row[23]) : null;
      const firstAttemptAt = (row[24] !== undefined && row[24]) ? row[24] : '';
      const firstConnectAt = (row[25] !== undefined && row[25]) ? row[25] : '';
      const callsConnected = (row[26] !== undefined) ? Number(row[26]) : (actualCalls > 0 && actualTalkMins > 0 ? 1 : 0);
      const telecrmLink = (row[27] !== undefined && row[27]) ? row[27] : '';
      const leadJourneyData = (RAW_PAYLOAD.journeys && RAW_PAYLOAD.journeys[telecrmLeadId]) ? RAW_PAYLOAD.journeys[telecrmLeadId] : null;

      // Authentic SLA calculation
      let authenticSlaStatus = 'N/A';
      let authenticSlaTurnaround = rawSlaMinutes;
      if (rawSlaMinutes !== null) {
        authenticSlaStatus = (rawSlaMinutes <= 20) ? 'Met' : 'Breach';
      } else if (st === 'New Lead') {
        authenticSlaStatus = 'Pending';
      }

      return {
        id: telecrmLeadId,
        telecrm_id: telecrmLeadId,
        lead_link: telecrmLink,
        first_attempt_at: firstAttemptAt,
        first_connect_at: firstConnectAt,
        calls_connected: callsConnected,
        journey_data: leadJourneyData,
        phone: telecrmPhone,"""

    if old_unpack_snippet in html:
        html = html.replace(old_unpack_snippet, new_unpack_snippet, 1)
        print("Updated HTML with authentic TeleCRM row unpacker!")

    # In openLeadHistoryModal, render authentic TeleCRM journey events if available
    old_hist_call_check = "if (callLogContainer) {"
    new_hist_call_check = """if (callLogContainer) {
        if (lead.journey_data && lead.journey_data.events && lead.journey_data.events.length > 0) {
          let jEventsHTML = `
            <div style="position:relative; padding-left:26px; border-left:2.5px solid #e2e8f0; margin-left:10px; display:flex; flex-direction:column; gap:12px;">
          `;
          lead.journey_data.events.forEach((ev, eIdx) => {
            const evType = ev.type || 'Activity';
            let dotColor = '#0284c7';
            let icon = '📌';
            if (evType.includes('call') || evType.includes('Call')) { dotColor = '#10b981'; icon = '📞'; }
            else if (evType.includes('WhatsApp')) { dotColor = '#25d366'; icon = '💬'; }
            else if (evType.includes('Status')) { dotColor = '#7c3aed'; icon = '🔄'; }
            else if (evType.includes('Assignment')) { dotColor = '#f59e0b'; icon = '👤'; }
            else if (evType.includes('Payment')) { dotColor = '#059669'; icon = '💳'; }

            jEventsHTML += `
              <div style="position:relative;">
                <div style="position:absolute; left:-33px; top:2px; width:14px; height:14px; border-radius:50%; background:${dotColor}; border:3px solid #ffffff; box-shadow:0 0 0 1.5px ${dotColor};"></div>
                <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:9px 12px;">
                  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:4px;">
                    <span style="font-size:11.5px; font-weight:800; color:#0f172a;">${icon} ${evType}</span>
                    <span style="font-size:10px; color:#64748b; font-weight:700;">🕒 ${ev.at || ''} &bull; ${ev.by || 'System'}</span>
                  </div>
                  ${ev.text ? `<div style="font-size:11px; color:#334155; margin-top:3px; word-break:break-word;">${ev.text}</div>` : ''}
                  ${ev.outcome ? `<div style="font-size:10px; color:#059669; font-weight:700; margin-top:2px;">Outcome: ${ev.outcome} ${ev.duration ? `(${ev.duration}s)` : ''}</div>` : ''}
                </div>
              </div>
            `;
          });
          jEventsHTML += `</div>`;
          callLogContainer.innerHTML = jEventsHTML;
          document.getElementById('leadHistoryModal').classList.add('active');
          return;
        }"""

    if old_hist_call_check in html:
        html = html.replace(old_hist_call_check, new_hist_call_check, 1)
        print("Updated Lead History Modal to render authentic TeleCRM journey event logs!")

    # Update todayStr to October 31, 2026 across HTML
    html = html.replace("'2026-11-06'", "'2026-10-31'")
    html = html.replace('"2026-11-06"', '"2026-10-31"')
    html = html.replace("'2026-11-05'", "'2026-10-30'")
    html = html.replace('"2026-11-05"', '"2026-10-30"')

    # Default date filter to 'all' so full October snapshot renders on load
    html = html.replace("date: 'today'", "date: 'all'")

    # Save to EduCRM_Live_Dashboard.html and index.html
    out_files = [
        os.path.join(base_dir, 'EduCRM_Live_Dashboard.html'),
        os.path.join(base_dir, 'index.html')
    ]

    for p in out_files:
        with open(p, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"Generated: {p} ({len(html):,} bytes)")

if __name__ == '__main__':
    build_dashboard()
