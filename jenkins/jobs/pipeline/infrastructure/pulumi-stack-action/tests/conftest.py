"""
pytest configuration and fixtures for pulumi-stack-action tests

このファイルはpytestの設定と共通フィクスチャを提供します。
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List

import pytest


# Add src directory to Python path for imports
_src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(_src_dir))


@pytest.fixture
def fixtures_dir() -> Path:
    """テストフィクスチャディレクトリのパスを返す"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_urns(fixtures_dir: Path) -> Dict:
    """サンプルURNデータを読み込む

    Returns:
        サンプルURN辞書
        {
            'valid_urns': List[Dict],
            'edge_case_urns': List[Dict],
            'special_character_urns': List[Dict]
        }
    """
    with open(fixtures_dir / "sample_urns.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_dot_files_dir(fixtures_dir: Path) -> Path:
    """サンプルDOTファイルディレクトリのパスを返す"""
    return fixtures_dir / "sample_dot_files"


@pytest.fixture
def simple_graph_content(sample_dot_files_dir: Path) -> str:
    """単純なDOTグラフのコンテンツを返す"""
    with open(sample_dot_files_dir / "simple_graph.dot", "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def complex_graph_content(sample_dot_files_dir: Path) -> str:
    """複雑なDOTグラフのコンテンツを返す"""
    with open(sample_dot_files_dir / "complex_graph.dot", "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def sample_urn_info() -> Dict[str, str]:
    """標準的なURN情報の辞書を返す

    Returns:
        URN情報辞書（parse_urn()の戻り値形式）
    """
    return {
        'stack': 'dev',
        'project': 'myproject',
        'provider': 'aws',
        'module': 'ec2',
        'type': 'Instance',
        'name': 'webserver',
        'full_urn': 'urn:pulumi:dev::myproject::aws:ec2/instance:Instance::webserver'
    }


@pytest.fixture
def sample_resources() -> List[Dict]:
    """単純な依存関係を持つリソースリストを返す

    Returns:
        リソース情報のリスト
    """
    return [
        {
            'urn': 'urn:pulumi:dev::project::aws:ec2/instance:Instance::web',
            'dependencies': ['urn:pulumi:dev::project::aws:ec2/securityGroup:SecurityGroup::sg']
        },
        {
            'urn': 'urn:pulumi:dev::project::aws:ec2/securityGroup:SecurityGroup::sg',
            'dependencies': []
        }
    ]


@pytest.fixture
def complex_resources() -> List[Dict]:
    """複雑な依存関係（親リソース + プロパティ依存）を持つリソースリストを返す

    Returns:
        リソース情報のリスト
    """
    return [
        {
            'urn': 'urn:pulumi:prod::app::aws:ec2/vpc:Vpc::main',
            'dependencies': []
        },
        {
            'urn': 'urn:pulumi:prod::app::aws:ec2/subnet:Subnet::public',
            'parent': 'urn:pulumi:prod::app::aws:ec2/vpc:Vpc::main',
            'propertyDependencies': {
                'vpcId': ['urn:pulumi:prod::app::aws:ec2/vpc:Vpc::main']
            },
            'dependencies': []
        },
        {
            'urn': 'urn:pulumi:prod::app::aws:ec2/instance:Instance::web',
            'propertyDependencies': {
                'subnetId': ['urn:pulumi:prod::app::aws:ec2/subnet:Subnet::public'],
                'vpcSecurityGroupIds': [
                    'urn:pulumi:prod::app::aws:ec2/securityGroup:SecurityGroup::web-sg'
                ]
            },
            'dependencies': [
                'urn:pulumi:prod::app::aws:ec2/subnet:Subnet::public'
            ]
        },
        {
            'urn': 'urn:pulumi:prod::app::aws:ec2/securityGroup:SecurityGroup::web-sg',
            'parent': 'urn:pulumi:prod::app::aws:ec2/vpc:Vpc::main',
            'dependencies': []
        }
    ]
