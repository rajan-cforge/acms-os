# =============================================================================
# ACMS Test VM - Ubuntu Desktop with Docker-in-Docker
# =============================================================================
# This creates a fully isolated Linux VM with its own Docker daemon
# for testing ACMS installation (simulates a fresh laptop).
#
# Usage:
#   cd test-vm && docker compose up -d --build
#   Open: http://localhost:6080 (web-based VNC)
#   Login: acms / acms123
# =============================================================================

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV USER=acms
ENV PASSWORD=acms123

# Install desktop environment and tools
RUN apt-get update && apt-get install -y \
    # Desktop environment (lightweight)
    xfce4 \
    xfce4-goodies \
    # VNC server
    tigervnc-standalone-server \
    tigervnc-common \
    # noVNC for web access
    novnc \
    websockify \
    # Development tools
    git \
    curl \
    wget \
    vim \
    nano \
    # Docker dependencies
    ca-certificates \
    gnupg \
    lsb-release \
    iptables \
    # Node.js for desktop app
    nodejs \
    npm \
    # Python
    python3 \
    python3-pip \
    # Firefox for web testing
    firefox \
    # Utilities
    sudo \
    dbus-x11 \
    xterm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CE (for Docker-in-Docker)
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create user
RUN useradd -m -s /bin/bash $USER && \
    echo "$USER:$PASSWORD" | chpasswd && \
    adduser $USER sudo && \
    adduser $USER docker && \
    echo "$USER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Setup VNC
RUN mkdir -p /home/$USER/.vnc && \
    echo "$PASSWORD" | vncpasswd -f > /home/$USER/.vnc/passwd && \
    chmod 600 /home/$USER/.vnc/passwd && \
    chown -R $USER:$USER /home/$USER/.vnc

# Startup script (starts Docker daemon + VNC)
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Fix permissions for home directory (needed when volume is mounted)\n\
chown -R acms:acms /home/acms\n\
rm -f /home/acms/.Xauthority /home/acms/.ICEauthority 2>/dev/null\n\
\n\
# Start Docker daemon in background\n\
echo "Starting Docker daemon..."\n\
dockerd > /var/log/dockerd.log 2>&1 &\n\
\n\
# Wait for Docker to be ready\n\
for i in {1..30}; do\n\
    if docker info > /dev/null 2>&1; then\n\
        echo "Docker is ready!"\n\
        break\n\
    fi\n\
    echo "Waiting for Docker... ($i/30)"\n\
    sleep 2\n\
done\n\
\n\
# Start VNC server as acms user\n\
export USER=acms\n\
export HOME=/home/acms\n\
cd $HOME\n\
su - acms -c "vncserver :1 -geometry 1280x800 -depth 24 -localhost no" &\n\
sleep 3\n\
\n\
# Start noVNC web interface\n\
websockify --web=/usr/share/novnc/ 80 localhost:5901 &\n\
\n\
echo ""\n\
echo "========================================"\n\
echo "  ACMS Test VM is ready!"\n\
echo "  Open: http://localhost:6080"\n\
echo "  Login: acms / acms123"\n\
echo "========================================"\n\
echo ""\n\
\n\
tail -f /dev/null' > /startup.sh && chmod +x /startup.sh

# VNC xstartup
RUN echo '#!/bin/bash\n\
unset SESSION_MANAGER\n\
unset DBUS_SESSION_BUS_ADDRESS\n\
exec startxfce4' > /home/$USER/.vnc/xstartup && \
    chmod +x /home/$USER/.vnc/xstartup && \
    chown -R $USER:$USER /home/$USER/.vnc

# Create desktop shortcut for terminal
RUN mkdir -p /home/$USER/Desktop && \
    echo '[Desktop Entry]\n\
Version=1.0\n\
Type=Application\n\
Name=Terminal\n\
Exec=xfce4-terminal\n\
Icon=utilities-terminal\n\
Terminal=false' > /home/$USER/Desktop/terminal.desktop && \
    chmod +x /home/$USER/Desktop/terminal.desktop && \
    chown -R $USER:$USER /home/$USER/Desktop

# Create install script on desktop
RUN echo '#!/bin/bash\n\
echo "=== ACMS Fresh Install Test ==="\n\
echo ""\n\
cd ~\n\
rm -rf acms-os 2>/dev/null\n\
\n\
echo "1. Cloning ACMS from GitHub..."\n\
git clone https://github.com/rajan-cforge/acms-os.git\n\
cd acms-os\n\
\n\
echo ""\n\
echo "2. Running installer..."\n\
./install.sh\n\
\n\
echo ""\n\
echo "3. Opening browser..."\n\
firefox http://localhost:40080 &\n\
' > /home/$USER/Desktop/install-acms.sh && \
    chmod +x /home/$USER/Desktop/install-acms.sh && \
    chown -R $USER:$USER /home/$USER/Desktop

# Create README on desktop
RUN echo 'ACMS Test VM\n\
============\n\
\n\
To test ACMS installation:\n\
\n\
1. Open Terminal (double-click icon)\n\
2. Run: ~/Desktop/install-acms.sh\n\
   OR manually:\n\
   git clone https://github.com/rajan-cforge/acms-os.git\n\
   cd acms-os\n\
   ./install.sh\n\
\n\
3. Access ACMS at http://localhost:40080\n\
' > /home/$USER/Desktop/README.txt && \
    chown $USER:$USER /home/$USER/Desktop/README.txt

EXPOSE 80 5900 5901

USER root
CMD ["/startup.sh"]
