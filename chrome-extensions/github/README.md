# ACMS GitHub Extension

Chrome extension to automatically capture GitHub issues, pull requests, and discussions into your local ACMS memory system.

## Features

- **Multi-Content Capture**: Issues, Pull Requests, and Discussions
- **Auto-Capture**: Monitors GitHub pages, captures on load and updates every 5 seconds
- **Privacy-Aware**: Detects private repos, API keys, credentials, emails
- **Smart Tagging**: Auto-generates tags from repo name, labels, state, and content
- **Manual Control**: Toggle auto-capture on/off, trigger manual captures
- **Repo-Aware**: Tracks repository, issue/PR number, state, labels
- **Comment Tracking**: Captures all comments, review comments, and replies
- **Sensitive Content Detection**: Flags credentials, API keys, internal mentions

## What Gets Captured

### Issues
- Title, number, state (open/closed)
- Description/body
- All comments with authors
- Labels and metadata
- Repository information

### Pull Requests
- Title, number, state (open/closed/merged)
- Description/body
- All comments with authors
- Review comments with authors
- Files changed count
- Labels and metadata
- Repository information

### Discussions
- Title and category
- Description/body
- All replies with authors
- Repository information

## Installation

### Prerequisites

1. ACMS API must be running on `http://localhost:40080`

```bash
# Start ACMS
cd /path/to/acms
./start_desktop.sh
```

2. Verify API health:

```bash
curl http://localhost:40080/health
# Should return: {"status":"healthy",...}
```

### Load Extension

1. Open Chrome browser
2. Navigate to `chrome://extensions/`
3. Enable "Developer mode" (toggle in top-right)
4. Click "Load unpacked"
5. Select directory: `/path/to/acms/chrome-extensions/github`
6. Extension should appear with green status indicator

## Usage

### Auto-Capture (Default)

1. Open any GitHub issue, PR, or discussion
2. Extension automatically captures on page load
3. Updates captured every 5 seconds (when comments added)
4. Click extension icon to see statistics
5. Captured content appears in ACMS Desktop App with tags: `github`, `issue`/`pull_request`/`discussion`, repo name, labels

### Manual Capture

1. Open GitHub issue/PR/discussion
2. Click ACMS extension icon
3. Click "Capture Now" button
4. Check Desktop App for new memory

### Toggle Capture

1. Click extension icon
2. Toggle "Auto-Capture" switch
3. Green = enabled, Gray = disabled

## What's Captured

Each capture includes:

- **Full content**: Formatted markdown with title, body, comments
- **Auto-tags**: github, [type], [repo-name], [labels], [state], topic tags
- **Privacy level**: Auto-detected by ACMS (CONFIDENTIAL for private repos or sensitive content)
- **Metadata**:
  - `source`: "github"
  - `type`: "issue", "pull_request", or "discussion"
  - `repository`: "owner/repo"
  - `number`: Issue/PR number
  - `state`: "open", "closed", "merged"
  - `labels`: Array of labels
  - `is_private_repo`: Boolean
  - `comment_count`: Total comments/replies
  - `url`: Full GitHub URL
  - `captured_at`: ISO timestamp
  - `sensitive_content`: Reason if sensitive (credentials/email/internal)
  - `privacy_hint`: "CONFIDENTIAL" if private or sensitive
- **Tier**: SHORT (default)
- **Phase**: "development"

## Privacy Detection

The extension automatically detects sensitive content:

### Credentials & Secrets
- API keys (api_key, api-key)
- Secret keys (secret_key, secret-key)
- Access tokens (access_token, access-token)
- Passwords
- GitHub personal access tokens (ghp_...)
- AWS keys
- Private keys (-----BEGIN ... KEY-----)

### Personal Information
- Email addresses

### Internal Content
- Keywords: "internal", "confidential", "private"

### Private Repositories
- Automatically detected via GitHub UI badges
- Marked as CONFIDENTIAL

## Tagging System

Tags are automatically generated:

### Base Tags
- `github` (always)
- `issue`, `pull_request`, or `discussion` (type)
- `auto-captured` (always)

### Repository Tag
- `owner-repo` (normalized repo name)

### Label Tags
- All GitHub labels (normalized: lowercase, dashes)

### State Tags
- `open`, `closed`, `merged`

