# リカバリーモードの設定
echo "Configuring Jenkins recovery mode..."

# 既存のJCasC設定をクリーンアップ
rm -f /mnt/efs/jenkins/jenkins.yaml
rm -f /mnt/efs/jenkins/casc*.yaml

# 初期セキュリティ設定
cat > /mnt/efs/jenkins/init.groovy.d/basic-security.groovy << 'EOF'
${recoveryModeGroovy}
EOF
