// Plaid OAuth Callback Handler for ACMS
// This endpoint receives the OAuth redirect from Plaid after bank authentication

export default function handler(req, res) {
  // Get OAuth state from query params
  const { oauth_state_id } = req.query;

  // Log for debugging
  console.log('OAuth callback received:', { oauth_state_id });

  // Return an HTML page that:
  // 1. Shows success message
  // 2. Provides the receivedRedirectUri for Plaid Link to resume
  // 3. Attempts to communicate with the Electron app

  const currentUrl = `https://${req.headers.host}${req.url}`;

  const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ACMS - Account Connected</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #fff;
        }
        .container {
            text-align: center;
            padding: 40px;
            max-width: 500px;
        }
        .success-icon {
            font-size: 64px;
            margin-bottom: 20px;
        }
        h1 {
            color: #4CAF50;
            margin-bottom: 16px;
            font-size: 28px;
        }
        p {
            color: #b0b0b0;
            margin-bottom: 12px;
            line-height: 1.6;
        }
        .instructions {
            background: rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 24px;
            margin-top: 24px;
        }
        .instructions h2 {
            font-size: 18px;
            margin-bottom: 12px;
            color: #fff;
        }
        .instructions ol {
            text-align: left;
            padding-left: 20px;
        }
        .instructions li {
            margin-bottom: 8px;
            color: #ccc;
        }
        .state-id {
            font-family: monospace;
            background: rgba(76, 175, 80, 0.2);
            border: 1px solid #4CAF50;
            padding: 12px 20px;
            border-radius: 8px;
            margin-top: 20px;
            font-size: 12px;
            word-break: break-all;
            color: #4CAF50;
        }
        .copy-btn {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 20px;
            transition: background 0.2s;
        }
        .copy-btn:hover {
            background: #45a049;
        }
        .copy-btn:active {
            transform: scale(0.98);
        }
        .copied {
            color: #4CAF50;
            margin-top: 8px;
            opacity: 0;
            transition: opacity 0.3s;
        }
        .copied.show {
            opacity: 1;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="success-icon">✅</div>
        <h1>Bank Authentication Complete!</h1>
        <p>You've successfully authenticated with your financial institution.</p>

        <div class="instructions">
            <h2>Next Steps:</h2>
            <ol>
                <li>Return to the <strong>ACMS desktop app</strong></li>
                <li>Click <strong>"Connect Account"</strong> again</li>
                <li>The connection will complete automatically</li>
            </ol>
        </div>

        <div class="state-id" id="redirect-uri">
            ${currentUrl}
        </div>

        <button class="copy-btn" onclick="copyUri()">Copy Redirect URI</button>
        <p class="copied" id="copied-msg">Copied to clipboard!</p>
    </div>

    <script>
        // Store the redirect URI for the Electron app to retrieve
        const redirectUri = '${currentUrl}';
        const oauthStateId = '${oauth_state_id || ''}';

        // Try to communicate with opener window (if opened as popup)
        if (window.opener) {
            try {
                window.opener.postMessage({
                    type: 'plaid-oauth-complete',
                    oauth_state_id: oauthStateId,
                    receivedRedirectUri: redirectUri
                }, '*');
            } catch (e) {
                console.log('Could not post message to opener:', e);
            }
        }

        // Store in localStorage for the app to retrieve
        try {
            localStorage.setItem('acms_oauth_redirect_uri', redirectUri);
            localStorage.setItem('acms_oauth_state_id', oauthStateId);
            localStorage.setItem('acms_oauth_timestamp', Date.now().toString());
        } catch (e) {
            console.log('LocalStorage not available:', e);
        }

        function copyUri() {
            navigator.clipboard.writeText(redirectUri).then(() => {
                document.getElementById('copied-msg').classList.add('show');
                setTimeout(() => {
                    document.getElementById('copied-msg').classList.remove('show');
                }, 2000);
            });
        }
    </script>
</body>
</html>
  `;

  res.setHeader('Content-Type', 'text/html');
  res.status(200).send(html);
}
