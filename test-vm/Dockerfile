# =============================================================================
# ACMS Test VM - Ubuntu Desktop with Docker
# =============================================================================
# This creates a Linux VM with a desktop environment for testing ACMS installation.
#
# Usage:
#   docker build -t acms-test-vm ./test-vm
#   docker run -d -p 6080:80 -p 5900:5900 --name acms-test acms-test-vm
#   Open: http://localhost:6080 (web-based VNC)
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
    # Docker
    docker.io \
    docker-compose \
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

# VNC startup script
RUN echo '#!/bin/bash\n\
export USER=acms\n\
export HOME=/home/acms\n\
cd $HOME\n\
vncserver :1 -geometry 1280x800 -depth 24 -localhost no &\n\
sleep 2\n\
websockify --web=/usr/share/novnc/ 80 localhost:5901 &\n\
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

# Create test instructions on desktop
RUN echo '#!/bin/bash\n\
# ACMS Installation Test\n\
# ----------------------\n\
# Run these commands to test the installation:\n\
\n\
# 1. Clone the repo\n\
git clone https://github.com/rajan-cforge/acms-os.git\n\
cd acms-os\n\
\n\
# 2. Run installer\n\
./install.sh\n\
\n\
# 3. Open browser to http://localhost:40080\n\
firefox http://localhost:40080 &\n\
' > /home/$USER/Desktop/test-acms.sh && \
    chmod +x /home/$USER/Desktop/test-acms.sh && \
    chown -R $USER:$USER /home/$USER/Desktop

EXPOSE 80 5900 5901

USER root
CMD ["/startup.sh"]
