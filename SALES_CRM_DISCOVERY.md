# Sales CRM Discovery & Analysis

**Status:** Phase 0.5 - Active  
**Started:** Mar 7, 2026  
**Goal:** Understand what data exists in Zoho CRM before designing metrics  

---

## 🎯 The Problem: Anti-Gaming Metrics Design

**Carlos's Insight:** "We want to evaluate salespeople based on quality metrics and not just vanity metrics. We want insight into all their activity and value the important things they do (not just call and hang up like some do, or fake activity they do to try to game the system)."

### The Gaming Patterns We've Seen:
- 📞 **Call-and-hang-up** → High call volume, zero value
- 💬 **VM rambling** → High talk time by calling VMs and speaking to them
- 📧 **Email spam** → Blasting emails with no engagement
- 📅 **Fake meetings** → Booking meetings that don't happen
- 📊 **Activity theater** → Logging fake activities to appear busy

### The Core Principle: **Holistic Cross-Validation**

Any single metric can be gamed. The answer is correlation:

- ✅ High calls + High meetings booked = Real work
- ❌ High calls + Low meetings = Dialing for dollars
- ❌ High talk time + Low meetings = VM gaming
- ❌ High emails + Low replies = Spam blasting
- ❌ High activity + Pipeline not moving = Fake busy work

**Metrics must tell a coherent story.**

---

## 🔍 Discovery Mission (Before Building)

**Before we design the scoring system, we need to understand:**

1. **What modules exist in Zoho CRM?**
   - Deals, Contacts, Accounts, Leads, Activities, Custom modules?

2. **What activity types are tracked?**
   - Calls, Emails, Meetings, Tasks, Events?
   - Are they logged automatically or manually?

3. **What fields are actually populated?**
   - Call duration, outcome, next steps?
   - Email subject, body, reply tracking?
   - Meeting attendance, no-shows?

4. **What custom fields exist?**
   - Deal stage history, close date changes?
   - Discount tracking, margin data?
   - Forecast categories?

5. **What's actually being used?**
   - Which fields have data vs. empty?
   - Which activities are logged consistently?
   - What's the data quality like?

6. **How does the team use the system?**
   - Do they log call outcomes?
   - Do they track email replies?
   - Do they update deal stages consistently?

---

## 📊 The Analysis Task for Claude Code

### Step 1: Schema Discovery
Pull complete Zoho CRM schema:
- All modules (Deals, Contacts, Activities, etc.)
- All fields per module (standard + custom)
- Field types, relationships, picklist values
- Activity types and their fields

### Step 2: Data Sampling
For each module, sample recent records (last 30 days):
- How many records?
- Which fields have data vs. null?
- Data quality patterns
- Usage patterns (what's being tracked?)

### Step 3: Activity Analysis
Focus on activity logging:
- Call logs: Volume, duration distribution, outcomes logged?
- Email logs: Volume, subject lines, replies tracked?
- Meeting logs: Scheduled vs. held, no-show tracking?
- Task logs: Types, completion rate, detail level?

### Step 4: Deal Pipeline Analysis
Understand deal flow:
- Stages and their definitions
- Stage progression patterns
- Close date change history
- Discount/margin tracking
- Forecast categories

### Step 5: User Activity Patterns
Sample data from active sales reps:
- What do high performers log?
- What do low performers log?
- Differences in data quality/detail
- Red flag patterns

### Step 6: Recommendations Report
Generate a report:
- **Available Metrics** (what data exists)
- **Reliable Metrics** (good data quality, consistently logged)
- **Unreliable Metrics** (poor quality, gaming-prone)
- **Cross-Validation Opportunities** (which metrics should correlate)
- **Proposed Scoring Framework** (based on actual data)

---

## 🎯 Desired Output

A comprehensive analysis document that answers:

1. **What can we measure?** (available data)
2. **What should we measure?** (quality metrics)
3. **How do we validate?** (cross-correlation)
4. **What do we ignore?** (vanity metrics, gaming-prone)

Then we design the Sales Output Rating system based on REAL data, not theoretical models.

---

## ✅ Zoho CRM Connection Status

**Connected:** Mar 7, 2026

- **Account:** ted@tradealliance.io (CEO, TradeAlgo)
- **CRM:** Trade Alliance (Zoho CRM, US region)
- **Credentials:** Secured in `.env`
- **API Status:** Tested and working ✅

**Next:** Run discovery analysis to understand what's in the system.

---

**Once we have the analysis, we'll design the holistic anti-gaming scoring system based on what actually exists in your CRM.**

— Atlas, The Architect 📐
