/**
 * ACMS GitHub Content Script
 *
 * Monitors GitHub issues, pull requests, and discussions for ACMS storage.
 *
 * GitHub captures are different from conversations:
 * - Issues: Title, body, comments, labels, state
 * - PRs: Title, body, comments, code review comments, files changed
 * - Discussions: Title, body, replies
 *
 * Privacy considerations:
 * - Private repos: Mark as CONFIDENTIAL or LOCAL_ONLY
 * - Code snippets: Check for API keys, credentials, secrets
 * - Internal discussions: Detect company-specific content
 */

console.log('[ACMS GitHub] Content script loaded');

let captureEnabled = true;
let lastCapturedContent = '';
let captureStats = {
  totalCaptures: 0,
  lastCaptureTime: null,
  lastItemId: null
};

// Load settings from storage
chrome.storage.local.get(['captureEnabled', 'captureStats'], (result) => {
  if (result.captureEnabled !== undefined) {
    captureEnabled = result.captureEnabled;
  }
  if (result.captureStats) {
    captureStats = result.captureStats;
  }
  console.log('[ACMS GitHub] Settings loaded:', { captureEnabled, captureStats });
});

// Listen for settings changes
chrome.storage.onChanged.addListener((changes) => {
  if (changes.captureEnabled) {
    captureEnabled = changes.captureEnabled.newValue;
    console.log('[ACMS GitHub] Capture enabled changed:', captureEnabled);
  }
});

/**
 * Detect page type (issue, PR, discussion, or other)
 */
function detectPageType() {
  const path = window.location.pathname;

  // Format: /owner/repo/issues/123
  if (path.match(/\/[^/]+\/[^/]+\/issues\/\d+/)) {
    return 'issue';
  }

  // Format: /owner/repo/pull/123
  if (path.match(/\/[^/]+\/[^/]+\/pull\/\d+/)) {
    return 'pull_request';
  }

  // Format: /owner/repo/discussions/123
  if (path.match(/\/[^/]+\/[^/]+\/discussions\/\d+/)) {
    return 'discussion';
  }

  return null;
}

/**
 * Extract repository info from URL
 */
function getRepoInfo() {
  const match = window.location.pathname.match(/\/([^/]+)\/([^/]+)/);
  if (match) {
    return {
      owner: match[1],
      repo: match[2],
      full_name: `${match[1]}/${match[2]}`
    };
  }
  return null;
}

/**
 * Check if repository is private
 */
function isPrivateRepo() {
  // Look for private badge using valid CSS selectors
  const privateBadge = document.querySelector('[aria-label*="Private"]');
  if (privateBadge) return true;

  // Check for "Private" text in labels
  const labels = document.querySelectorAll('.Label, .Label--secondary');
  for (const label of labels) {
    if (label.textContent.trim().toLowerCase() === 'private') {
      return true;
    }
  }

  return false;
}

/**
 * Extract issue content
 */
function extractIssue() {
  // Title
  const titleEl = document.querySelector('.js-issue-title, .gh-header-title, h1.js-issue-title');
  const title = titleEl ? titleEl.textContent.trim() : 'Untitled Issue';

  // Issue number
  const numberEl = document.querySelector('.gh-header-number');
  const number = numberEl ? numberEl.textContent.trim() : '';

  // State (open/closed)
  const stateEl = document.querySelector('[title*="Status:"]') ||
                  document.querySelector('.State');
  const state = stateEl ? stateEl.textContent.trim().toLowerCase() : 'unknown';

  // Labels
  const labels = Array.from(document.querySelectorAll('.IssueLabel, .Label'))
    .map(label => label.textContent.trim())
    .filter(text => text.length > 0);

  // Body/Description
  const bodyEl = document.querySelector('.comment-body') ||
                 document.querySelector('[data-target="issue-body"]');
  const body = bodyEl ? bodyEl.textContent.trim() : '';

  // Comments
  const comments = [];
  const commentEls = document.querySelectorAll('.timeline-comment');

  commentEls.forEach((commentEl, index) => {
    const authorEl = commentEl.querySelector('.author');
    const author = authorEl ? authorEl.textContent.trim() : 'Unknown';

    const bodyEl = commentEl.querySelector('.comment-body');
    const content = bodyEl ? bodyEl.textContent.trim() : '';

    if (content.length > 0 && index > 0) { // Skip first comment (issue body)
      comments.push({ author, content });
    }
  });

  return {
    type: 'issue',
    title,
    number,
    state,
    labels,
    body,
    comments,
    commentCount: comments.length
  };
}

/**
 * Extract pull request content
 */
