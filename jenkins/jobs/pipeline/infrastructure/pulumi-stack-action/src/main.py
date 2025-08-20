#!/usr/bin/env python3
"""
Pulumi Deployment Report Generator - Main Entry Point
"""

import argparse
import numpy as np  # matplotlib用のグローバルインポート

from report_generator import PulumiReportGenerator


def main():
    parser = argparse.ArgumentParser(description='Generate Pulumi deployment report')
    parser.add_argument('--artifacts-dir', required=True, help='Directory containing JSON artifacts')
    parser.add_argument('--output-dir', required=True, help='Output directory for HTML report')
    parser.add_argument('--template-dir', required=True, help='Template directory')
    parser.add_argument('--stack-name', required=True, help='Pulumi stack name')
    parser.add_argument('--project-path', required=True, help='Pulumi project path')
    parser.add_argument('--branch', required=True, help='Git branch')
    parser.add_argument('--build-number', required=True, help='Jenkins build number')
    parser.add_argument('--timestamp', required=True, help='Build timestamp')
    parser.add_argument('--action-type', default='deploy', help='Action type (deploy/destroy)')
    
    args = parser.parse_args()
    
    generator = PulumiReportGenerator(args)
    generator.generate_report()


if __name__ == '__main__':
    main()
