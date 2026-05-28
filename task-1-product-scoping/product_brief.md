# Task 1: Product Scoping - Internal Marketing Analysis

## 1. Initial Analysis
* **The Core Challenge:** The marketing team is constantly asked to evaluate cross-channel performance and identify strategic focus areas right now.
* **The Current Operational Bottleneck:** Answering this question currently requires manual data extraction across multiple disparate tools. This creates delayed responses, high inconsistency based on who pulls the numbers, and a single point of failure if key personnel are unavailable.
* **Core Objective:** Establish a rapid, highly consistent, and automated methodology to address cross-channel performance without forcing the team to change their existing tools or day-to-day operational habits.

## 2. User Description
* **Primary Target User:** The Internal Marketing Analyst / Account Manager.
* **User Context:** This persona deeply understands marketing metrics but is heavily burdened by the manual "data janitor" work required to stitch numbers together. They need a unified canvas that surfaces insights instantly, freeing up their time to focus on client strategy rather than manual formatting.

## 3. Focus Definition (v1 Strategy)
* **Operational Alignment:** Rather than building an overcomplicated system or attempting complex, fragile API integrations upfront, the initial focus will center entirely on streamlining the data layer around the team's current manual export workflows.
* **Core MVP Value:** The v1 implementation must solve the immediate problem of data fragmentation and speed-to-insight for the internal team before expanding functionality to external clients.

## 4. Scope Boundaries (v1 MVP)

### 🟩 In-Scope
* **Unified Cross-Channel Canvas:** A single, aggregated performance dashboard displaying critical top-of-funnel metrics: Total Spend, Impressions, Clicks, Conversions, Blended CPA (Cost Per Acquisition), and Blended ROAS (Return on Ad Spend).
* **"Drop-Zone" File Ingestion:** A centralized, shared storage folder (e.g., Google Drive or Google Cloud Storage staging bucket) where analysts can drop their standard daily/weekly manual CSV exports. The tool automatically detects, parses, and cleans these files without changing the team's current tools.
* **Data Currency Metadata:** A prominent "Last Updated" timestamp for each active ad network source, ensuring analysts immediately know how fresh the data is before building recommendations.

### 🟥 Out-of-Scope (Explicitly Deferred)
* **Direct Platform API Integration (OAuth):** Building live API pipelines to Meta Ads, Google Ads, or TikTok Manager is completely deferred to preserve simplicity and adhere to the strict constraint of not altering existing workflows in v1.
* **Client-Facing Portals & Access Control:** No external client login systems, white-labeling, multi-tenant permissions, or custom client UI views.
* **Write-Back Automated Optimization:** The system will remain purely read-only for analytical consumption; it will not write back to ad networks to pause campaigns, adjust bids, or shift budgets automatically.

## 5. Definition of a Successful Interaction
A successful interaction occurs when an internal analyst opens the dashboard, selects a specific client brand, and can instantly pinpoint which channel is underperforming (e.g., tracking a sudden spike in cross-channel CPA) within 60 seconds. The analyst walks away knowing exactly where to refocus their strategic attention, completely eliminating the 2–3 hours normally lost to manual file stitching and spreadsheet formatting.

## 6. Data Flow Architecture (v1 Engine)

The diagram below outlines how the v1 tool seamlessly interfaces with the team's existing manual workflows, centralizing the data layer without disrupting current day-to-day operations.

```mermaid
graph TD
    %% Data Sources (Existing Tools)
    subgraph Ad_Platforms [Existing Tools & Workflows]
        A1[Meta Ads Manager] -->|Manual CSV Export| B1[Standardized Format A]
        A2[Google Ads Console] -->|Manual CSV Export| B2[Standardized Format B]
        A3[TikTok Ads Manager] -->|Manual CSV Export| B3[Standardized Format C]
    end

    %% Ingestion Layer
    subgraph Ingestion_Layer [Ingestion & Storage Layer]
        B1 & B2 & B3 -->|Drop Files| C[Central Shared Storage Folder / GCS Bucket]
        C -->|Automated Trigger| D[Processing Engine]
    end

    %% Processing & Core Engine
    subgraph Core_Engine [Data Transformation Engine]
        D -->|Step 1: Parsing| E[Parse Inconsistent Headers & Formats]
        E -->|Step 2: Cleaning| F[Handle Nulls, Currency Mismatches & Typo Resolving]
        F -->|Step 3: Aggregation| G[Calculate Blended Metrics: Spend, CPA, ROAS]
    end

    %% Output View
    subgraph Internal_Delivery [Delivery & Presentation Layer]
        G -->|Store Unified Structure| H[(Internal Data Analytics Tables)]
        H -->|Render Views| I[v1 Performance Dashboard UI]
        I -->|Instant Actionable Insight| J[Internal Marketing Analyst]
    end

    %% Visual Styling
    style Ad_Platforms fill:#f9f9f9,stroke:#333,stroke-width:1px
    style Ingestion_Layer fill:#e1f5fe,stroke:#0288d1,stroke-width:1px
    style Core_Engine fill:#efebe9,stroke:#5d4037,stroke-width:1px
    style Internal_Delivery fill:#e8f5e9,stroke:#388e3c,stroke-width:1px
