#!/bin/bash
# Enable logging
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
set -x
#---------------------------------------
# Configure /tmp size
#---------------------------------------
# Add tmpfs configuration to /etc/fstab
echo "tmpfs    /tmp    tmpfs    rw,nosuid,nodev,size=5G    0 0" >> /etc/fstab
# Remount /tmp with new size
mount -o remount,size=5G /tmp            
#---------------------------------------
# Swap Configuration
#---------------------------------------
# Create 4GB swap file
dd if=/dev/zero of=/swapfile bs=128M count=32
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile swap swap defaults 0 0' >> /etc/fstab
#---------------------------------------
# System Update & Package Installation
#---------------------------------------
# Update system packages
dnf update -y

# Install base packages (Javaを除く)
dnf install -y \
  docker \
  git \
  jq \
  openssh-server \
  aws-cli
  
# Install additional development packages
dnf groupinstall -y "Development Tools"
dnf install -y python3-pip nodejs

#---------------------------------------
# Docker Configuration
#---------------------------------------
# Configure Docker daemon
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "live-restore": true,
  "group": "docker"
}
EOF

# Start Docker
systemctl enable docker
systemctl start docker

# Create jenkins user
useradd -m -d /home/jenkins -s /bin/bash jenkins
usermod -aG docker jenkins
chmod 666 /var/run/docker.sock

# Wait for Docker
timeout 30 bash -c 'until docker info >/dev/null 2>&1; do sleep 2; done'

#---------------------------------------
# Jenkins Directory Setup
#---------------------------------------
mkdir -p /home/jenkins/agent
chown -R jenkins:jenkins /home/jenkins
chmod 755 /home/jenkins/agent

#---------------------------------------
# SSH Configuration
#---------------------------------------
mkdir -p /home/jenkins/.ssh
chmod 700 /home/jenkins/.ssh
cp /home/ec2-user/.ssh/authorized_keys /home/jenkins/.ssh/
chmod 600 /home/jenkins/.ssh/authorized_keys
chown -R jenkins:jenkins /home/jenkins/.ssh

systemctl restart sshd

#---------------------------------------
# Final Docker Verification
#---------------------------------------
echo "Verifying Docker setup..."
docker info >/dev/null 2>&1 && \
  echo "Docker is operational" || \
  echo "Docker verification failed"

#---------------------------------------
# Install Java (必ず最後に実施)
#---------------------------------------
echo "Starting Java installation..."
dnf install -y java-17-amazon-corretto

# Final verification
echo "Setup complete. Verifying installations..."
java -version
docker --version