### Topic Tags (from title/body)
- `bug` (bug, error, crash, issue, problem, fix)
- `feature` (feature, enhancement, improvement, add, implement)
- `documentation` (documentation, docs, readme)
- `testing` (test, testing, spec)
- `refactoring` (refactor, cleanup, optimize)

### Example
Issue with labels "bug" and "priority:high" in repo "acme/webapp":
- Tags: `github`, `issue`, `auto-captured`, `acme-webapp`, `bug`, `priority-high`, `open`, `bug` (topic)

## Troubleshooting

### Red Status Indicator

**Problem**: Extension can't connect to ACMS API

**Solution**:
```bash
# Check if API is running
curl http://localhost:40080/health

# If not, start ACMS
cd /path/to/acms
./start_desktop.sh
```

### No Content Extracted

**Problem**: GitHub page may not be fully loaded or wrong page type

**Solution**:
1. Wait for page to fully load (spinner gone)
2. Verify you're on an issue, PR, or discussion page (not repo home, file view, etc.)
3. Open Chrome DevTools (F12)
4. Go to Console tab
5. Look for `[ACMS GitHub]` log messages
6. Check for "Not an issue/PR/discussion page" message

### Private Repo Not Marked Confidential

**Problem**: Privacy detection may miss private badge

**Solution**:
1. Extension looks for "Private" badge in UI
2. If repo is private but not flagged, check console for `is_private_repo: false`
3. Privacy classifier in ACMS API will still catch most sensitive content

### Comments Not Captured

**Problem**: Comments may load dynamically

**Solution**:
1. Scroll down to load all comments
2. Wait 5 seconds for re-capture
3. Or use manual capture button

## Debugging

### Content Script Console

1. Open GitHub page
2. Press F12 (DevTools)
3. Go to Console tab
4. Filter by `[ACMS GitHub]`
5. Check for extraction logs:
   - "Starting page monitoring"
   - "Sending to background for storage"
   - Type, repo, tags, content length

### Background Script Console

1. Go to `chrome://extensions/`
2. Find "ACMS GitHub Capture"
3. Click "Inspect views: service worker"
4. Look for `[ACMS Background]` messages

## Architecture

### Content Script (`content.js`)

- Runs on all https://github.com/* pages
- Detects page type (issue/PR/discussion)
- Extracts content based on type
- Formats as markdown
- Detects private repos and sensitive content
- Generates contextual tags
- Sends to background script on load + every 5 seconds

### Page Type Detection

```javascript
// URL patterns:
/owner/repo/issues/123      → issue
/owner/repo/pull/123        → pull_request
/owner/repo/discussions/123 → discussion
```

### Extraction Strategy

1. **Issue**: Title, number, state, labels, body, comments
2. **PR**: Title, number, state, labels, body, comments, review comments, files changed
3. **Discussion**: Title, category, body, replies

All use GitHub's semantic HTML structure with fallbacks.

### Privacy Detection

Multi-layer approach:
1. **Private badge**: Check for "Private" badge in GitHub UI
2. **Credential patterns**: Regex matching for API keys, tokens, passwords
3. **Email detection**: Regex for email addresses
4. **Internal keywords**: Check for "internal", "confidential", "private"
5. **ACMS classifier**: Final privacy level determined by ACMS API

### Message Format

#### Issue Example
```markdown
# GitHub Issue: Fix memory leak in API server

**Repository**: acme/webapp
**Issue**: #456
**State**: open
**Labels**: bug, priority:high
**URL**: https://github.com/acme/webapp/issues/456
**Captured**: 2025-01-15T10:30:00.000Z

---

## Description

API server crashes after 24 hours due to memory leak...

---

## Comments (3)

### Comment 1 by @johndoe

I can reproduce this on staging...

---

...
```

## Background Script (`background.js`)

- Service worker (Manifest V3)
- Handles API communication with ACMS
- Stores content via POST /memories
- Maintains API health checks
- Manages extension state

## Popup (`popup.html`, `popup.js`)

- Extension UI for user control
- Auto-capture toggle
- Manual capture button
- Real-time statistics
- ACMS health indicator

## Privacy