function extractPullRequest() {
  // Title
  const titleEl = document.querySelector('.js-issue-title');
  const title = titleEl ? titleEl.textContent.trim() : 'Untitled PR';

  // PR number
  const numberEl = document.querySelector('.gh-header-number');
  const number = numberEl ? numberEl.textContent.trim() : '';

  // State (open/closed/merged)
  const stateEl = document.querySelector('[title*="Status:"]') ||
                  document.querySelector('.State');
  const state = stateEl ? stateEl.textContent.trim().toLowerCase() : 'unknown';

  // Labels
  const labels = Array.from(document.querySelectorAll('.IssueLabel, .Label'))
    .map(label => label.textContent.trim())
    .filter(text => text.length > 0);

  // Description
  const bodyEl = document.querySelector('.comment-body');
  const body = bodyEl ? bodyEl.textContent.trim() : '';

  // Comments
  const comments = [];
  const commentEls = document.querySelectorAll('.timeline-comment');

  commentEls.forEach((commentEl, index) => {
    const authorEl = commentEl.querySelector('.author');
    const author = authorEl ? authorEl.textContent.trim() : 'Unknown';

    const bodyEl = commentEl.querySelector('.comment-body');
    const content = bodyEl ? bodyEl.textContent.trim() : '';

    if (content.length > 0 && index > 0) {
      comments.push({ author, content });
    }
  });

  // Files changed (count)
  const filesChangedEl = document.querySelector('#files_tab_counter, .diffbar-item');
  const filesChanged = filesChangedEl ? filesChangedEl.textContent.trim() : '0';

  // Review comments
  const reviewComments = [];
  const reviewCommentEls = document.querySelectorAll('.review-comment');

  reviewCommentEls.forEach(commentEl => {
    const authorEl = commentEl.querySelector('.author');
    const author = authorEl ? authorEl.textContent.trim() : 'Unknown';

    const bodyEl = commentEl.querySelector('.comment-body');
    const content = bodyEl ? bodyEl.textContent.trim() : '';

    if (content.length > 0) {
      reviewComments.push({ author, content });
    }
  });

  return {
    type: 'pull_request',
    title,
    number,
    state,
    labels,
    body,
    comments,
    reviewComments,
    commentCount: comments.length + reviewComments.length,
    filesChanged
  };
}

/**
 * Extract discussion content
 */
function extractDiscussion() {
  // Title
  const titleEl = document.querySelector('.gh-header-title, h1');
  const title = titleEl ? titleEl.textContent.trim() : 'Untitled Discussion';

  // Category
  const categoryEl = document.querySelector('.color-fg-muted, .Label');
  const category = categoryEl ? categoryEl.textContent.trim() : '';

  // Body
  const bodyEl = document.querySelector('.comment-body');
  const body = bodyEl ? bodyEl.textContent.trim() : '';

  // Replies
  const replies = [];
  const replyEls = document.querySelectorAll('.timeline-comment');

  replyEls.forEach((replyEl, index) => {
    const authorEl = replyEl.querySelector('.author');
    const author = authorEl ? authorEl.textContent.trim() : 'Unknown';

    const bodyEl = replyEl.querySelector('.comment-body');
    const content = bodyEl ? bodyEl.textContent.trim() : '';

    if (content.length > 0 && index > 0) {
      replies.push({ author, content });
    }
  });

  return {
    type: 'discussion',
    title,
    category,
    body,
    replies,
    replyCount: replies.length
  };
}

/**
 * Format issue as markdown
 * @param {boolean} includeTimestamp - Whether to include capture timestamp (for duplicate detection, set to false)
 */
function formatIssue(issue, repo, includeTimestamp = true) {
  let formatted = `# GitHub Issue: ${issue.title}\n\n`;
  formatted += `**Repository**: ${repo.full_name}\n`;
  formatted += `**Issue**: ${issue.number}\n`;
  formatted += `**State**: ${issue.state}\n`;

  if (issue.labels.length > 0) {
    formatted += `**Labels**: ${issue.labels.join(', ')}\n`;
  }

  formatted += `**URL**: ${window.location.href}\n`;

  if (includeTimestamp) {
    formatted += `**Captured**: ${new Date().toISOString()}\n\n`;
  } else {
    formatted += '\n';
  }

  formatted += '---\n\n';

  formatted += '## Description\n\n';
  formatted += issue.body + '\n\n';
  formatted += '---\n\n';

  if (issue.comments.length > 0) {
    formatted += `## Comments (${issue.comments.length})\n\n`;

    issue.comments.forEach((comment, index) => {
      formatted += `### Comment ${index + 1} by @${comment.author}\n\n`;
      formatted += comment.content + '\n\n';
      formatted += '---\n\n';
    });
  }

  return formatted;
}

/**
 * Format pull request as markdown
 * @param {boolean} includeTimestamp - Whether to include capture timestamp (for duplicate detection, set to false)
 */
