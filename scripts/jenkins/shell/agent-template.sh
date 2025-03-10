#!/bin/bash
# This is a minimal agent setup script template.
# Please customize this file with your specific agent setup requirements.

echo "Starting Jenkins agent setup..."
dnf update -y
dnf install -y java-17-amazon-corretto docker git
systemctl enable docker
systemctl start docker

# Create jenkins user
useradd -m -d /home/jenkins -s /bin/bash jenkins
usermod -aG docker jenkins

mkdir -p /home/jenkins/agent
chown -R jenkins:jenkins /home/jenkins
echo "Jenkins agent setup completed."