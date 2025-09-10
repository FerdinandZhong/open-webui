# SDN Screening System - Architecture

## Search Flow Diagram

```
                        ┌──────────────────────────┐
                        │     USER QUERY INPUT     │
                        │  "John Smith, 1980, USA" │
                        └────────────┬─────────────┘
                                     │
                                     ▼
                        ┌──────────────────────────┐
                        │    QUERY PARSER          │
                        │  • Extract Name          │
                        │  • Extract DOB           │
                        │  • Extract Nationality   │
                        └────────────┬─────────────┘
                                     │
                                     ▼
                        ┌──────────────────────────┐
                        │  1. NAME VARIATIONS      │
                        │     GENERATOR            │
                        │  • John Smith            │
                        │  • Smith, John           │
                        │  • SMITH John            │
                        └────────────┬─────────────┘
                                     │
           ┌─────────────────┬───────┴───────┬─────────────────┐
           ▼                 ▼                ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ 2A. EXACT    │  │ 2B. FUZZY    │  │ 2C. PHONETIC │  │ 2D. ALIAS    │
    │   MATCHING   │  │   MATCHING   │  │   MATCHING   │  │   MATCHING   │
    │ Score: 1.0   │  │ Score: 0.8   │  │ Metaphone    │  │ AKA Lookup   │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                 │                 │                 │
           └─────────────────┴─────────────────┴─────────────────┘
                                      │
                                      ▼
                        ┌──────────────────────────┐
                        │  3. CONTEXT ANALYSIS     │
                        │  • DOB Comparison        │
                        │  • Nationality Check     │
                        │  • Address Matching      │
                        └────────────┬─────────────┘
                                     │
                                     ▼
                        ┌──────────────────────────┐
                        │  4. LLM EVALUATION       │
                        │     (OpenAI GPT-4)       │
                        │  • Confidence Scoring    │
                        │  • Risk Assessment       │
                        └────────────┬─────────────┘
                                     │
                                     ▼
                        ┌──────────────────────────┐
                        │  5. FINAL RANKING        │
                        │  • Combine Scores        │
                        │  • Sort by Relevance     │
                        │  • Apply Thresholds      │
                        └────────────┬─────────────┘
                                     │
                                     ▼
                        ┌──────────────────────────┐
                        │  6. EXPLANATION GEN      │
                        │  • Match Reasons         │
                        │  • Risk Level            │
                        │  • Recommendations       │
                        └────────────┬─────────────┘
                                     │
                                     ▼
                            [JSON Response]
                             • Match Results
                             • Confidence Scores
                             • Explanations
```

## Data Pipeline Architecture

```
                        ┌──────────────────────────┐
                        │    OFAC TREASURY.GOV     │
                        │    SDN XML DATA FILE     │
                        └────────────┬─────────────┘
                                     │
                                     ▼
                        ┌──────────────────────────┐
                        │  1. DOWNLOAD SERVICE     │
                        │     (requests)           │
                        │  • Daily Schedule        │
                        │  • Version Control       │
                        └────────────┬─────────────┘
                                     │
                                     ▼
                        ┌──────────────────────────┐
                        │  2. XML PARSER           │
                        │     (xml.etree)          │
                        │  • Extract Entities      │
                        │  • Parse Aliases         │
                        │  • Get Addresses         │
                        └────────────┬─────────────┘
                                     │
                                     ▼
                        ┌──────────────────────────┐
                        │  3. CSV CONVERTER        │
                        │  • Normalize Data        │
                        │  • Format Fields         │
                        │  • Clean Records         │
                        └────────────┬─────────────┘
                                     │
                                     ▼
                        ┌──────────────────────────┐
                        │  4. DATABASE IMPORT      │
                        │     (SQLite)             │
                        │  • Create Indexes        │
                        │  • Full-Text Search      │
                        └────────────┬─────────────┘
                                     │
                                     ▼
                        ┌──────────────────────────┐
                        │  5. MEMORY CACHE         │
                        │     (pandas DataFrame)   │
                        │  • Load on Startup       │
                        │  • 15,000+ Entries       │
                        └────────────┬─────────────┘
                                     │
           ┌─────────────────────────┴─────────────────────────┐
           ▼                                                   ▼
    ┌──────────────┐                              ┌──────────────┐
    │  FLASK UI    │                              │  FASTAPI     │
    │  Web Interface│                              │  REST API    │
    └──────────────┘                              └──────────────┘
```

## Technology Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND LAYER                          │
├─────────────────┬─────────────────┬─────────────────┬──────────┤
│   HTML5/CSS3    │    JavaScript    │    Bootstrap    │  jQuery  │
└─────────────────┴─────────────────┴─────────────────┴──────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                         API LAYER                               │
├─────────────────┬─────────────────┬─────────────────┬──────────┤
│     FastAPI     │      Flask       │      CORS       │ Uvicorn  │
└─────────────────┴─────────────────┴─────────────────┴──────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                      PROCESSING LAYER                           │
├─────────────────┬─────────────────┬─────────────────┬──────────┤
│   FuzzyWuzzy    │    Metaphone     │   OpenAI API   │  Pandas  │
└─────────────────┴─────────────────┴─────────────────┴──────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                              │
├─────────────────┬─────────────────┬─────────────────┬──────────┤
│     SQLite      │    CSV Files     │   XML Parser    │  Cache   │
└─────────────────┴─────────────────┴─────────────────┴──────────┘
```

## Search Process

### Input
```
"Vladimir Putin, 1952, Russian"
```

### Processing Steps
```
1. Parse Query
   ├── Name: "Vladimir Putin"
   ├── DOB: 1952
   └── Nationality: Russian

2. Name Matching
   ├── Generate: ["Vladimir Putin", "Putin Vladimir", "PUTIN, Vladimir"]
   ├── Search: 15,000+ SDN entries
   └── Find: 3 potential matches

3. Context Ranking
   ├── Check DOB match
   ├── Verify nationality
   └── LLM confidence score

4. Output
   └── Match #12345: Vladimir Vladimirovich PUTIN
       ├── Score: 0.98
       ├── Confidence: HIGH
       └── Explanation: "Exact name match, DOB and nationality confirmed"
```

## Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **Data Pipeline** | Downloads & processes OFAC data | `data_list/pipeline.py` |
| **Name Matcher** | Finds potential matches | `sdn_api/core/name_matcher.py` |
| **Ranker** | Scores based on context | `sdn_api/core/ranker.py` |
| **LLM Service** | AI-powered analysis | `sdn_api/core/llm_service.py` |
| **API** | REST endpoints | `sdn_api/api/main.py` |
| **Web UI** | User interface | `flask_ui/` |