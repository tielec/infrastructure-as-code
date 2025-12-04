"""
ResourceDependencyBuilderクラスの単体テスト

このテストスイートはPhase 3のテストシナリオに基づいて実装されています。
テスト戦略: UNIT_INTEGRATION (このファイルはUNITテスト部分)
カバレッジ目標: 80%以上
"""

import pytest
from resource_dependency_builder import ResourceDependencyBuilder


# =============================================================================
# 2.1 URNマッピング作成テスト（TestURNMapping）
# =============================================================================

class TestURNMapping:
    """URNマッピング作成機能のテスト"""

    def test_create_urn_to_node_mapping_正常系_3リソース(self):
        """
        Given: 有効なURNを持つ3個のリソースリストが存在する
        When: create_urn_to_node_mapping()を呼び出す
        Then: 3エントリのマッピング辞書が返される
        """
        # Given
        resources = [
            {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a'},
            {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b'},
            {'urn': 'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc'}
        ]

        # When
        mapping = ResourceDependencyBuilder.create_urn_to_node_mapping(resources)

        # Then
        assert len(mapping) == 3
        assert mapping['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a'] == 'resource_0'
        assert mapping['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b'] == 'resource_1'
        assert mapping['urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc'] == 'resource_2'

    def test_create_urn_to_node_mapping_空リスト(self):
        """
        Given: 空のリソースリスト
        When: create_urn_to_node_mapping()を呼び出す
        Then: 空の辞書が返される
        """
        # Given
        resources = []

        # When
        mapping = ResourceDependencyBuilder.create_urn_to_node_mapping(resources)

        # Then
        assert mapping == {}

    def test_create_urn_to_node_mapping_1リソース(self):
        """
        Given: 有効なURNを持つ1個のリソースリスト
        When: create_urn_to_node_mapping()を呼び出す
        Then: 1エントリのマッピング辞書が返される
        """
        # Given
        resources = [
            {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'}
        ]

        # When
        mapping = ResourceDependencyBuilder.create_urn_to_node_mapping(resources)

        # Then
        assert len(mapping) == 1
        assert mapping['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'] == 'resource_0'

    def test_create_urn_to_node_mapping_重複URN(self):
        """
        Given: 同じURNを持つ2個のリソースリスト
        When: create_urn_to_node_mapping()を呼び出す
        Then: 最後のリソースのノードIDが使用される
        """
        # Given
        resources = [
            {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'},
            {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'}
        ]

        # When
        mapping = ResourceDependencyBuilder.create_urn_to_node_mapping(resources)

        # Then
        assert len(mapping) == 1
        assert mapping['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'] == 'resource_1'

    def test_create_urn_to_node_mapping_urnキーなし(self):
        """
        Given: 'urn'キーを持たないリソースを含むリスト
        When: create_urn_to_node_mapping()を呼び出す
        Then: 空文字列がキーとして扱われ、エラーが発生しない
        """
        # Given
        resources = [
            {'type': 'aws:s3/bucket:Bucket'},  # urnキーなし
            {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b'}
        ]

        # When
        mapping = ResourceDependencyBuilder.create_urn_to_node_mapping(resources)

        # Then
        assert len(mapping) == 2
        assert '' in mapping
        assert mapping[''] == 'resource_0'
        assert mapping['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b'] == 'resource_1'

    def test_create_urn_to_node_mapping_最大20リソース(self):
        """
        Given: ちょうど20個のリソースリスト
        When: create_urn_to_node_mapping()を呼び出す
        Then: 20エントリのマッピング辞書が返される
        """
        # Given
        resources = [
            {'urn': f'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-{i}'}
            for i in range(20)
        ]

        # When
        mapping = ResourceDependencyBuilder.create_urn_to_node_mapping(resources)

        # Then
        assert len(mapping) == 20
        for i in range(20):
            urn = f'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-{i}'
            assert mapping[urn] == f'resource_{i}'


# =============================================================================
# 2.2 直接依存関係追加テスト（TestDirectDependencies）
# =============================================================================

class TestDirectDependencies:
    """直接依存関係追加機能のテスト"""

    def test_add_direct_dependencies_正常系_1依存(self):
        """
        Given: 1個の依存URNを持つリソースとURNマッピングが存在する
        When: _add_direct_dependencies()を呼び出す
        Then: 依存関係のエッジが正しく追加される
        """
        # Given
        node_id = 'resource_1'
        resource = {
            'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a']
        }
        urn_to_node_id = {
            'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a': 'resource_0'
        }
        dot_lines = []

        # When
        ResourceDependencyBuilder._add_direct_dependencies(
            node_id, resource, urn_to_node_id, dot_lines
        )

        # Then
        assert len(dot_lines) == 1
        assert '"resource_1" -> "resource_0"' in dot_lines[0]
        assert 'style=solid' in dot_lines[0]
        assert 'color="#9C27B0"' in dot_lines[0]

    def test_add_direct_dependencies_複数依存_3個(self):
        """
        Given: 3個の依存URNを持つリソース
        When: _add_direct_dependencies()を呼び出す
        Then: 3行の依存関係エッジが追加される
        """
        # Given
        node_id = 'resource_3'
        resource = {
            'dependencies': [
                'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a',
                'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b',
                'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc'
            ]
        }
        urn_to_node_id = {
            'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a': 'resource_0',
            'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b': 'resource_1',
            'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc': 'resource_2'
        }
        dot_lines = []

        # When
        ResourceDependencyBuilder._add_direct_dependencies(
            node_id, resource, urn_to_node_id, dot_lines
        )

        # Then
        assert len(dot_lines) == 3
        for line in dot_lines:
            assert '"resource_3" ->' in line
            assert 'style=solid' in line

    def test_add_direct_dependencies_空依存リスト(self):
        """
        Given: 空の依存リストを持つリソース
        When: _add_direct_dependencies()を呼び出す
        Then: 何も追加されない
        """
        # Given
        node_id = 'resource_1'
        resource = {'dependencies': []}
        urn_to_node_id = {}
        dot_lines = []

        # When
        ResourceDependencyBuilder._add_direct_dependencies(
            node_id, resource, urn_to_node_id, dot_lines
        )

        # Then
        assert len(dot_lines) == 0

    def test_add_direct_dependencies_存在しないURN(self):
        """
        Given: 存在しないURNへの依存を持つリソース
        When: _add_direct_dependencies()を呼び出す
        Then: 存在するURNのみが処理され、存在しないURNはスキップされる
        """
        # Given
        node_id = 'resource_1'
        resource = {
            'dependencies': [
                'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a',  # 存在する
                'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::nonexistent'  # 存在しない
            ]
        }
        urn_to_node_id = {
            'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a': 'resource_0'
        }
        dot_lines = []

        # When
        ResourceDependencyBuilder._add_direct_dependencies(
            node_id, resource, urn_to_node_id, dot_lines
        )

        # Then
        assert len(dot_lines) == 1
        assert '"resource_1" -> "resource_0"' in dot_lines[0]

    def test_add_direct_dependencies_dependenciesキーなし(self):
        """
        Given: 'dependencies'キーを持たないリソース
        When: _add_direct_dependencies()を呼び出す
        Then: 何も追加されず、エラーが発生しない
        """
        # Given
        node_id = 'resource_1'
        resource = {'type': 'aws:s3/bucket:Bucket'}
        urn_to_node_id = {}
        dot_lines = []

        # When
        ResourceDependencyBuilder._add_direct_dependencies(
            node_id, resource, urn_to_node_id, dot_lines
        )

        # Then
        assert len(dot_lines) == 0


# =============================================================================
# 2.3 親依存関係追加テスト（TestParentDependencies）
# =============================================================================

class TestParentDependencies:
    """親依存関係追加機能のテスト"""

    def test_add_parent_dependency_正常系(self):
        """
        Given: 有効な親URNを持つリソースとURNマッピングが存在する
        When: _add_parent_dependency()を呼び出す
        Then: 親依存関係のエッジが正しく追加される
        """
        # Given
        node_id = 'resource_1'
        resource = {
            'parent': 'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc'
        }
        urn_to_node_id = {
            'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc': 'resource_0'
        }
        dot_lines = []

        # When
        ResourceDependencyBuilder._add_parent_dependency(
            node_id, resource, urn_to_node_id, dot_lines
        )

        # Then
        assert len(dot_lines) == 1
        assert '"resource_1" -> "resource_0"' in dot_lines[0]
        assert 'style=dashed' in dot_lines[0]
        assert 'color="#2196F3"' in dot_lines[0]
        assert 'label="parent"' in dot_lines[0]

    def test_add_parent_dependency_parentなし(self):
        """
        Given: parent=Noneのリソース
        When: _add_parent_dependency()を呼び出す
        Then: 何も追加されない
        """
        # Given
        node_id = 'resource_1'
        resource = {'parent': None}
        urn_to_node_id = {}
        dot_lines = []

        # When
        ResourceDependencyBuilder._add_parent_dependency(
            node_id, resource, urn_to_node_id, dot_lines
        )

        # Then
        assert len(dot_lines) == 0

    def test_add_parent_dependency_parent空文字列(self):
        """
        Given: parent=空文字列のリソース
        When: _add_parent_dependency()を呼び出す
        Then: 何も追加されない
        """
        # Given
        node_id = 'resource_1'
        resource = {'parent': ''}
        urn_to_node_id = {}
        dot_lines = []

        # When
        ResourceDependencyBuilder._add_parent_dependency(
            node_id, resource, urn_to_node_id, dot_lines
        )

        # Then
        assert len(dot_lines) == 0

    def test_add_parent_dependency_存在しないURN(self):
        """
        Given: 存在しない親URNを持つリソース
        When: _add_parent_dependency()を呼び出す
        Then: 何も追加されない
        """
        # Given
        node_id = 'resource_1'
        resource = {
            'parent': 'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::nonexistent'
        }
        urn_to_node_id = {
            'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc': 'resource_0'
        }
        dot_lines = []

        # When
        ResourceDependencyBuilder._add_parent_dependency(
            node_id, resource, urn_to_node_id, dot_lines
        )

        # Then
        assert len(dot_lines) == 0

    def test_add_parent_dependency_parentキーなし(self):
        """
        Given: 'parent'キーを持たないリソース
        When: _add_parent_dependency()を呼び出す
        Then: 何も追加されず、エラーが発生しない
        """
        # Given
        node_id = 'resource_1'
        resource = {'type': 'aws:s3/bucket:Bucket'}
        urn_to_node_id = {}
        dot_lines = []

        # When
        ResourceDependencyBuilder._add_parent_dependency(
            node_id, resource, urn_to_node_id, dot_lines
        )

        # Then
        assert len(dot_lines) == 0


# =============================================================================
# 2.4 プロパティ依存関係追加テスト（TestPropertyDependencies）
# =============================================================================

class TestPropertyDependencies:
    """プロパティ依存関係追加機能のテスト"""

    def test_add_property_dependencies_正常系_1プロパティ(self):
        """
        Given: 1個のプロパティ依存を持つリソースとURNマッピングが存在する
        When: _add_property_dependencies()を呼び出す
        Then: プロパティ依存関係のエッジが正しく追加される
        """
        # Given
        node_id = 'resource_1'
        resource = {
            'propertyDependencies': {
                'bucket': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket']
            }
        }
        urn_to_node_id = {
            'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket': 'resource_0'
        }
        dot_lines = []

        # When
        ResourceDependencyBuilder._add_property_dependencies(
            node_id, resource, urn_to_node_id, dot_lines
        )

        # Then
        assert len(dot_lines) == 1
        assert '"resource_1" -> "resource_0"' in dot_lines[0]
        assert 'style=dotted' in dot_lines[0]
        assert 'color="#FF5722"' in dot_lines[0]
        assert 'label="bucket"' in dot_lines[0]

    def test_add_property_dependencies_複数プロパティ_3個(self):
        """
        Given: 3個のプロパティ依存を持つリソース
        When: _add_property_dependencies()を呼び出す
        Then: 3行のプロパティ依存関係エッジが追加される
        """
        # Given
        node_id = 'resource_3'
        resource = {
            'propertyDependencies': {
                'vpcId': ['urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc'],
                'securityGroupIds': [
                    'urn:pulumi:dev::myproject::aws:ec2/securityGroup:SecurityGroup::sg-a',
                    'urn:pulumi:dev::myproject::aws:ec2/securityGroup:SecurityGroup::sg-b'
                ]
            }
        }
        urn_to_node_id = {
            'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc': 'resource_0',
            'urn:pulumi:dev::myproject::aws:ec2/securityGroup:SecurityGroup::sg-a': 'resource_1',
            'urn:pulumi:dev::myproject::aws:ec2/securityGroup:SecurityGroup::sg-b': 'resource_2'
        }
        dot_lines = []

        # When
        ResourceDependencyBuilder._add_property_dependencies(
            node_id, resource, urn_to_node_id, dot_lines
        )

        # Then
        assert len(dot_lines) == 3
        assert 'label="vpcId"' in dot_lines[0]
        assert 'label="securityGroupIds"' in dot_lines[1]
        assert 'label="securityGroupIds"' in dot_lines[2]

    def test_add_property_dependencies_長いプロパティ名(self):
        """
        Given: ドット区切りの長いプロパティ名を持つリソース
        When: _add_property_dependencies()を呼び出す
        Then: 末尾のみがラベルとして使用される
        """
        # Given
        node_id = 'resource_1'
        resource = {
            'propertyDependencies': {
                'vpc.subnet.id': ['urn:pulumi:dev::myproject::aws:ec2/subnet:Subnet::my-subnet']
            }
        }
        urn_to_node_id = {
            'urn:pulumi:dev::myproject::aws:ec2/subnet:Subnet::my-subnet': 'resource_0'
        }
        dot_lines = []

        # When
        ResourceDependencyBuilder._add_property_dependencies(
            node_id, resource, urn_to_node_id, dot_lines
        )

        # Then
        assert len(dot_lines) == 1
        assert 'label="id"' in dot_lines[0]
        assert 'label="vpc.subnet.id"' not in dot_lines[0]

    def test_add_property_dependencies_空辞書(self):
        """
        Given: 空のpropertyDependencies辞書を持つリソース
        When: _add_property_dependencies()を呼び出す
        Then: 何も追加されない
        """
        # Given
        node_id = 'resource_1'
        resource = {'propertyDependencies': {}}
        urn_to_node_id = {}
        dot_lines = []

        # When
        ResourceDependencyBuilder._add_property_dependencies(
            node_id, resource, urn_to_node_id, dot_lines
        )

        # Then
        assert len(dot_lines) == 0

    def test_add_property_dependencies_存在しないURN(self):
        """
        Given: 存在しないURNへのプロパティ依存を持つリソース
        When: _add_property_dependencies()を呼び出す
        Then: 存在するURNのみが処理される
        """
        # Given
        node_id = 'resource_1'
        resource = {
            'propertyDependencies': {
                'vpcId': [
                    'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc',  # 存在する
                    'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::nonexistent'  # 存在しない
                ]
            }
        }
        urn_to_node_id = {
            'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc': 'resource_0'
        }
        dot_lines = []

        # When
        ResourceDependencyBuilder._add_property_dependencies(
            node_id, resource, urn_to_node_id, dot_lines
        )

        # Then
        assert len(dot_lines) == 1
        assert '"resource_1" -> "resource_0"' in dot_lines[0]

    def test_add_property_dependencies_propertyDependenciesキーなし(self):
        """
        Given: 'propertyDependencies'キーを持たないリソース
        When: _add_property_dependencies()を呼び出す
        Then: 何も追加されず、エラーが発生しない
        """
        # Given
        node_id = 'resource_1'
        resource = {'type': 'aws:s3/bucket:Bucket'}
        urn_to_node_id = {}
        dot_lines = []

        # When
        ResourceDependencyBuilder._add_property_dependencies(
            node_id, resource, urn_to_node_id, dot_lines
        )

        # Then
        assert len(dot_lines) == 0


# =============================================================================
# 2.5 リソース依存関係追加テスト（TestResourceDependencies）
# =============================================================================

class TestResourceDependencies:
    """リソース依存関係追加機能（エントリーポイント）のテスト"""

    def test_add_resource_dependencies_正常系_2リソース(self):
        """
        Given: 2個のリソース（1つは依存関係を持つ）
        When: add_resource_dependencies()を呼び出す
        Then: 依存関係エッジが正しく生成される
        """
        # Given
        resources = [
            {
                'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a',
                'dependencies': [],
                'parent': None,
                'propertyDependencies': {}
            },
            {
                'urn': 'urn:pulumi:dev::myproject::aws:s3/bucketObject:BucketObject::my-object',
                'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a'],
                'parent': None,
                'propertyDependencies': {}
            }
        ]
        dot_lines = []

        # When
        ResourceDependencyBuilder.add_resource_dependencies(resources, dot_lines)

        # Then
        assert len(dot_lines) >= 3
        assert dot_lines[0] == ''
        assert '// リソース間の依存関係' in dot_lines[1]
        # 依存関係エッジの確認
        dependency_edges = [line for line in dot_lines if '->' in line]
        assert len(dependency_edges) >= 1
        assert any('"resource_1" -> "resource_0"' in line for line in dependency_edges)

    def test_add_resource_dependencies_空リスト(self):
        """
        Given: 空のリソースリスト
        When: add_resource_dependencies()を呼び出す
        Then: 何も追加されない
        """
        # Given
        resources = []
        dot_lines = []

        # When
        ResourceDependencyBuilder.add_resource_dependencies(resources, dot_lines)

        # Then
        assert len(dot_lines) == 0

    def test_add_resource_dependencies_1リソース(self):
        """
        Given: 1個のリソースリスト
        When: add_resource_dependencies()を呼び出す
        Then: 何も追加されない（依存関係がないため）
        """
        # Given
        resources = [
            {
                'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket',
                'dependencies': [],
                'parent': None,
                'propertyDependencies': {}
            }
        ]
        dot_lines = []

        # When
        ResourceDependencyBuilder.add_resource_dependencies(resources, dot_lines)

        # Then
        assert len(dot_lines) == 0

    def test_add_resource_dependencies_20リソース(self):
        """
        Given: ちょうど20個のリソースリスト（各リソースは前のリソースに依存）
        When: add_resource_dependencies()を呼び出す
        Then: 19個の依存関係エッジが含まれる
        """
        # Given
        resources = []
        for i in range(20):
            urn = f'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-{i}'
            dependencies = []
            if i > 0:
                dependencies = [f'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-{i-1}']
            resources.append({
                'urn': urn,
                'dependencies': dependencies,
                'parent': None,
                'propertyDependencies': {}
            })
        dot_lines = []

        # When
        ResourceDependencyBuilder.add_resource_dependencies(resources, dot_lines)

        # Then
        assert '// リソース間の依存関係' in dot_lines[1]
        dependency_edges = [line for line in dot_lines if '->' in line]
        assert len(dependency_edges) == 19

    def test_add_resource_dependencies_複合シナリオ(self):
        """
        Given: 直接+親+プロパティ依存が混在するリソースリスト
        When: add_resource_dependencies()を呼び出す
        Then: 3種類すべての依存関係エッジが生成される
        """
        # Given
        resources = [
            {
                'urn': 'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc',
                'dependencies': [],
                'parent': None,
                'propertyDependencies': {}
            },
            {
                'urn': 'urn:pulumi:dev::myproject::aws:ec2/subnet:Subnet::my-subnet',
                'dependencies': ['urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc'],
                'parent': 'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc',
                'propertyDependencies': {
                    'vpcId': ['urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc']
                }
            }
        ]
        dot_lines = []

        # When
        ResourceDependencyBuilder.add_resource_dependencies(resources, dot_lines)

        # Then
        assert len(dot_lines) == 5  # 空行、コメント、直接依存、親依存、プロパティ依存
        assert dot_lines[0] == ''
        assert '// リソース間の依存関係' in dot_lines[1]

        # 3種類の依存関係をそれぞれ確認
        edges = dot_lines[2:]
        assert any('style=solid' in line for line in edges)  # 直接依存
        assert any('style=dashed' in line and 'label="parent"' in line for line in edges)  # 親依存
        assert any('style=dotted' in line and 'label="vpcId"' in line for line in edges)  # プロパティ依存


# =============================================================================
# 2.6 エッジケーステスト（TestEdgeCases）
# =============================================================================

class TestEdgeCases:
    """エッジケースのテスト"""

    def test_循環依存の処理(self):
        """
        Given: resource_0がresource_1に依存し、resource_1がresource_0に依存
        When: add_resource_dependencies()を呼び出す
        Then: 両方のエッジが生成され、無限ループが発生しない
        """
        # Given
        resources = [
            {
                'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a',
                'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b'],
                'parent': None,
                'propertyDependencies': {}
            },
            {
                'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b',
                'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a'],
                'parent': None,
                'propertyDependencies': {}
            }
        ]
        dot_lines = []

        # When
        ResourceDependencyBuilder.add_resource_dependencies(resources, dot_lines)

        # Then
        assert len(dot_lines) == 4  # 空行、コメント、エッジ2本
        edges = [line for line in dot_lines if '->' in line]
        assert len(edges) == 2
        assert any('"resource_0" -> "resource_1"' in line for line in edges)
        assert any('"resource_1" -> "resource_0"' in line for line in edges)

    def test_自己参照依存(self):
        """
        Given: resource_0がresource_0自身に依存
        When: add_resource_dependencies()を呼び出す
        Then: 何も追加されない（リソースが1個のみのため）
        """
        # Given
        resources = [
            {
                'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a',
                'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a'],
                'parent': None,
                'propertyDependencies': {}
            }
        ]
        dot_lines = []

        # When
        ResourceDependencyBuilder.add_resource_dependencies(resources, dot_lines)

        # Then
        assert len(dot_lines) == 0

    def test_極端に長いURN(self):
        """
        Given: 極端に長いURN（300文字以上）を持つリソース
        When: create_urn_to_node_mapping()を呼び出す
        Then: 長いURNが正しく登録され、エラーが発生しない
        """
        # Given
        long_name = 'a' * 300
        resources = [
            {
                'urn': f'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::{long_name}',
                'dependencies': [],
                'parent': None,
                'propertyDependencies': {}
            }
        ]

        # When
        mapping = ResourceDependencyBuilder.create_urn_to_node_mapping(resources)

        # Then
        assert len(mapping) == 1
        long_urn = f'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::{long_name}'
        assert long_urn in mapping
        assert mapping[long_urn] == 'resource_0'

    def test_すべてのフィールドがNoneのリソース(self):
        """
        Given: dependencies, parent, propertyDependenciesがすべてNoneのリソース
        When: add_resource_dependencies()を呼び出す
        Then: コメント行のみ追加され、依存関係エッジは追加されない
        """
        # Given
        resources = [
            {
                'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a',
                'dependencies': None,
                'parent': None,
                'propertyDependencies': None
            },
            {
                'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b',
                'dependencies': None,
                'parent': None,
                'propertyDependencies': None
            }
        ]
        dot_lines = []

        # When
        ResourceDependencyBuilder.add_resource_dependencies(resources, dot_lines)

        # Then
        assert len(dot_lines) == 2  # 空行、コメント
        assert dot_lines[0] == ''
        assert '// リソース間の依存関係' in dot_lines[1]


# =============================================================================
# 2.7 エラーハンドリングテスト（TestErrorHandling）
# =============================================================================

class TestErrorHandling:
    """エラーハンドリングのテスト"""

    def test_不正なリソース辞書_urnキーなし(self):
        """
        Given: 'urn'キーが存在しないリソース辞書
        When: add_resource_dependencies()を呼び出す
        Then: URNマッピングに空文字列がキーとして追加され、エラーが発生しない
        """
        # Given
        resources = [
            {'type': 'aws:s3/bucket:Bucket'},  # urnキーなし
            {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b'}
        ]
        dot_lines = []

        # When
        ResourceDependencyBuilder.add_resource_dependencies(resources, dot_lines)

        # Then
        # エラーが発生しないことを確認
        assert len(dot_lines) >= 2
        assert dot_lines[0] == ''
        assert '// リソース間の依存関係' in dot_lines[1]

    def test_Noneリソース(self):
        """
        Given: Noneを含むリソースリスト
        When: create_urn_to_node_mapping()を呼び出す
        Then: AttributeErrorが発生する（設計上の想定外）
        """
        # Given
        resources = [
            None,
            {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b'}
        ]

        # When & Then
        with pytest.raises(AttributeError):
            ResourceDependencyBuilder.create_urn_to_node_mapping(resources)


# =============================================================================
# 2.8 定数スタイル設定テスト（TestStyleConstants）
# =============================================================================

class TestStyleConstants:
    """スタイル定数のテスト"""

    def test_DIRECT_DEPENDENCY_STYLE定数(self):
        """
        Given: ResourceDependencyBuilderクラスが読み込まれている
        When: DIRECT_DEPENDENCY_STYLE定数を参照する
        Then: 正しいスタイル定義が返される
        """
        # When
        style = ResourceDependencyBuilder.DIRECT_DEPENDENCY_STYLE

        # Then
        assert style == 'style=solid, color="#9C27B0", fontsize="10"'

    def test_PARENT_DEPENDENCY_STYLE定数(self):
        """
        Given: ResourceDependencyBuilderクラスが読み込まれている
        When: PARENT_DEPENDENCY_STYLE定数を参照する
        Then: 正しいスタイル定義が返される
        """
        # When
        style = ResourceDependencyBuilder.PARENT_DEPENDENCY_STYLE

        # Then
        assert style == 'style=dashed, color="#2196F3", label="parent", fontsize="10"'

    def test_PROPERTY_DEPENDENCY_STYLE定数(self):
        """
        Given: ResourceDependencyBuilderクラスが読み込まれている
        When: PROPERTY_DEPENDENCY_STYLE定数を参照する
        Then: 正しいスタイル定義が返される
        """
        # When
        style = ResourceDependencyBuilder.PROPERTY_DEPENDENCY_STYLE

        # Then
        assert style == 'style=dotted, color="#FF5722", fontsize="9"'
