const { app, BrowserWindow, Tray, Menu, ipcMain } = require('electron');
const path = require('path');

let mainWindow = null;
let tray = null;
const ACMS_API = 'http://localhost:40080';

// Create the main window
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 700,
    minWidth: 600,
    minHeight: 400,
    title: 'ACMS - Adaptive Context Memory System',
    webPreferences: {
      nodeIntegration: true,  // Required for current renderer architecture
      contextIsolation: false, // TODO: Migrate to contextIsolation: true with preload
      // Note: Full security hardening requires refactoring renderer to use contextBridge
      // See preload.js for the secure API pattern when ready to migrate
    },
    icon: path.join(__dirname, 'assets', 'icon.png')
  });

  mainWindow.loadFile('index.html');

  // Open DevTools in development mode
  if (process.argv.includes('--inspect')) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('close', (event) => {
    // Hide instead of closing on macOS
    if (process.platform === 'darwin' && !app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Create system tray
function createTray() {
  // Create a simple colored icon for the tray (fallback if no icon exists)
  const iconPath = path.join(__dirname, 'assets', 'tray-icon.png');

  // For now, use a native image if icon file doesn't exist
  const { nativeImage } = require('electron');
  const fs = require('fs');

  let trayIcon;
  if (fs.existsSync(iconPath)) {
    trayIcon = iconPath;
  } else {
    // Create a simple template icon (macOS will colorize it automatically)
    trayIcon = nativeImage.createEmpty();
  }

  tray = new Tray(trayIcon);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show ACMS',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        } else {
          createWindow();
        }
      }
    },
    { type: 'separator' },
    {
      label: 'Quick Search',
      accelerator: 'CmdOrCtrl+Shift+F',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
          mainWindow.webContents.send('focus-search');
        }
      }
    },
    {
      label: 'Store Memory',
      accelerator: 'CmdOrCtrl+Shift+S',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
          mainWindow.webContents.send('open-store');
        }
      }
    },
    { type: 'separator' },
    {
      label: 'View Stats',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
          mainWindow.webContents.send('show-stats');
        }
      }
    },
    { type: 'separator' },
    {
      label: 'Settings',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
          mainWindow.webContents.send('open-settings');
        }
      }
    },
    { type: 'separator' },
    {
      label: 'Developer Tools',
      accelerator: 'CmdOrCtrl+Shift+I',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
          mainWindow.webContents.toggleDevTools();
        }
      }
    },
    { type: 'separator' },
    {
      label: 'Quit ACMS',
      accelerator: 'CmdOrCtrl+Q',
      click: () => {
        app.isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray.setToolTip('ACMS - Memory System');
  tray.setContextMenu(contextMenu);

  // Click on tray icon shows window
  tray.on('click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    } else {
      createWindow();
    }
  });
}

// Check ACMS API health
async function checkAPIHealth() {
  try {
    const response = await fetch(`${ACMS_API}/health`);
    if (response.ok) {
      const data = await response.json();
      return { status: 'connected', data };
    }
    return { status: 'error', error: 'API not responding' };
  } catch (error) {
    return { status: 'disconnected', error: error.message };
  }
}

// IPC handlers
ipcMain.handle('get-memories', async (event, limit = 20, source = '') => {
  try {
    // Build query params
    let url = `${ACMS_API}/memories?limit=${limit}`;
    if (source) {
      url += `&source=${encodeURIComponent(source)}`;
    }

    const response = await fetch(url);
    if (response.ok) {
      return await response.json();
    }
    throw new Error(`API returned ${response.status}`);
  } catch (error) {
    console.error('Error fetching memories:', error);
    return { error: error.message };
  }
});

ipcMain.handle('search-memories', async (event, query, limit = 10) => {
  try {
    const response = await fetch(`${ACMS_API}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, limit })
    });
    if (response.ok) {
      return await response.json();
    }
    throw new Error(`API returned ${response.status}`);
  } catch (error) {
    console.error('Error searching memories:', error);
    return { error: error.message };
  }
});

ipcMain.handle('store-memory', async (event, memoryData) => {
  try {
    const response = await fetch(`${ACMS_API}/memories`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(memoryData)
    });
    if (response.ok) {
      return await response.json();
    }
    throw new Error(`API returned ${response.status}`);
  } catch (error) {
    console.error('Error storing memory:', error);
    return { error: error.message };
  }
});

ipcMain.handle('get-stats', async () => {
  try {
    const response = await fetch(`${ACMS_API}/stats`);
    if (response.ok) {
      return await response.json();
    }
    throw new Error(`API returned ${response.status}`);
  } catch (error) {
    console.error('Error fetching stats:', error);
    return { error: error.message };
  }
});

ipcMain.handle('get-memory', async (event, memoryId) => {
  try {
    const response = await fetch(`${ACMS_API}/memories/${memoryId}`);
    if (response.ok) {
      return await response.json();
    }
    throw new Error(`API returned ${response.status}`);
  } catch (error) {
    console.error('Error fetching memory:', error);
    return { error: error.message };
  }
});

ipcMain.handle('delete-memory', async (event, memoryId) => {
  try {
    const response = await fetch(`${ACMS_API}/memories/${memoryId}`, {
      method: 'DELETE'
    });
    if (response.ok) {
      return await response.json();
    }
    throw new Error(`API returned ${response.status}`);
  } catch (error) {
    console.error('Error deleting memory:', error);
    return { error: error.message };
  }
});

ipcMain.handle('check-health', async () => {
  return await checkAPIHealth();
});

// Get conversation threads
ipcMain.handle('get-conversations', async (event, options = {}) => {
  try {
    const {
      source = '',
      limit = 50,
      offset = 0
    } = options;

    // Build query params
    let url = `${ACMS_API}/conversations?limit=${limit}&offset=${offset}`;
    if (source) {
      url += `&source=${encodeURIComponent(source)}`;
    }

    const response = await fetch(url);
    if (response.ok) {
      return await response.json();
    }
    throw new Error(`API returned ${response.status}`);
  } catch (error) {
    console.error('Error fetching conversations:', error);
    return { error: error.message };
  }
});

// Get conversation thread with turns
ipcMain.handle('get-conversation', async (event, threadId) => {
  try {
    const response = await fetch(`${ACMS_API}/conversations/${threadId}`);
    if (response.ok) {
      return await response.json();
    }
    throw new Error(`API returned ${response.status}`);
  } catch (error) {
    console.error('Error fetching conversation:', error);
    return { error: error.message };
  }
});

// App lifecycle
app.whenReady().then(() => {
  createWindow();
  createTray();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });

  // Check API health on startup
  checkAPIHealth().then((health) => {
    console.log('ACMS API Health:', health);
    if (mainWindow) {
      mainWindow.webContents.send('api-health', health);
    }
  });
});

app.on('window-all-closed', () => {
  // Keep app running in tray on macOS
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  app.isQuitting = true;
});