function formatPullRequest(pr, repo, includeTimestamp = true) {
  let formatted = `# GitHub Pull Request: ${pr.title}\n\n`;
  formatted += `**Repository**: ${repo.full_name}\n`;
  formatted += `**PR**: ${pr.number}\n`;
  formatted += `**State**: ${pr.state}\n`;
  formatted += `**Files Changed**: ${pr.filesChanged}\n`;

  if (pr.labels.length > 0) {
    formatted += `**Labels**: ${pr.labels.join(', ')}\n`;
  }

  formatted += `**URL**: ${window.location.href}\n`;

  if (includeTimestamp) {
    formatted += `**Captured**: ${new Date().toISOString()}\n\n`;
  } else {
    formatted += '\n';
  }

  formatted += '---\n\n';

  formatted += '## Description\n\n';
  formatted += pr.body + '\n\n';
  formatted += '---\n\n';

  if (pr.comments.length > 0) {
    formatted += `## Comments (${pr.comments.length})\n\n`;

    pr.comments.forEach((comment, index) => {
      formatted += `### Comment ${index + 1} by @${comment.author}\n\n`;
      formatted += comment.content + '\n\n';
      formatted += '---\n\n';
    });
  }

  if (pr.reviewComments.length > 0) {
    formatted += `## Review Comments (${pr.reviewComments.length})\n\n`;

    pr.reviewComments.forEach((comment, index) => {
      formatted += `### Review Comment ${index + 1} by @${comment.author}\n\n`;
      formatted += comment.content + '\n\n';
      formatted += '---\n\n';
    });
  }

  return formatted;
}

/**
 * Format discussion as markdown
 * @param {boolean} includeTimestamp - Whether to include capture timestamp (for duplicate detection, set to false)
 */
function formatDiscussion(discussion, repo, includeTimestamp = true) {
  let formatted = `# GitHub Discussion: ${discussion.title}\n\n`;
  formatted += `**Repository**: ${repo.full_name}\n`;
  formatted += `**Category**: ${discussion.category}\n`;
  formatted += `**URL**: ${window.location.href}\n`;

  if (includeTimestamp) {
    formatted += `**Captured**: ${new Date().toISOString()}\n\n`;
  } else {
    formatted += '\n';
  }

  formatted += '---\n\n';

  formatted += '## Description\n\n';
  formatted += discussion.body + '\n\n';
  formatted += '---\n\n';

  if (discussion.replies.length > 0) {
    formatted += `## Replies (${discussion.replies.length})\n\n`;

    discussion.replies.forEach((reply, index) => {
      formatted += `### Reply ${index + 1} by @${reply.author}\n\n`;
      formatted += reply.content + '\n\n';
      formatted += '---\n\n';
    });
  }

  return formatted;
}

/**
 * Detect privacy-sensitive content in text
 */
function detectSensitiveContent(text) {
  const lowerText = text.toLowerCase();

  // API keys, tokens, credentials
  const credentialPatterns = [
    /api[_-]?key/i,
    /secret[_-]?key/i,
    /access[_-]?token/i,
    /password/i,
    /credential/i,
    /ghp_[a-zA-Z0-9]{36}/, // GitHub personal access token
    /sk[_-][a-zA-Z0-9]{32}/, // Secret key pattern
    /AWS/i,
    /-----BEGIN.*KEY-----/
  ];

  for (const pattern of credentialPatterns) {
    if (pattern.test(text)) {
      return { sensitive: true, reason: 'credentials' };
    }
  }

  // Email addresses
  if (/@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}/.test(text)) {
    return { sensitive: true, reason: 'email' };
  }

  // Internal/private mentions
  if (lowerText.includes('internal') || lowerText.includes('confidential') || lowerText.includes('private')) {
    return { sensitive: true, reason: 'internal' };
  }

  return { sensitive: false };
}

/**
 * Generate tags for GitHub content
 */
function generateTags(data, pageType, repo) {
  const tags = ['github', pageType, 'auto-captured'];

  // Add repo name as tag
  tags.push(repo.full_name.replace('/', '-'));

  // Add labels as tags
  if (data.labels && data.labels.length > 0) {
    data.labels.forEach(label => {
      tags.push(label.toLowerCase().replace(/\s+/g, '-'));
    });
  }

  // Add state
  if (data.state) {
    tags.push(data.state);
  }

  // Topic detection from title and body
  const fullText = (data.title + ' ' + data.body).toLowerCase();

  if (fullText.match(/\b(bug|error|crash|issue|problem|fix)\b/)) {
    tags.push('bug');
  }
  if (fullText.match(/\b(feature|enhancement|improvement|add|implement)\b/)) {
    tags.push('feature');
  }
  if (fullText.match(/\b(documentation|docs|readme)\b/)) {
    tags.push('documentation');
  }
  if (fullText.match(/\b(test|testing|spec)\b/)) {
    tags.push('testing');
  }
  if (fullText.match(/\b(refactor|cleanup|optimize)\b/)) {
    tags.push('refactoring');
  }

  return [...new Set(tags)]; // Remove duplicates
}