- All data stored locally on your machine
- No external servers contacted
- Only communicates with `localhost:40080` (your local ACMS)
- Privacy classification handled by ACMS API
- Sensitive content flagged with privacy hints
- Private repos auto-marked as CONFIDENTIAL
- Toggle capture on/off anytime

## Technical Details

### DOM Selectors

GitHub uses semantic HTML with stable classes:

**Common**:
- `.js-issue-title` - Issue/PR title
- `.gh-header-number` - Issue/PR number
- `.State` - Open/closed/merged state
- `.IssueLabel`, `.Label` - Labels
- `.comment-body` - Comment content
- `.author` - Comment author

**Issue-specific**:
- `.timeline-comment` - Comments

**PR-specific**:
- `.review-comment` - Review comments
- `#files_tab_counter` - Files changed

**Discussion-specific**:
- `.gh-header-title` - Discussion title

### Capture Timing

- **Initial capture**: 2 seconds after page load
- **Re-capture**: Every 5 seconds (for new comments)
- **Navigation**: 2 seconds after SPA navigation

### Deduplication

Content is deduplicated by comparing full formatted text:
- If `content === lastCapturedContent`, skip capture
- Prevents duplicate memories for same issue/PR state

## Comparison with ChatGPT/Claude/Gemini Extensions

| Feature | ChatGPT | Claude | Gemini | GitHub |
|---------|---------|--------|--------|--------|
| Auto-capture | ✅ | ✅ | ✅ | ✅ |
| Manual capture | ✅ | ✅ | ✅ | ✅ |
| Privacy detection | ✅ | ✅ | ✅ | ✅ Advanced |
| Content type | Conversation | Conversation | Conversation | Issue/PR/Discussion |
| Topic tagging | 5 topics | 5 topics | 6 topics | 5 topics + labels |
| Capture interval | 2s | 2s | 2s | 5s |
| Credential detection | ❌ | ❌ | ❌ | ✅ |
| Repo awareness | ❌ | ❌ | ❌ | ✅ |
| Privacy hints | ❌ | ❌ | ❌ | ✅ |

## Known Limitations

1. **DOM changes**: GitHub updates frequently, DOM structure may change
2. **Dynamic loading**: Some comments may load lazily (scroll to trigger)
3. **Code review files**: Does not capture file diffs (only counts)
4. **Attachments**: Does not capture images, files
5. **Reactions**: Does not capture emoji reactions
6. **Long threads**: Very long issues (500+ comments) may be truncated in UI

## Future Enhancements

- **File diff capture**: Store code changes from PRs
- **Image capture**: Save screenshots, attachments
- **Reaction tracking**: Capture emoji reactions
- **Linked issues**: Track issue/PR references
- **Milestone tracking**: Capture milestone info
- **Project board**: Track project column
- **CI/CD status**: Capture check run status
- **Code snippets**: Extract and highlight code blocks

## Success Criteria

✅ Extension loads without errors
✅ Green status indicator when ACMS running
✅ GitHub issues/PRs/discussions auto-captured
✅ Content appears in Desktop App
✅ Privacy badges show CONFIDENTIAL for private repos
✅ Tags include: github, type, repo, labels, state
✅ Sensitive content flagged correctly

## Testing Checklist

### Issue Testing
- [ ] Install extension in Chrome
- [ ] Verify green status indicator
- [ ] Open public GitHub issue
- [ ] Verify capture in Desktop App
- [ ] Check tags include repo name and labels
- [ ] Open private repo issue
- [ ] Verify privacy badge shows CONFIDENTIAL

### PR Testing
- [ ] Open GitHub pull request
- [ ] Verify capture includes PR number
- [ ] Check review comments captured
- [ ] Verify files changed count present
- [ ] Check state (open/merged/closed)

### Discussion Testing
- [ ] Open GitHub discussion
- [ ] Verify category captured
- [ ] Check all replies present
- [ ] Verify formatting correct

### Privacy Testing
- [ ] Create issue with API key in comment
- [ ] Verify `sensitive_content: "credentials"` in metadata
- [ ] Verify privacy badge shows CONFIDENTIAL
- [ ] Test with email in issue body
- [ ] Verify `sensitive_content: "email"` flagged

---

**Part of ACMS Phase 4c** - Web Extensions for AI Tools

Built with ❤️ for local-first AI memory management
