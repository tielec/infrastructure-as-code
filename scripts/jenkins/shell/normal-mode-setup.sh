# 通常モードの設定
echo "Configuring Jenkins normal mode..."

# 既存のgroovyスクリプトをクリーンアップ
rm -f /mnt/efs/jenkins/init.groovy.d/*.groovy

# CLI無効化スクリプト
cat > /mnt/efs/jenkins/init.groovy.d/disable-cli.groovy << 'EOF'
${disableCliGroovy}
EOF

# 基本設定スクリプト
cat > /mnt/efs/jenkins/init.groovy.d/basic-settings.groovy << 'EOF'
${basicSettingsGroovy}
EOF
