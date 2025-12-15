# Jenkins Agent for ECS Fargate
# Multi-stage build to keep runtime image small

# ===========================================
# Stage 1: Builder - install tooling
# ===========================================
FROM amazonlinux:2023 AS builder

RUN dnf update -y && \
    dnf install -y --allowerasing \
    curl \
    tar \
    gzip \
    unzip && \
    dnf clean all

# AWS CLI v2
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install --install-dir /opt/aws-cli --bin-dir /opt/aws-cli/bin && \
    rm -rf aws awscliv2.zip

# Pulumi CLI
RUN curl -fsSL https://get.pulumi.com/releases/sdk/pulumi-v3.115.0-linux-x64.tar.gz \
    | tar -xz -C /opt

# ===========================================
# Stage 2: Runtime - final image
# ===========================================
FROM amazoncorretto:21-al2023

LABEL maintainer="DevOps Team"
LABEL description="Jenkins Agent for ECS Fargate"
LABEL version="1.0.0"

ENV JENKINS_AGENT_HOME=/home/jenkins
ENV JAVA_HOME=/usr/lib/jvm/java-21-amazon-corretto

# Runtime dependencies
RUN dnf update -y && \
    dnf install -y --allowerasing \
    git \
    jq \
    docker \
    python3 \
    python3-pip \
    shadow-utils \
    tar \
    gzip \
    openssh-clients && \
    dnf clean all && \
    rm -rf /var/cache/dnf

# Node.js 20
RUN curl -fsSL https://rpm.nodesource.com/setup_20.x | bash - && \
    dnf install -y nodejs && \
    npm install -g npm@latest

# AWS CLI from builder
COPY --from=builder /opt/aws-cli /opt/aws-cli
RUN ln -s /opt/aws-cli/bin/aws /usr/local/bin/aws && \
    ln -s /opt/aws-cli/bin/aws_completer /usr/local/bin/aws_completer

# Pulumi from builder
COPY --from=builder /opt/pulumi /opt/pulumi
RUN ln -s /opt/pulumi/pulumi /usr/local/bin/pulumi

# Ansible
RUN pip3 install --no-cache-dir ansible boto3 botocore

# Jenkins user
RUN groupadd -g 1000 jenkins && \
    useradd -u 1000 -g jenkins -d ${JENKINS_AGENT_HOME} -m jenkins && \
    mkdir -p ${JENKINS_AGENT_HOME}/.jenkins && \
    chown -R jenkins:jenkins ${JENKINS_AGENT_HOME}

# Jenkins remoting jar
ARG JENKINS_REMOTING_VERSION=3206.vb_15dcf73f6a_9
RUN curl -fsSL https://repo.jenkins-ci.org/public/org/jenkins-ci/main/remoting/${JENKINS_REMOTING_VERSION}/remoting-${JENKINS_REMOTING_VERSION}.jar \
    -o ${JENKINS_AGENT_HOME}/agent.jar && \
    chown jenkins:jenkins ${JENKINS_AGENT_HOME}/agent.jar

# Optional Docker group membership (DinD scenarios)
RUN usermod -aG docker jenkins || true

# Entrypoint
COPY --chown=jenkins:jenkins entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER jenkins
WORKDIR ${JENKINS_AGENT_HOME}

# Quick sanity check (fail fast if any tool missing)
RUN java -version && \
    git --version && \
    node --version && \
    npm --version && \
    python3 --version && \
    aws --version && \
    pulumi version && \
    ansible --version

ENTRYPOINT ["/entrypoint.sh"]