/**
 * Capture current page (issue/PR/discussion)
 */
async function capturePage() {
  if (!captureEnabled) {
    console.log('[ACMS GitHub] Capture disabled, skipping');
    return;
  }

  const pageType = detectPageType();
  if (!pageType) {
    console.log('[ACMS GitHub] Not an issue/PR/discussion page, skipping');
    return;
  }

  const repo = getRepoInfo();
  if (!repo) {
    console.log('[ACMS GitHub] Could not extract repo info, skipping');
    return;
  }

  // Extract content based on page type
  let data;
  let content;
  let contentForComparison;

  if (pageType === 'issue') {
    data = extractIssue();
    content = formatIssue(data, repo, true); // With timestamp for storage
    contentForComparison = formatIssue(data, repo, false); // Without timestamp for duplicate detection
  } else if (pageType === 'pull_request') {
    data = extractPullRequest();
    content = formatPullRequest(data, repo, true);
    contentForComparison = formatPullRequest(data, repo, false);
  } else if (pageType === 'discussion') {
    data = extractDiscussion();
    content = formatDiscussion(data, repo, true);
    contentForComparison = formatDiscussion(data, repo, false);
  }

  if (!content || content.length < 100) {
    console.log('[ACMS GitHub] Content too short or empty, skipping');
    return;
  }

  // Skip if content hasn't changed (compare without timestamp)
  if (contentForComparison === lastCapturedContent) {
    console.log('[ACMS GitHub] Content unchanged, skipping duplicate capture');
    return;
  }

  lastCapturedContent = contentForComparison;

  // Check for sensitive content
  const sensitivityCheck = detectSensitiveContent(content);

  // Generate tags
  const tags = generateTags(data, pageType, repo);

  // Prepare memory data
  const memoryData = {
    content: content,
    tags: tags,
    phase: 'development',
    tier: 'SHORT',
    metadata: {
      source: 'github',
      type: pageType,
      repository: repo.full_name,
      number: data.number || '',
      state: data.state || '',
      labels: data.labels || [],
      is_private_repo: isPrivateRepo(),
      comment_count: data.commentCount || data.replyCount || 0,
      url: window.location.href,
      captured_at: new Date().toISOString(),
      sensitive_content: sensitivityCheck.sensitive ? sensitivityCheck.reason : null
    }
  };

  // Add privacy hint if private repo or sensitive content
  if (isPrivateRepo() || sensitivityCheck.sensitive) {
    memoryData.metadata.privacy_hint = 'CONFIDENTIAL';
  }

  console.log('[ACMS GitHub] Sending to background for storage:', {
    type: pageType,
    repo: repo.full_name,
    tags: tags.length,
    contentLength: content.length,
    sensitive: sensitivityCheck.sensitive
  });

  // Send to background script
  chrome.runtime.sendMessage({
    type: 'capture-conversation',
    data: memoryData
  }, (response) => {
    if (chrome.runtime.lastError) {
      console.error('[ACMS GitHub] Error sending message:', chrome.runtime.lastError);
      return;
    }

    if (response && response.success) {
      console.log('[ACMS GitHub] Capture successful:', response.memoryId);

      // Update stats
      captureStats.totalCaptures++;
      captureStats.lastCaptureTime = new Date().toISOString();
      captureStats.lastItemId = data.number;
      chrome.storage.local.set({ captureStats });
    } else {
      console.error('[ACMS GitHub] Capture failed:', response?.error);
    }
  });
}

/**
 * Start monitoring page
 */
function startMonitoring() {
  console.log('[ACMS GitHub] Starting page monitoring');

  // Initial capture after page load
  setTimeout(() => {
    capturePage();
  }, 2000);

  // Re-capture when comments added (check every 5 seconds)
  setInterval(() => {
    capturePage();
  }, 5000);

  // Handle SPA navigation
  let lastUrl = window.location.href;
  setInterval(() => {
    if (window.location.href !== lastUrl) {
      lastUrl = window.location.href;
      lastCapturedContent = ''; // Reset on navigation
      console.log('[ACMS GitHub] Navigation detected, resetting capture');

      // Capture new page after navigation
      setTimeout(() => {
        capturePage();
      }, 2000);
    }
  }, 500);
}

// Listen for manual capture requests from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'capture-now') {
    console.log('[ACMS GitHub] Manual capture requested');
    lastCapturedContent = ''; // Force capture even if content same
    capturePage();
    sendResponse({ success: true });
  }
  return true; // Keep channel open for async response
});

// Start monitoring when page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', startMonitoring);
} else {
  startMonitoring();
}

console.log('[ACMS GitHub] Content script initialized');
