# ACMS Views UX Test Suite

**Version:** 1.0
**Date:** February 6, 2026
**QA Engineer:** UX Testing Specialist
**Total Test Cases:** 127

---

## Table of Contents

1. [Overview](#overview)
2. [Test Environment](#test-environment)
3. [View 1: Memories View](#view-1-memories-view)
4. [View 2: Knowledge View](#view-2-knowledge-view)
5. [View 3: Financial View](#view-3-financial-view)
6. [View 4: Reports/Insights View](#view-4-reportsinsights-view)
7. [View 5: Data Flow View](#view-5-data-flow-view)
8. [Cross-View Navigation Tests](#cross-view-navigation-tests)
9. [Active Second Brain Components](#active-second-brain-components)
10. [Complete Test Suite Summary](#complete-test-suite-summary)
11. [Priority Rankings](#priority-rankings)
12. [Automation Recommendations](#automation-recommendations)
13. [Manual Testing Requirements](#manual-testing-requirements)

---

## Overview

This document contains comprehensive UX test scenarios for the redesigned ACMS desktop application views. Each view has been analyzed through 10 iterations of increasing rigor:

| Iteration | Focus Area |
|-----------|------------|
| 1-2 | Basic functionality (loading, display) |
| 3-4 | User flows (task accomplishment) |
| 5-6 | Edge cases (empty states, errors, large data) |
| 7-8 | Accessibility (keyboard nav, screen readers) |
| 9-10 | Performance and delight (animations, responsiveness) |

---

## Test Environment

**Application:** ACMS Desktop App (Electron)
**Backend:** FastAPI on port 40080
**Databases:** PostgreSQL (40432), Weaviate (40480), Redis (40379)
**Test Data Requirements:**
- Minimum 100 memory items across privacy levels
- 50+ knowledge items with varying confidence scores
- Connected Plaid sandbox account (for Financial view)
- Generated reports history (5+ reports)

---

## View 1: Memories View

### Iteration 1-2: Basic Functionality

#### MEM-001: View Loads Successfully
- **Test ID:** MEM-001
- **User Story:** As a user, I want the Memories view to load so I can see my stored memories
- **Preconditions:** User is logged in, API is running
- **Steps:**
  1. Click "Memories" in sidebar navigation
  2. Wait for view to render
- **Expected Result:** View displays with header "Memory Browser", stats section, and memory list
- **Acceptance Criteria:**
  - Header displays within 500ms
  - Stats section shows loading state then populates
  - Memory list displays items or empty state
- **Priority:** P0

#### MEM-002: Statistics Display Correctly
- **Test ID:** MEM-002
- **User Story:** As a user, I want to see memory statistics to understand my data
- **Preconditions:** At least 10 memories exist in the system
- **Steps:**
  1. Navigate to Memories view
  2. Observe stats section
- **Expected Result:**
  - Total Memories count displays correctly
  - Privacy level breakdown shows (PUBLIC, INTERNAL, CONFIDENTIAL, LOCAL_ONLY)
  - Tier breakdown shows (CORE, ACTIVE, ARCHIVE)
  - Source breakdown displays top sources
- **Acceptance Criteria:** Stats match actual database counts within 5% tolerance
- **Priority:** P0

#### MEM-003: Memory Cards Render Properly
- **Test ID:** MEM-003
- **User Story:** As a user, I want to see memory cards with relevant information
- **Preconditions:** Memories exist with varied data
- **Steps:**
  1. Navigate to Memories view
  2. Observe memory card content
- **Expected Result:** Each card shows:
  - Privacy level badge with appropriate color
  - Tier badge
  - CRS score (if available)
  - Content preview (truncated to 300 chars)
  - Tags (up to 5)
  - Created date
  - Truncated ID with tooltip
- **Acceptance Criteria:** All fields render without visual overflow
- **Priority:** P0

### Iteration 3-4: User Flows

#### MEM-004: Filter by Privacy Level
- **Test ID:** MEM-004
- **User Story:** As a user, I want to filter memories by privacy level
- **Preconditions:** Memories exist with different privacy levels
- **Steps:**
  1. Navigate to Memories view
  2. Select "CONFIDENTIAL" from privacy dropdown
  3. Observe filtered results
- **Expected Result:** Only CONFIDENTIAL memories display
- **Acceptance Criteria:**
  - Filter applies within 500ms
  - Count updates to reflect filtered set
  - No non-CONFIDENTIAL items appear
- **Priority:** P1

#### MEM-005: Filter by Tier
- **Test ID:** MEM-005
- **User Story:** As a user, I want to filter memories by storage tier
- **Preconditions:** Memories exist across tiers
- **Steps:**
  1. Navigate to Memories view
  2. Select "CORE" from tier dropdown
- **Expected Result:** Only CORE tier memories display
- **Acceptance Criteria:** Filter correctly isolates tier
- **Priority:** P1

#### MEM-006: Search Memories
- **Test ID:** MEM-006
- **User Story:** As a user, I want to search memories by content or tags
- **Preconditions:** Memories exist with searchable content
- **Steps:**
  1. Navigate to Memories view
  2. Enter "python" in search box
  3. Wait for debounce (300ms)
- **Expected Result:** Only memories containing "python" in content or tags display
- **Acceptance Criteria:**
  - Debounce prevents excessive API calls
  - Case-insensitive matching
  - Results update without page reload
- **Priority:** P1

#### MEM-007: Combined Filters
- **Test ID:** MEM-007
- **User Story:** As a user, I want to combine multiple filters
- **Preconditions:** Varied memory data exists
- **Steps:**
  1. Select "INTERNAL" privacy
  2. Select "ACTIVE" tier
  3. Search for "docker"
- **Expected Result:** Results match ALL filter criteria
- **Acceptance Criteria:** AND logic applied to all filters
- **Priority:** P1

#### MEM-008: Refresh Memories
- **Test ID:** MEM-008
- **User Story:** As a user, I want to refresh the memory list
- **Preconditions:** View is loaded with data
- **Steps:**
  1. Click "Refresh" button
- **Expected Result:**
  - Loading indicator appears
  - Fresh data loads
  - Current filters preserved
- **Acceptance Criteria:** Refresh completes within 2 seconds
- **Priority:** P2

### Iteration 5-6: Edge Cases

#### MEM-009: Empty State Display
- **Test ID:** MEM-009
- **User Story:** As a user, I want to see a helpful message when no memories exist
- **Preconditions:** No memories in database
- **Steps:**
  1. Navigate to Memories view
- **Expected Result:** "No memories found" message displays
- **Acceptance Criteria:** Message is helpful, not just "No data"
- **Priority:** P2

#### MEM-010: No Results After Filter
- **Test ID:** MEM-010
- **User Story:** As a user, I want feedback when filters return no results
- **Preconditions:** Memories exist but not matching filters
- **Steps:**
  1. Apply filters that match no memories
- **Expected Result:** "No memories found" with suggestion to adjust filters
- **Acceptance Criteria:** Clear guidance on why no results
- **Priority:** P2

#### MEM-011: API Error Handling
- **Test ID:** MEM-011
- **User Story:** As a user, I want to see error messages when API fails
- **Preconditions:** API is unavailable or returns error
- **Steps:**
  1. Stop API service
  2. Navigate to Memories view
- **Expected Result:** Error message "Failed to load stats/memories: [error]"
- **Acceptance Criteria:** Error message is user-friendly, includes error detail
- **Priority:** P1

#### MEM-012: Large Dataset Performance
- **Test ID:** MEM-012
- **User Story:** As a user, I want the view to remain responsive with large data
- **Preconditions:** 10,000+ memories in database
- **Steps:**
  1. Navigate to Memories view
  2. Scroll through list
  3. Apply filters
- **Expected Result:**
  - Initial load completes within 3 seconds
  - Scrolling is smooth (60fps)
  - Filters apply within 1 second
- **Acceptance Criteria:** No UI freezing or jank
- **Priority:** P1

#### MEM-013: Very Long Content Handling
- **Test ID:** MEM-013
- **User Story:** As a user, I want long content to be properly truncated
- **Preconditions:** Memory with 5000+ character content
- **Steps:**
  1. View memory card with long content
- **Expected Result:** Content truncated to 300 chars with "..."
- **Acceptance Criteria:** No text overflow, ellipsis visible
- **Priority:** P2

#### MEM-014: Special Characters in Content
- **Test ID:** MEM-014
- **User Story:** As a user, I want special characters to display correctly
- **Preconditions:** Memory with HTML entities, unicode, emoji
- **Steps:**
  1. View memory with content like "<script>alert('xss')</script>"
- **Expected Result:** Characters escaped and displayed as text, not executed
- **Acceptance Criteria:** XSS prevention, proper escaping
- **Priority:** P0 (Security)

### Iteration 7-8: Accessibility

#### MEM-015: Keyboard Navigation - Filters
- **Test ID:** MEM-015
- **User Story:** As a keyboard user, I want to navigate filters without mouse
- **Preconditions:** View loaded
- **Steps:**
  1. Tab to privacy filter
  2. Use arrow keys to change selection
  3. Tab to tier filter
  4. Tab to search input
- **Expected Result:** All controls reachable and operable via keyboard
- **Acceptance Criteria:**
  - Tab order is logical (left to right)
  - Focus indicators visible
  - Enter/Space activates controls
- **Priority:** P2

#### MEM-016: Screen Reader Announcements
- **Test ID:** MEM-016
- **User Story:** As a screen reader user, I want view content announced
- **Preconditions:** Screen reader active (VoiceOver on Mac)
- **Steps:**
  1. Navigate to Memories view
  2. Listen to announcements
- **Expected Result:**
  - Page title announced
  - Stats announced with labels
  - Memory cards have accessible content
- **Acceptance Criteria:** ARIA labels present on interactive elements
- **Priority:** P2

#### MEM-017: Focus Management
- **Test ID:** MEM-017
- **User Story:** As a user, I want focus to be managed appropriately
- **Preconditions:** View loaded
- **Steps:**
  1. Apply a filter
  2. Observe focus state
- **Expected Result:** Focus returns to logical position after filter
- **Acceptance Criteria:** No focus trap, no lost focus
- **Priority:** P2

#### MEM-018: Color Contrast
- **Test ID:** MEM-018
- **User Story:** As a user with vision impairment, I want readable text
- **Preconditions:** View loaded
- **Steps:**
  1. Inspect text/background contrast ratios
- **Expected Result:** All text meets WCAG AA (4.5:1 for normal text)
- **Acceptance Criteria:** Run automated contrast checker
- **Priority:** P2

### Iteration 9-10: Performance and Delight

#### MEM-019: Loading Skeleton Animation
- **Test ID:** MEM-019
- **User Story:** As a user, I want visual feedback while data loads
- **Preconditions:** Simulate slow network
- **Steps:**
  1. Navigate to Memories view
  2. Observe loading state
- **Expected Result:** Skeleton animation or spinner visible during load
- **Acceptance Criteria:** Loading state appears within 100ms
- **Priority:** P3

#### MEM-020: Smooth Filter Transitions
- **Test ID:** MEM-020
- **User Story:** As a user, I want smooth visual transitions when filtering
- **Preconditions:** View loaded with data
- **Steps:**
  1. Apply filter
  2. Observe transition
- **Expected Result:** Cards fade/animate out, new cards animate in
- **Acceptance Criteria:** No jarring jumps, smooth reflow
- **Priority:** P3

#### MEM-021: Responsive Layout
- **Test ID:** MEM-021
- **User Story:** As a user, I want the view to adapt to window size
- **Preconditions:** View loaded
- **Steps:**
  1. Resize window to 800px width
  2. Resize to 1200px width
  3. Resize to 1920px width
- **Expected Result:**
  - Cards reflow appropriately
  - No horizontal scrolling at any size
  - Stats grid adjusts
- **Acceptance Criteria:** Minimum supported width: 768px
- **Priority:** P2

---

## View 2: Knowledge View

### Iteration 1-2: Basic Functionality

#### KNO-001: View Loads Successfully
- **Test ID:** KNO-001
- **User Story:** As a user, I want the Knowledge Base view to load
- **Preconditions:** User logged in, knowledge items exist
- **Steps:**
  1. Click "Knowledge" in sidebar
- **Expected Result:**
  - Header "Knowledge Base" displays
  - Tab navigation shows (All Knowledge, Needs Review, Verified)
  - Stats section populates
  - Knowledge list renders
- **Acceptance Criteria:** Full view renders within 2 seconds
- **Priority:** P0

#### KNO-002: Knowledge Stats Display
- **Test ID:** KNO-002
- **User Story:** As a user, I want to see knowledge statistics
- **Preconditions:** Knowledge items exist
- **Steps:**
  1. Navigate to Knowledge view
  2. Observe stats
- **Expected Result:**
  - Total Knowledge count
  - Total Facts count
  - Top Topics list
  - Top Domains list
- **Acceptance Criteria:** Stats accurate to database
- **Priority:** P0

#### KNO-003: Knowledge Cards Render
- **Test ID:** KNO-003
- **User Story:** As a user, I want to see knowledge cards with details
- **Preconditions:** Knowledge items exist
- **Steps:**
  1. Navigate to Knowledge view
  2. Inspect card content
- **Expected Result:** Each card shows:
  - Topic cluster badge
  - Problem domain badge
  - Extraction confidence percentage
  - Canonical query
  - Primary intent
  - Answer summary (truncated)
  - Key facts (up to 3)
  - Related topics (up to 5)
  - Created date and ID
- **Acceptance Criteria:** All fields render correctly
- **Priority:** P0

### Iteration 3-4: User Flows

#### KNO-004: Tab Switching - All Knowledge
- **Test ID:** KNO-004
- **User Story:** As a user, I want to view all knowledge items
- **Preconditions:** Multiple knowledge items exist
- **Steps:**
  1. Click "All Knowledge" tab
- **Expected Result:** All knowledge items display unfiltered
- **Acceptance Criteria:** Tab shows active state, list updates
- **Priority:** P1

#### KNO-005: Tab Switching - Needs Review
- **Test ID:** KNO-005
- **User Story:** As a user, I want to see items needing review (Active Second Brain)
- **Preconditions:** Knowledge with low confidence exists
- **Steps:**
  1. Click "Needs Review" tab
- **Expected Result:**
  - Only low-confidence, unverified items show
  - Edit and Verify buttons visible on each card
  - Confidence indicator displayed
- **Acceptance Criteria:** Review queue loads from /api/knowledge/review
- **Priority:** P0 (Active Second Brain)

#### KNO-006: Tab Switching - Verified
- **Test ID:** KNO-006
- **User Story:** As a user, I want to see verified knowledge
- **Preconditions:** Verified knowledge exists
- **Steps:**
  1. Click "Verified" tab
- **Expected Result:** Only user-verified knowledge displays
- **Acceptance Criteria:** verified=true filter applied
- **Priority:** P1

#### KNO-007: Filter by Domain
- **Test ID:** KNO-007
- **User Story:** As a user, I want to filter knowledge by domain
- **Preconditions:** Knowledge across domains exists
- **Steps:**
  1. Select domain from dropdown
- **Expected Result:** Only items in selected domain display
- **Acceptance Criteria:** Domain filter applies correctly
- **Priority:** P1

#### KNO-008: Filter by Topic
- **Test ID:** KNO-008
- **User Story:** As a user, I want to filter knowledge by topic
- **Preconditions:** Knowledge with topics exists
- **Steps:**
  1. Select topic from dropdown
- **Expected Result:** Only items with selected topic display
- **Acceptance Criteria:** Topic filter applies correctly
- **Priority:** P1

#### KNO-009: Search Knowledge
- **Test ID:** KNO-009
- **User Story:** As a user, I want to search knowledge content
- **Preconditions:** Knowledge exists
- **Steps:**
  1. Enter search term in search box
  2. Wait for debounce
- **Expected Result:** Results filtered by search term
- **Acceptance Criteria:** Search applies with 300ms debounce
- **Priority:** P1

#### KNO-010: Click to View Full Article
- **Test ID:** KNO-010
- **User Story:** As a user, I want to view full knowledge details
- **Preconditions:** Knowledge item exists
- **Steps:**
  1. Click on a knowledge card
- **Expected Result:** Modal opens with full article:
  - All badges (domain, topic, intent, confidence)
  - Full canonical query as title
  - Complete answer summary
  - Why context (if available)
  - All key facts
  - Entities
  - Related topics
  - Source queries
  - Metadata (ID, created, usage count, feedback score, model)
- **Acceptance Criteria:** Modal fetches from /knowledge/{id}
- **Priority:** P1

#### KNO-011: Close Knowledge Modal
- **Test ID:** KNO-011
- **User Story:** As a user, I want to close the knowledge modal
- **Preconditions:** Modal is open
- **Steps:**
  1. Click X button OR click overlay OR press Escape
- **Expected Result:** Modal closes, returns to list view
- **Acceptance Criteria:** All close methods work
- **Priority:** P1

### Iteration 5-6: Edge Cases (Active Second Brain)

#### KNO-012: Verify Knowledge Action
- **Test ID:** KNO-012
- **User Story:** As a user, I want to verify knowledge without editing (AC for Active Second Brain)
- **Preconditions:** Low-confidence item in review queue
- **Steps:**
  1. Go to "Needs Review" tab
  2. Click "Verify" button on a card
- **Expected Result:**
  - API call to /api/knowledge/verify
  - Success toast: "Knowledge verified!"
  - Item removed from review queue
  - Item appears in Verified tab
- **Acceptance Criteria:** POST /api/knowledge/verify with knowledge_id
- **Priority:** P0 (Active Second Brain)

#### KNO-013: Edit Knowledge - Show Correction Modal
- **Test ID:** KNO-013
- **User Story:** As a user, I want to correct inaccurate knowledge
- **Preconditions:** Knowledge item exists
- **Steps:**
  1. Click "Edit" button on knowledge card
- **Expected Result:** Correction modal opens with:
  - Current content displayed (read-only)
  - Corrected content textarea (pre-filled)
  - Correction type dropdown
  - Reason input (optional)
  - Cancel and Save buttons
- **Acceptance Criteria:** Modal renders correctly
- **Priority:** P0 (Active Second Brain)

#### KNO-014: Submit Knowledge Correction
- **Test ID:** KNO-014
- **User Story:** As a user, I want to save my knowledge correction
- **Preconditions:** Correction modal is open
- **Steps:**
  1. Modify content in textarea
  2. Select correction type "Factual Error"
  3. Optionally add reason
  4. Click "Save Correction"
- **Expected Result:**
  - API call to /api/knowledge/correct
  - Success toast: "Correction saved!"
  - Modal closes
  - List refreshes
- **Acceptance Criteria:** POST with knowledge_id, corrected_content, correction_type, reason
- **Priority:** P0 (Active Second Brain)

#### KNO-015: Correction Validation - Empty Content
- **Test ID:** KNO-015
- **User Story:** As a user, I want validation when submitting empty correction
- **Preconditions:** Correction modal open
- **Steps:**
  1. Clear the corrected content textarea
  2. Click "Save Correction"
- **Expected Result:** Error toast: "Please enter corrected content"
- **Acceptance Criteria:** Client-side validation prevents empty submit
- **Priority:** P1

#### KNO-016: Empty Review Queue
- **Test ID:** KNO-016
- **User Story:** As a user, I want positive feedback when no items need review
- **Preconditions:** All knowledge verified or high confidence
- **Steps:**
  1. Go to "Needs Review" tab
- **Expected Result:** Message: "No items need review! All knowledge has been verified or has high confidence."
- **Acceptance Criteria:** Celebratory empty state
- **Priority:** P2

#### KNO-017: Cross-View Navigation from Insights
- **Test ID:** KNO-017
- **User Story:** As a user, I want to navigate to Knowledge filtered by domain from Insights
- **Preconditions:** Insights view shows expertise centers
- **Steps:**
  1. Go to Insights view
  2. Click on an expertise center card (e.g., "Python")
- **Expected Result:**
  - View switches to Knowledge
  - Domain filter pre-set to clicked domain
  - Filter badge shows "Showing knowledge in domain: Python"
  - Clear filter button available
- **Acceptance Criteria:** navigateToKnowledgeWithFilter({ domain: 'Python' }) called
- **Priority:** P2

### Iteration 7-8: Accessibility

#### KNO-018: Keyboard Navigation - Tabs
- **Test ID:** KNO-018
- **User Story:** As a keyboard user, I want to navigate tabs
- **Preconditions:** View loaded
- **Steps:**
  1. Tab to tab buttons
  2. Use arrow keys or Enter to switch tabs
- **Expected Result:** Tabs navigable and activatable via keyboard
- **Acceptance Criteria:** Focus visible, tab role announced
- **Priority:** P2

#### KNO-019: Modal Focus Trap
- **Test ID:** KNO-019
- **User Story:** As a user, I want focus trapped in open modal
- **Preconditions:** Knowledge modal open
- **Steps:**
  1. Tab through modal elements
  2. Continue tabbing past last element
- **Expected Result:** Focus cycles within modal, does not escape to background
- **Acceptance Criteria:** Focus returns to first focusable element
- **Priority:** P2

#### KNO-020: Screen Reader - Card Content
- **Test ID:** KNO-020
- **User Story:** As a screen reader user, I want card content announced
- **Preconditions:** Screen reader active
- **Steps:**
  1. Navigate to knowledge card
- **Expected Result:** Topic, domain, confidence, query, and summary announced
- **Acceptance Criteria:** Semantic HTML or ARIA labels present
- **Priority:** P2

### Iteration 9-10: Performance and Delight

#### KNO-021: Confidence Score Visual Indicator
- **Test ID:** KNO-021
- **User Story:** As a user, I want visual indication of confidence levels
- **Preconditions:** Items with varying confidence
- **Steps:**
  1. View cards with different confidence scores
- **Expected Result:**
  - High confidence (>80%) shown in green
  - Medium (50-80%) in yellow
  - Low (<50%) in red
- **Acceptance Criteria:** Color coding matches confidence thresholds
- **Priority:** P3

#### KNO-022: Modal Animation
- **Test ID:** KNO-022
- **User Story:** As a user, I want smooth modal open/close
- **Preconditions:** Click knowledge card
- **Steps:**
  1. Click card to open modal
  2. Close modal
- **Expected Result:** Fade-in on open, fade-out on close
- **Acceptance Criteria:** Animation duration ~200ms
- **Priority:** P3

---

## View 3: Financial View

### Iteration 1-2: Basic Functionality

#### FIN-001: View Loads - No Account Connected
- **Test ID:** FIN-001
- **User Story:** As a new user, I want to see setup instructions
- **Preconditions:** No Plaid account connected
- **Steps:**
  1. Click "Financial" in sidebar
- **Expected Result:** Setup card displays with:
  - Icon and "Connect Your Investment Accounts" heading
  - Description of features
  - Security badge (Plaid)
  - Portfolio tracking feature
  - AI insights feature
  - Sandbox notice (if in sandbox mode)
  - "Connect Account" button
  - Supported institutions list
- **Acceptance Criteria:** Setup card renders, button functional
- **Priority:** P0

#### FIN-002: View Loads - Account Connected
- **Test ID:** FIN-002
- **User Story:** As a user with connected account, I want to see my portfolio
- **Preconditions:** Plaid account connected, holdings synced
- **Steps:**
  1. Click "Financial" in sidebar
- **Expected Result:** Portfolio Dashboard displays with:
  - Header showing institution count
  - Sync All and Add Account buttons
  - Tab navigation (Holdings, Constitution, Accounts, Transactions)
  - Holdings tab loaded by default
- **Acceptance Criteria:** Dashboard renders with data
- **Priority:** P0

#### FIN-003: Holdings Tab Display
- **Test ID:** FIN-003
- **User Story:** As a user, I want to see my portfolio holdings
- **Preconditions:** Holdings data exists
- **Steps:**
  1. View Holdings tab (default)
- **Expected Result:**
  - Portfolio summary: Total Value, Cost Basis, Total Gain/Loss, Position count
  - Holdings table with columns: Symbol, Name, Shares, Price, Value, Gain/Loss, % Portfolio
  - Gain/loss colored (green positive, red negative)
- **Acceptance Criteria:** Values calculate correctly, formatting proper
- **Priority:** P0

### Iteration 3-4: User Flows

#### FIN-004: Initiate Plaid Link
- **Test ID:** FIN-004
- **User Story:** As a user, I want to connect a new account via Plaid
- **Preconditions:** Setup card visible OR Add Account button visible
- **Steps:**
  1. Click "Connect Account" button
- **Expected Result:** Plaid Link modal opens (Plaid SDK)
- **Acceptance Criteria:** initiatePlaidLink() called
- **Priority:** P0

#### FIN-005: Switch to Constitution Tab
- **Test ID:** FIN-005
- **User Story:** As a user, I want to view my investment rules
- **Preconditions:** Account connected
- **Steps:**
  1. Click "Constitution" tab
- **Expected Result:** Constitution rules view loads with:
  - Advisor dashboard with health score
  - Health score ring visualization
  - Advisor commentary
  - Quick actions (if applicable)
  - Principles sections
- **Acceptance Criteria:** Rules evaluated against current holdings
- **Priority:** P1

#### FIN-006: Switch to Accounts Tab
- **Test ID:** FIN-006
- **User Story:** As a user, I want to see my connected accounts
- **Preconditions:** Institutions connected
- **Steps:**
  1. Click "Accounts" tab
- **Expected Result:** Account cards grid showing:
  - Institution name
  - Account details (name, type, balance)
  - Connection status
- **Acceptance Criteria:** All connected accounts display
- **Priority:** P1

#### FIN-007: Switch to Transactions Tab
- **Test ID:** FIN-007
- **User Story:** As a user, I want to see transaction history
- **Preconditions:** Transactions synced
- **Steps:**
  1. Click "Transactions" tab
- **Expected Result:** Transactions table with:
  - Date, Type, Symbol, Shares, Amount, Account
  - Buy/Sell type coloring
  - Last 50 transactions
- **Acceptance Criteria:** Transactions display in date order
- **Priority:** P1

#### FIN-008: Sync All Accounts
- **Test ID:** FIN-008
- **User Story:** As a user, I want to refresh all account data
- **Preconditions:** Accounts connected
- **Steps:**
  1. Click "Sync All" button
- **Expected Result:**
  - Sync status indicator appears
  - Data refreshes from Plaid
  - Current tab reloads with new data
- **Acceptance Criteria:** syncAllAccounts() executes successfully
- **Priority:** P1

### Iteration 5-6: Edge Cases

#### FIN-009: Empty Holdings State
- **Test ID:** FIN-009
- **User Story:** As a user, I want guidance when no holdings data exists
- **Preconditions:** Account connected but no holdings synced
- **Steps:**
  1. View Holdings tab
- **Expected Result:** "No Holdings Data - Click 'Sync All' to fetch your portfolio data"
- **Acceptance Criteria:** Helpful empty state with action
- **Priority:** P2

#### FIN-010: Empty Transactions State
- **Test ID:** FIN-010
- **User Story:** As a user, I want guidance when no transactions exist
- **Preconditions:** Account connected, no transactions
- **Steps:**
  1. View Transactions tab
- **Expected Result:** "No Transaction History - Click 'Sync All' to fetch"
- **Acceptance Criteria:** Helpful empty state
- **Priority:** P2

#### FIN-011: API Error - Plaid Status
- **Test ID:** FIN-011
- **User Story:** As a user, I want error handling when Plaid API fails
- **Preconditions:** Plaid API unavailable
- **Steps:**
  1. Navigate to Financial view
- **Expected Result:** Error state with:
  - "Unable to Load Financial Status"
  - Error message
  - Retry button
- **Acceptance Criteria:** Graceful error handling
- **Priority:** P1

#### FIN-012: Holdings Tab Load Error
- **Test ID:** FIN-012
- **User Story:** As a user, I want error feedback on tab load failure
- **Preconditions:** Holdings API fails
- **Steps:**
  1. Click Holdings tab
- **Expected Result:** "Failed to load holdings. Try syncing first."
- **Acceptance Criteria:** Tab-specific error message
- **Priority:** P2

#### FIN-013: Constitution Rules - No Holdings Data
- **Test ID:** FIN-013
- **User Story:** As a user, I want constitution to work without holdings
- **Preconditions:** No holdings synced
- **Steps:**
  1. Click Constitution tab
- **Expected Result:** Rules display with "No data" or N/A for metrics that require holdings
- **Acceptance Criteria:** No crash, graceful degradation
- **Priority:** P2

### Iteration 7-8: Accessibility

#### FIN-014: Keyboard Navigation - Tabs
- **Test ID:** FIN-014
- **User Story:** As a keyboard user, I want to switch portfolio tabs
- **Preconditions:** Dashboard loaded
- **Steps:**
  1. Tab to tab buttons
  2. Press Enter/Space to activate
- **Expected Result:** Tabs switchable via keyboard
- **Acceptance Criteria:** Focus visible, correct tab panel shown
- **Priority:** P2

#### FIN-015: Screen Reader - Holdings Table
- **Test ID:** FIN-015
- **User Story:** As a screen reader user, I want holdings table announced
- **Preconditions:** Holdings tab active
- **Steps:**
  1. Navigate table with screen reader
- **Expected Result:** Column headers and cell values announced
- **Acceptance Criteria:** Table has proper headers/scope
- **Priority:** P2

#### FIN-016: Color Independence - Gain/Loss
- **Test ID:** FIN-016
- **User Story:** As a colorblind user, I want gain/loss indicated beyond color
- **Preconditions:** Holdings with gains and losses
- **Steps:**
  1. View gain/loss column
- **Expected Result:**
  - Positive values have + sign
  - Negative values have - sign
  - Not reliant solely on color
- **Acceptance Criteria:** Text indicators present
- **Priority:** P2

### Iteration 9-10: Performance and Delight

#### FIN-017: Health Score Animation
- **Test ID:** FIN-017
- **User Story:** As a user, I want engaging health score display
- **Preconditions:** Constitution tab active
- **Steps:**
  1. View health score ring
- **Expected Result:**
  - Ring fills to score percentage
  - Color reflects health level (excellent/good/fair/poor)
  - Animated fill on load
- **Acceptance Criteria:** CSS animation smooth
- **Priority:** P3

#### FIN-018: Currency Formatting
- **Test ID:** FIN-018
- **User Story:** As a user, I want proper currency display
- **Preconditions:** Holdings with various values
- **Steps:**
  1. View dollar amounts
- **Expected Result:**
  - Proper comma separation (1,234,567.89)
  - $ symbol prefix
  - 2 decimal places
- **Acceptance Criteria:** formatCurrency() applied consistently
- **Priority:** P2

---

## View 4: Reports/Insights View

### Iteration 1-2: Basic Functionality

#### REP-001: Reports View Loads
- **Test ID:** REP-001
- **User Story:** As a user, I want the Reports view to load
- **Preconditions:** User logged in
- **Steps:**
  1. Click "Reports" in sidebar
- **Expected Result:**
  - Header with icon and "Intelligence Reports"
  - Generate section with form (type, scope, format)
  - Generate Report button
  - Report History section
- **Acceptance Criteria:** View renders completely
- **Priority:** P0

#### REP-002: Report History Loads
- **Test ID:** REP-002
- **User Story:** As a user, I want to see my previous reports
- **Preconditions:** Reports exist in database
- **Steps:**
  1. Navigate to Reports view
  2. Observe Report History section
- **Expected Result:**
  - Grid of report cards
  - Each card shows: type badge, date, title, period, preview stats, View button
- **Acceptance Criteria:** Cards load from /api/v2/reports
- **Priority:** P0

#### INS-001: Insights View Loads
- **Test ID:** INS-001
- **User Story:** As a user, I want the Insights view to load
- **Preconditions:** User logged in
- **Steps:**
  1. Click "Insights" in sidebar
- **Expected Result:**
  - Header "Insights Dashboard"
  - Analysis input field
  - Period selector and Generate Insights button
  - Dashboard content
- **Acceptance Criteria:** View renders
- **Priority:** P0

#### INS-002: Knowledge Intelligence Loads
- **Test ID:** INS-002
- **User Story:** As a user, I want to see knowledge-powered insights
- **Preconditions:** Knowledge base has data
- **Steps:**
  1. Navigate to Insights view
- **Expected Result:** Dashboard shows:
  - Executive Summary with headline
  - Knowledge Velocity stats
  - Expertise Centers (clickable cards)
  - Attention Signals (deep/growing/needs attention)
  - Key Facts by Domain
  - Recommendations
- **Acceptance Criteria:** Data from /api/v2/insights/knowledge
- **Priority:** P0

### Iteration 3-4: User Flows

#### REP-003: Generate Weekly Report
- **Test ID:** REP-003
- **User Story:** As a user, I want to generate a weekly report
- **Preconditions:** Query history exists
- **Steps:**
  1. Select "Weekly Summary" type
  2. Select "Personal" scope
  3. Select "View Online" format
  4. Click "Generate Report"
- **Expected Result:**
  - Loading animation with "Generating Your Report"
  - Report display appears with:
    - Hero header with badge and headline
    - Hero stats (queries, topics, knowledge, facts, cost)
    - Top Topics chart
    - Agent Usage donut chart
    - Key Insights
    - Recommendations
  - Report added to history
- **Acceptance Criteria:** POST /api/v2/reports/generate, renders JSON
- **Priority:** P0

#### REP-004: Generate Markdown Report
- **Test ID:** REP-004
- **User Story:** As a user, I want to download a markdown report
- **Preconditions:** Report form visible
- **Steps:**
  1. Select "Markdown" format
  2. Click "Generate Report"
- **Expected Result:**
  - File download triggers
  - File named acms-report-YYYY-MM-DD.md
  - Success message displays
- **Acceptance Criteria:** Blob download works
- **Priority:** P1

#### REP-005: View Historical Report
- **Test ID:** REP-005
- **User Story:** As a user, I want to view a previously generated report
- **Preconditions:** Reports exist in history
- **Steps:**
  1. Click "View Full Report" on a history card
- **Expected Result:**
  - Loading indicator
  - Report display renders with full content
- **Acceptance Criteria:** GET /api/v2/reports/{id}
- **Priority:** P1

#### REP-006: Close Report Display
- **Test ID:** REP-006
- **User Story:** As a user, I want to close the report display
- **Preconditions:** Report display open
- **Steps:**
  1. Click X button
- **Expected Result:** Report display hides
- **Acceptance Criteria:** .hidden class applied
- **Priority:** P2

#### INS-003: Change Insights Period
- **Test ID:** INS-003
- **User Story:** As a user, I want to view insights for different periods
- **Preconditions:** Insights view loaded
- **Steps:**
  1. Select "Last 30 days" from period dropdown
- **Expected Result:** Dashboard reloads with 30-day data
- **Acceptance Criteria:** period_days=30 passed to API
- **Priority:** P1

#### INS-004: Generate Insights On Demand
- **Test ID:** INS-004
- **User Story:** As a user, I want to trigger fresh insight generation
- **Preconditions:** Insights view loaded
- **Steps:**
  1. Click "Generate Insights" button
- **Expected Result:**
  - Button shows "Generating..."
  - Success message: "Insights Generated! X insights from Y topics"
  - Dashboard refreshes
- **Acceptance Criteria:** POST /api/v2/insights/generate
- **Priority:** P1

#### INS-005: Perform Topic Analysis
- **Test ID:** INS-005
- **User Story:** As a user, I want to analyze a specific topic
- **Preconditions:** Insights view loaded
- **Steps:**
  1. Enter "What have I learned about Docker?" in analysis input
  2. Click "Analyze" or press Enter
- **Expected Result:** Analysis results section shows:
  - Topic heading with confidence
  - Analysis text
  - Key learnings list
  - Knowledge gaps (if any)
  - Related topics
- **Acceptance Criteria:** POST /api/v2/insights/analyze
- **Priority:** P1

#### INS-006: Click Expertise Center to Navigate
- **Test ID:** INS-006
- **User Story:** As a user, I want to drill into expertise domains
- **Preconditions:** Expertise centers displayed
- **Steps:**
  1. Click on an expertise center card
- **Expected Result:**
  - View switches to Knowledge
  - Domain filter pre-applied
- **Acceptance Criteria:** navigateToKnowledgeWithFilter called
- **Priority:** P2

### Iteration 5-6: Edge Cases

#### REP-007: Empty Report History
- **Test ID:** REP-007
- **User Story:** As a user, I want guidance when no reports exist
- **Preconditions:** No reports generated
- **Steps:**
  1. Navigate to Reports view
- **Expected Result:** Empty state with:
  - Icon
  - "No Reports Yet" heading
  - Guidance text
- **Acceptance Criteria:** Helpful empty state
- **Priority:** P2

#### REP-008: Report Generation Failure
- **Test ID:** REP-008
- **User Story:** As a user, I want error handling on generation failure
- **Preconditions:** API error simulated
- **Steps:**
  1. Click Generate Report
- **Expected Result:**
  - Error display with icon
  - "Generation Failed" message
  - Error detail
  - Close button
- **Acceptance Criteria:** Graceful error display
- **Priority:** P1

#### INS-007: No Insights Available
- **Test ID:** INS-007
- **User Story:** As a user, I want feedback when no insights exist
- **Preconditions:** New user, no query history
- **Steps:**
  1. Navigate to Insights view
- **Expected Result:**
  - Stats show 0 values
  - "No insights detected yet. Keep using ACMS!" message
- **Acceptance Criteria:** Encouraging empty states
- **Priority:** P2

#### INS-008: Analysis No Results
- **Test ID:** INS-008
- **User Story:** As a user, I want feedback when analysis finds nothing
- **Preconditions:** Insights view loaded
- **Steps:**
  1. Analyze topic with no data: "quantum computing"
- **Expected Result:** "No analysis available" or low confidence message
- **Acceptance Criteria:** Graceful handling of unknown topics
- **Priority:** P2

### Iteration 7-8: Accessibility

#### REP-009: Keyboard Navigation - Generate Form
- **Test ID:** REP-009
- **User Story:** As a keyboard user, I want to fill generate form
- **Preconditions:** Reports view loaded
- **Steps:**
  1. Tab through form controls
  2. Change values with keyboard
  3. Tab to and activate Generate button
- **Expected Result:** All controls keyboard accessible
- **Acceptance Criteria:** Logical tab order
- **Priority:** P2

#### REP-010: Screen Reader - Report Content
- **Test ID:** REP-010
- **User Story:** As a screen reader user, I want report content announced
- **Preconditions:** Report displayed
- **Steps:**
  1. Navigate report with screen reader
- **Expected Result:**
  - Headings hierarchy correct (h1, h2, h3)
  - Charts have text alternatives
  - Data tables have proper structure
- **Acceptance Criteria:** Semantic HTML used
- **Priority:** P2

#### INS-009: Analysis Input Accessible
- **Test ID:** INS-009
- **User Story:** As a screen reader user, I want analysis input labeled
- **Preconditions:** Insights view loaded
- **Steps:**
  1. Focus analysis input
- **Expected Result:** Input purpose announced (via label or aria-label)
- **Acceptance Criteria:** Accessible name present
- **Priority:** P2

### Iteration 9-10: Performance and Delight

#### REP-011: Report Loading Animation
- **Test ID:** REP-011
- **User Story:** As a user, I want engaging loading state during generation
- **Preconditions:** Click Generate Report
- **Steps:**
  1. Observe loading state
- **Expected Result:**
  - Animated spinner icon
  - Pulsing/animated bars
  - "Analyzing usage patterns, extracting insights..." message
- **Acceptance Criteria:** Multi-element animation
- **Priority:** P3

#### REP-012: Chart Visualizations
- **Test ID:** REP-012
- **User Story:** As a user, I want visually appealing charts
- **Preconditions:** Report displayed with data
- **Steps:**
  1. View Top Topics bar chart
  2. View Agent Usage donut chart
- **Expected Result:**
  - Bar chart with colored bars, rank numbers, trend indicators
  - Donut chart with conic-gradient, center total, legend
- **Acceptance Criteria:** Charts render correctly with data
- **Priority:** P2

#### INS-010: Expertise Card Hover Effects
- **Test ID:** INS-010
- **User Story:** As a user, I want visual feedback on interactive elements
- **Preconditions:** Expertise centers displayed
- **Steps:**
  1. Hover over expertise card
- **Expected Result:**
  - Cursor changes to pointer
  - Card has hover effect (shadow, border, scale)
  - Navigation hint visible
- **Acceptance Criteria:** .clickable class with hover styles
- **Priority:** P3

---

## View 5: Data Flow View

### Iteration 1-2: Basic Functionality

#### DFL-001: View Loads Successfully
- **Test ID:** DFL-001
- **User Story:** As a user, I want the Data Flow view to load
- **Preconditions:** Audit system initialized
- **Steps:**
  1. Click "Data Flow" in sidebar
- **Expected Result:**
  - Header "Data Flow Monitor"
  - Period selector (Today, 7 Days, 30 Days)
  - Privacy Status Hero
  - Stats row
  - Details grid
- **Acceptance Criteria:** View renders from /api/v2/audit/dashboard
- **Priority:** P0

#### DFL-002: Privacy Status Hero Display
- **Test ID:** DFL-002
- **User Story:** As a user, I want to see my privacy status prominently
- **Preconditions:** View loaded
- **Steps:**
  1. Observe Privacy Status Hero section
- **Expected Result:**
  - Green shield icon with "SECURE" if no leakage
  - Red/yellow warning if violations
  - Clear explanation text
- **Acceptance Criteria:** Visual indicator matches status
- **Priority:** P0 (Security)

#### DFL-003: Hero Stats Display
- **Test ID:** DFL-003
- **User Story:** As a user, I want to see data flow statistics
- **Preconditions:** Data flow events exist
- **Steps:**
  1. View stats row
- **Expected Result:** Four stat cards:
  - Data Ingress (items received)
  - Transforms (processing operations)
  - Data Egress (external API calls)
  - LLM Cost (USD and tokens)
- **Acceptance Criteria:** Calculations match API data
- **Priority:** P0

### Iteration 3-4: User Flows

#### DFL-004: Switch Period - 7 Days
- **Test ID:** DFL-004
- **User Story:** As a user, I want to view data flow for 7 days
- **Preconditions:** View loaded
- **Steps:**
  1. Click "7 Days" button
- **Expected Result:**
  - Button shows active state
  - Dashboard reloads with 7-day aggregated data
- **Acceptance Criteria:** days parameter passed to API
- **Priority:** P1

#### DFL-005: View Ingress Details
- **Test ID:** DFL-005
- **User Story:** As a user, I want to see ingress breakdown
- **Preconditions:** Ingress section visible
- **Steps:**
  1. View Data Ingress section
- **Expected Result:** Breakdown by source:
  - Gmail emails count
  - Calendar events count
  - Plaid transactions count
  - Files uploaded count
  - Chat messages count
- **Acceptance Criteria:** Individual source counts display
- **Priority:** P1

#### DFL-006: View Egress Details
- **Test ID:** DFL-006
- **User Story:** As a user, I want to see egress breakdown
- **Preconditions:** Egress section visible
- **Steps:**
  1. View Data Egress section
- **Expected Result:** Breakdown by destination:
  - Claude API calls
  - OpenAI API calls
  - Gemini API calls
  - Browser automations
- **Acceptance Criteria:** Individual destination counts display
- **Priority:** P1

#### DFL-007: View Transforms Details
- **Test ID:** DFL-007
- **User Story:** As a user, I want to see transformation operations
- **Preconditions:** Transforms section visible
- **Steps:**
  1. View Data Transformations section
- **Expected Result:**
  - Summaries count
  - Embeddings count
  - Learning signals count
  - Knowledge facts count
  - Memories count
- **Acceptance Criteria:** Transform type breakdown
- **Priority:** P1

#### DFL-008: View Integration Status
- **Test ID:** DFL-008
- **User Story:** As a user, I want to see integration health
- **Preconditions:** Integrations exist
- **Steps:**
  1. View Integration Status section
- **Expected Result:**
  - Card for each integration (Gmail, Plaid, etc.)
  - Connection status (connected/disconnected)
  - Health status indicator
  - Items synced count
  - Last sync time
- **Acceptance Criteria:** All integrations listed
- **Priority:** P1

#### DFL-009: View Weekly Trend
- **Test ID:** DFL-009
- **User Story:** As a user, I want to see data flow trends
- **Preconditions:** Week trend data exists
- **Steps:**
  1. View Weekly Trend section
- **Expected Result:**
  - Bar chart with 7 days
  - Day labels (Mon, Tue, etc.)
  - Bar heights proportional to operations
  - Values displayed
- **Acceptance Criteria:** Trend chart renders
- **Priority:** P2

#### DFL-010: View Recent Events
- **Test ID:** DFL-010
- **User Story:** As a user, I want to see recent audit events
- **Preconditions:** Audit events exist
- **Steps:**
  1. View Recent Events table
- **Expected Result:** Table with columns:
  - Time (relative)
  - Type (ingress/egress/transform)
  - Source
  - Operation
  - Destination
  - Status (checkmark/X)
  - Duration (ms)
- **Acceptance Criteria:** Last 15 events displayed
- **Priority:** P1

#### DFL-011: View End of Day Report
- **Test ID:** DFL-011
- **User Story:** As a user, I want to generate EOD report
- **Preconditions:** EOD button visible
- **Steps:**
  1. Click "View Today's Report" button
- **Expected Result:**
  - Loading state appears
  - EOD report display shows comprehensive summary
- **Acceptance Criteria:** GET /api/v2/audit/report/today
- **Priority:** P2

### Iteration 5-6: Edge Cases

#### DFL-012: No Data Today
- **Test ID:** DFL-012
- **User Story:** As a user, I want feedback when no activity today
- **Preconditions:** No audit events today
- **Steps:**
  1. View Data Flow with "Today" selected
- **Expected Result:**
  - Stats show 0 values
  - "No events recorded" in recent events
- **Acceptance Criteria:** Graceful zero state
- **Priority:** P2

#### DFL-013: API Error - Audit Dashboard
- **Test ID:** DFL-013
- **User Story:** As a user, I want error handling when audit fails
- **Preconditions:** Audit API unavailable
- **Steps:**
  1. Navigate to Data Flow view
- **Expected Result:**
  - "Unable to Load Data Flow"
  - Error message
  - "Make sure audit system is initialized" hint
  - Retry button
- **Acceptance Criteria:** Helpful error state
- **Priority:** P1

#### DFL-014: Privacy Violation State
- **Test ID:** DFL-014
- **User Story:** As a user, I want clear warning on privacy issues
- **Preconditions:** Simulate privacy violation (CONFIDENTIAL to external)
- **Steps:**
  1. View Privacy Status Hero
- **Expected Result:**
  - Red/warning styling
  - "WARNING" status
  - Clear explanation of violation
- **Acceptance Criteria:** Security concern prominently displayed
- **Priority:** P0 (Security)

#### DFL-015: Failed Event Display
- **Test ID:** DFL-015
- **User Story:** As a user, I want failed events highlighted
- **Preconditions:** Failed audit event exists
- **Steps:**
  1. View Recent Events table
- **Expected Result:**
  - Failed row has distinct styling
  - X icon instead of checkmark
- **Acceptance Criteria:** event-failed class applied
- **Priority:** P1

### Iteration 7-8: Accessibility

#### DFL-016: Keyboard Navigation - Period Selector
- **Test ID:** DFL-016
- **User Story:** As a keyboard user, I want to change period
- **Preconditions:** View loaded
- **Steps:**
  1. Tab to period buttons
  2. Press Enter/Space
- **Expected Result:** Period changes, content reloads
- **Acceptance Criteria:** Buttons keyboard accessible
- **Priority:** P2

#### DFL-017: Screen Reader - Stats Cards
- **Test ID:** DFL-017
- **User Story:** As a screen reader user, I want stats announced
- **Preconditions:** Screen reader active
- **Steps:**
  1. Navigate stats cards
- **Expected Result:**
  - Value and label announced together
  - Icon has aria-hidden or alt text
- **Acceptance Criteria:** Meaningful announcements
- **Priority:** P2

#### DFL-018: Events Table Accessibility
- **Test ID:** DFL-018
- **User Story:** As a screen reader user, I want events table navigable
- **Preconditions:** Events table visible
- **Steps:**
  1. Navigate table with screen reader
- **Expected Result:**
  - Column headers announced
  - Row context provided
  - Status symbols have text alternatives
- **Acceptance Criteria:** Proper table markup
- **Priority:** P2

### Iteration 9-10: Performance and Delight

#### DFL-019: Privacy Hero Visual Impact
- **Test ID:** DFL-019
- **User Story:** As a user, I want privacy status to be visually prominent
- **Preconditions:** View loaded
- **Steps:**
  1. View Privacy Status Hero
- **Expected Result:**
  - Large, clear icon
  - Color-coded background
  - Prominent text
- **Acceptance Criteria:** Immediately draws attention
- **Priority:** P2

#### DFL-020: Loading Skeleton
- **Test ID:** DFL-020
- **User Story:** As a user, I want visual placeholder during load
- **Preconditions:** Simulate slow network
- **Steps:**
  1. Navigate to Data Flow view
- **Expected Result:**
  - Skeleton cards visible
  - Pulsing animation
- **Acceptance Criteria:** Skeleton matches layout
- **Priority:** P3

---

## Cross-View Navigation Tests

#### NAV-001: Sidebar Navigation - All Views
- **Test ID:** NAV-001
- **User Story:** As a user, I want to navigate between all views
- **Preconditions:** App loaded
- **Steps:**
  1. Click each sidebar item in order:
     - Chat, Email, Financial, Memories, Knowledge, Search, Insights, Reports, API Analytics, Data Flow, Settings
- **Expected Result:** Each view loads correctly
- **Acceptance Criteria:** No view fails to load
- **Priority:** P0

#### NAV-002: Active Navigation State
- **Test ID:** NAV-002
- **User Story:** As a user, I want to see which view is active
- **Preconditions:** View loaded
- **Steps:**
  1. Navigate to any view
  2. Check sidebar
- **Expected Result:** Active view has visual indicator (.active class)
- **Acceptance Criteria:** Clear active state
- **Priority:** P1

#### NAV-003: Insights to Knowledge Navigation
- **Test ID:** NAV-003
- **User Story:** As a user, I want to drill from Insights to Knowledge
- **Preconditions:** Insights view showing expertise centers
- **Steps:**
  1. Click expertise center card
- **Expected Result:**
  - Navigates to Knowledge view
  - Domain filter pre-applied
  - Sidebar active state updates
- **Acceptance Criteria:** Filter state preserved
- **Priority:** P2

#### NAV-004: Nudge Action Navigation
- **Test ID:** NAV-004
- **User Story:** As a user, I want nudges to navigate to relevant content
- **Preconditions:** Nudge with related_id exists
- **Steps:**
  1. Click nudge in sidebar
- **Expected Result:**
  - Navigation to appropriate view
  - Item/context highlighted or focused
- **Acceptance Criteria:** Custom event handled
- **Priority:** P2

---

## Active Second Brain Components

### Feedback Modal Tests

#### FB-001: Positive Feedback Modal Opens
- **Test ID:** FB-001
- **User Story:** As a user, I want to save good responses (AC9)
- **Preconditions:** Chat message with feedback buttons
- **Steps:**
  1. Click thumbs up button on a message
- **Expected Result:**
  - Modal opens within 500ms (AC9)
  - Title "Thanks for the feedback!"
  - "Save as verified knowledge?" prompt
  - Countdown visible (AC13)
  - "Yes, Save" and "No, Thanks" buttons
- **Acceptance Criteria:** showPositiveFeedbackModal called
- **Priority:** P0 (Active Second Brain)

#### FB-002: Save as Verified Knowledge
- **Test ID:** FB-002
- **User Story:** As a user, I want to save verified responses (AC10)
- **Preconditions:** Positive modal open
- **Steps:**
  1. Click "Yes, Save"
- **Expected Result:**
  - API call with save_as_verified: true
  - Success toast
  - Message marked as "Saved"
  - Modal closes
- **Acceptance Criteria:** POST /api/v2/feedback with save_as_verified
- **Priority:** P0 (Active Second Brain)

#### FB-003: Auto-Dismiss After 10 Seconds
- **Test ID:** FB-003
- **User Story:** As a user, I want modal to auto-dismiss (AC13)
- **Preconditions:** Positive modal open
- **Steps:**
  1. Wait 10 seconds without interacting
- **Expected Result:**
  - Countdown updates every second
  - Modal auto-closes at 0
  - Feedback recorded without save
- **Acceptance Criteria:** setInterval countdown works
- **Priority:** P1 (Active Second Brain)

#### FB-004: Negative Feedback Modal Opens
- **Test ID:** FB-004
- **User Story:** As a user, I want to report bad responses (AC11)
- **Preconditions:** Chat message with feedback buttons
- **Steps:**
  1. Click thumbs down button
- **Expected Result:**
  - Modal opens with "What went wrong?"
  - Reason radio buttons (8 options)
  - Optional comment textarea
  - Submit and Cancel buttons
- **Acceptance Criteria:** showNegativeFeedbackModal called
- **Priority:** P0 (Active Second Brain)

#### FB-005: Submit Negative with Reason
- **Test ID:** FB-005
- **User Story:** As a user, I want to submit feedback with reason
- **Preconditions:** Negative modal open
- **Steps:**
  1. Select "Incorrect" reason
  2. Add optional comment
  3. Click "Submit Feedback"
- **Expected Result:**
  - API call with reason and reason_text
  - Success toast
  - If demoted: "This response has been removed from cache"
  - Modal closes
- **Acceptance Criteria:** POST /api/v2/feedback with negative feedback
- **Priority:** P0 (Active Second Brain)

#### FB-006: Negative Feedback - No Reason Selected
- **Test ID:** FB-006
- **User Story:** As a user, I want validation when no reason selected
- **Preconditions:** Negative modal open
- **Steps:**
  1. Click Submit without selecting reason
- **Expected Result:** Error toast: "Please select a reason"
- **Acceptance Criteria:** Client-side validation
- **Priority:** P1

#### FB-007: Wrong Agent Reason - Cache Demotion
- **Test ID:** FB-007
- **User Story:** As a user, I want "Wrong Agent" to demote cache (AC12)
- **Preconditions:** Cached response shown
- **Steps:**
  1. Click thumbs down
  2. Select "Wrong Agent"
  3. Submit
- **Expected Result:**
  - Response demoted from cache
  - Toast confirms demotion
  - Next similar query will call LLM fresh
- **Acceptance Criteria:** Cache entry demoted
- **Priority:** P0 (Active Second Brain)

### Nudge Sidebar Tests

#### NUD-001: Nudge Sidebar Opens
- **Test ID:** NUD-001
- **User Story:** As a user, I want to view my notifications
- **Preconditions:** Nudge toggle button visible
- **Steps:**
  1. Click bell icon in header
- **Expected Result:**
  - Sidebar slides open
  - Header "Notifications"
  - Close button and Clear All button
  - Nudge cards or empty state
- **Acceptance Criteria:** openNudgeSidebar called
- **Priority:** P1 (Active Second Brain)

#### NUD-002: Badge Count Updates
- **Test ID:** NUD-002
- **User Story:** As a user, I want to see notification count
- **Preconditions:** Nudges exist
- **Steps:**
  1. Observe bell icon
- **Expected Result:**
  - Badge shows count
  - Count > 99 shows "99+"
  - Badge hidden if count = 0
- **Acceptance Criteria:** updateNudgeBadge works
- **Priority:** P1

#### NUD-003: Nudge Card Display
- **Test ID:** NUD-003
- **User Story:** As a user, I want to see nudge details
- **Preconditions:** Nudges loaded
- **Steps:**
  1. Open nudge sidebar
  2. Inspect nudge card
- **Expected Result:** Card shows:
  - Type icon and label
  - Priority badge
  - Title
  - Message
  - Timestamp (relative)
  - View, Snooze, Dismiss buttons
- **Acceptance Criteria:** All nudge types render correctly
- **Priority:** P1

#### NUD-004: Snooze Nudge
- **Test ID:** NUD-004
- **User Story:** As a user, I want to snooze notifications
- **Preconditions:** Nudge visible
- **Steps:**
  1. Click "Snooze" button on nudge
- **Expected Result:**
  - API call to /api/nudges/snooze
  - Toast: "Snoozed for 60 minutes"
  - Nudge removed from list
  - Badge count updates
- **Acceptance Criteria:** snoozeNudge(id, 60) called
- **Priority:** P2

#### NUD-005: Dismiss Nudge
- **Test ID:** NUD-005
- **User Story:** As a user, I want to dismiss notifications
- **Preconditions:** Nudge visible
- **Steps:**
  1. Click X button on nudge
- **Expected Result:**
  - API call to /api/nudges/dismiss
  - Nudge removed from list
  - Badge count updates
- **Acceptance Criteria:** dismissNudge(id) called
- **Priority:** P2

#### NUD-006: Clear All Nudges
- **Test ID:** NUD-006
- **User Story:** As a user, I want to clear all notifications
- **Preconditions:** Multiple nudges exist
- **Steps:**
  1. Click "Clear All" button
- **Expected Result:**
  - All nudges dismissed
  - Empty state shows
  - Badge hidden
- **Acceptance Criteria:** clearAllNudges iterates through list
- **Priority:** P2

#### NUD-007: Polling for New Nudges
- **Test ID:** NUD-007
- **User Story:** As a user, I want nudges to update automatically
- **Preconditions:** App running
- **Steps:**
  1. Wait 60 seconds
  2. Add nudge via API
  3. Observe badge
- **Expected Result:**
  - Badge updates without refresh
  - New nudge appears in sidebar
- **Acceptance Criteria:** startNudgePolling(60000) working
- **Priority:** P2

---

## Complete Test Suite Summary

| View | Test Cases | P0 | P1 | P2 | P3 |
|------|-----------|----|----|----|----|
| Memories | 21 | 5 | 6 | 8 | 2 |
| Knowledge | 22 | 7 | 7 | 6 | 2 |
| Financial | 18 | 3 | 8 | 6 | 1 |
| Reports/Insights | 22 | 4 | 7 | 9 | 2 |
| Data Flow | 20 | 3 | 9 | 7 | 1 |
| Navigation | 4 | 1 | 1 | 2 | 0 |
| Feedback Modal | 7 | 5 | 2 | 0 | 0 |
| Nudge Sidebar | 7 | 0 | 3 | 4 | 0 |
| **TOTAL** | **121** | **28** | **43** | **42** | **8** |

---

## Priority Rankings

### P0 - Critical (28 tests)
Must pass before any release. Includes:
- View loading functionality
- Core data display
- Security (XSS prevention, privacy status)
- Active Second Brain core features (feedback, knowledge correction)

### P1 - High (43 tests)
Must pass for production release. Includes:
- All user flows (filters, search, navigation)
- Error handling
- Large dataset performance
- Tab functionality

### P2 - Medium (42 tests)
Should pass for quality release. Includes:
- Accessibility (keyboard nav, screen readers)
- Empty states
- Edge cases
- Visual indicators

### P3 - Low (8 tests)
Nice to have. Includes:
- Animations and transitions
- Loading skeletons
- Visual polish

---

## Automation Recommendations

### Recommended for Automation (Playwright/Cypress)

1. **All P0 tests** - Critical path must be automated
2. **View loading tests** (MEM-001, KNO-001, FIN-001, REP-001, INS-001, DFL-001)
3. **Navigation tests** (NAV-001, NAV-002)
4. **Filter/search functionality** (MEM-004-007, KNO-007-009)
5. **Tab switching** (KNO-004-006, FIN-005-007)
6. **API error handling** (MEM-011, KNO-011, FIN-011, DFL-013)
7. **Active Second Brain flows** (FB-001-007, NUD-001-007)

### Test Data Setup Requirements

```javascript
// Playwright fixture example
test.beforeAll(async () => {
  // Create test memories across privacy levels
  await seedMemories({ count: 100, privacyLevels: ['PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'LOCAL_ONLY'] });

  // Create knowledge items with varying confidence
  await seedKnowledge({ count: 50, confidenceRange: [0.3, 0.99] });

  // Create reports history
  await seedReports({ count: 5, types: ['weekly', 'monthly'] });

  // Setup Plaid sandbox
  await connectPlaidSandbox();
});
```

### Automation Framework Recommendations

1. **Playwright** (Preferred)
   - Cross-browser support
   - Built-in wait handling
   - Network mocking for error tests
   - Accessibility testing via axe-core integration

2. **Test Organization**
   ```
   tests/
     e2e/
       views/
         memories.spec.ts
         knowledge.spec.ts
         financial.spec.ts
         reports.spec.ts
         insights.spec.ts
         data-flow.spec.ts
       components/
         feedback-modal.spec.ts
         nudge-sidebar.spec.ts
       navigation.spec.ts
   ```

3. **CI Integration**
   - Run on PR merge
   - Run nightly for full regression
   - Screenshot comparison for visual tests

---

## Manual Testing Requirements

### Tests Requiring Manual Execution

1. **Screen reader tests** (MEM-016, KNO-020, REP-010, etc.)
   - Requires VoiceOver/NVDA expertise
   - Cannot be reliably automated

2. **Visual design verification**
   - Color schemes
   - Layout aesthetics
   - Animation smoothness

3. **Plaid Link integration** (FIN-004)
   - Third-party SDK
   - Manual interaction required

4. **Performance perception tests**
   - "Feel" of responsiveness
   - Animation quality

5. **Exploratory testing**
   - Edge cases not covered
   - Unusual user journeys

### Manual Test Session Template

```markdown
## Manual Test Session

**Tester:** [Name]
**Date:** [Date]
**Duration:** [Time]
**Build:** [Version]

### Focus Areas
- [ ] Screen reader compatibility
- [ ] Visual design review
- [ ] Exploratory testing

### Findings
| ID | Description | Severity | Steps | Screenshot |
|----|-------------|----------|-------|------------|
|    |             |          |       |            |

### Overall Assessment
[Notes on quality, usability, recommendations]
```

---

## Sign-Off Checklist

Before feature completion:

- [ ] All P0 tests passing
- [ ] All P1 tests passing
- [ ] 80%+ P2 tests passing
- [ ] Automated test suite running in CI
- [ ] Manual accessibility audit completed
- [ ] Performance benchmarks met (load < 2s, scroll 60fps)
- [ ] Cross-browser testing (Chrome, Safari, Firefox on Mac)
- [ ] QA sign-off obtained

---

**Document prepared by:** QA Engineering Team
**Last updated:** February 6, 2026
**Next review:** After implementation of test automation
