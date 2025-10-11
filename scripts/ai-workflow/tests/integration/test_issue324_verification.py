"""
Issue #324 Verification Test
Tests the implementation of test_implementation phase separation
"""
import json
import tempfile
from pathlib import Path
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "ai-workflow"))

from core.workflow_state import WorkflowState


def test_create_new_includes_test_implementation_phase():
    """Verify that new workflows include test_implementation phase"""
    with tempfile.TemporaryDirectory() as tmpdir:
        metadata_path = Path(tmpdir) / "metadata.json"

        # Create new workflow
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number="324",
            issue_url="https://github.com/tielec/infrastructure-as-code/issues/324",
            issue_title="Test Phase Separation"
        )

        # Verify test_implementation phase exists
        assert "test_implementation" in state.data['phases'], \
            "test_implementation phase not found in phases"

        # Verify phase structure
        test_impl_phase = state.data['phases']['test_implementation']
        assert test_impl_phase['status'] == 'pending'
        assert test_impl_phase['retry_count'] == 0
        assert test_impl_phase['started_at'] is None
        assert test_impl_phase['completed_at'] is None
        assert test_impl_phase['review_result'] is None

        print("✅ test_create_new_includes_test_implementation_phase: PASSED")
        return True


def test_create_new_test_implementation_phase_order():
    """Verify that test_implementation is between implementation and testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        metadata_path = Path(tmpdir) / "metadata.json"

        # Create new workflow
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number="324",
            issue_url="https://github.com/tielec/infrastructure-as-code/issues/324",
            issue_title="Test Phase Order"
        )

        # Get phase order
        phases_list = list(state.data['phases'].keys())

        # Verify order
        impl_index = phases_list.index('implementation')
        test_impl_index = phases_list.index('test_implementation')
        testing_index = phases_list.index('testing')

        assert impl_index < test_impl_index < testing_index, \
            f"Phase order incorrect: implementation={impl_index}, test_implementation={test_impl_index}, testing={testing_index}"

        # Verify expected order
        expected_order = [
            'planning', 'requirements', 'design', 'test_scenario',
            'implementation', 'test_implementation', 'testing',
            'documentation', 'report'
        ]
        assert phases_list == expected_order, \
            f"Phase order mismatch. Expected: {expected_order}, Got: {phases_list}"

        print("✅ test_create_new_test_implementation_phase_order: PASSED")
        return True


def test_update_phase_status_test_implementation():
    """Verify that test_implementation phase status can be updated"""
    with tempfile.TemporaryDirectory() as tmpdir:
        metadata_path = Path(tmpdir) / "metadata.json"

        # Create new workflow
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number="324",
            issue_url="https://github.com/tielec/infrastructure-as-code/issues/324",
            issue_title="Test Status Update"
        )

        # Import PhaseStatus
        from core.workflow_state import PhaseStatus

        # Update to in_progress
        state.update_phase_status('test_implementation', PhaseStatus.IN_PROGRESS)
        state.save()

        # Verify status
        assert state.data['phases']['test_implementation']['status'] == 'in_progress'
        assert state.data['phases']['test_implementation']['started_at'] is not None

        # Update to completed
        state.update_phase_status('test_implementation', PhaseStatus.COMPLETED)
        state.save()

        # Verify status
        assert state.data['phases']['test_implementation']['status'] == 'completed'
        assert state.data['phases']['test_implementation']['completed_at'] is not None

        print("✅ test_update_phase_status_test_implementation: PASSED")
        return True


def test_get_phase_status_test_implementation():
    """Verify that test_implementation phase status can be retrieved"""
    with tempfile.TemporaryDirectory() as tmpdir:
        metadata_path = Path(tmpdir) / "metadata.json"

        # Create new workflow
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number="324",
            issue_url="https://github.com/tielec/infrastructure-as-code/issues/324",
            issue_title="Test Status Get"
        )

        # Get status
        status = state.get_phase_status('test_implementation')

        # Verify status
        assert status == 'pending', f"Expected 'pending', got '{status}'"

        print("✅ test_get_phase_status_test_implementation: PASSED")
        return True


def test_phase_indices_after_test_implementation_addition():
    """Verify phase indices are correct after adding test_implementation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        metadata_path = Path(tmpdir) / "metadata.json"

        # Create new workflow
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number="324",
            issue_url="https://github.com/tielec/infrastructure-as-code/issues/324",
            issue_title="Test Phase Indices"
        )

        # Get phase list
        phases_list = list(state.data['phases'].keys())

        # Verify indices
        assert phases_list[0] == 'planning'
        assert phases_list[1] == 'requirements'
        assert phases_list[2] == 'design'
        assert phases_list[3] == 'test_scenario'
        assert phases_list[4] == 'implementation'
        assert phases_list[5] == 'test_implementation'  # New phase
        assert phases_list[6] == 'testing'  # Shifted from 5
        assert phases_list[7] == 'documentation'  # Shifted from 6
        assert phases_list[8] == 'report'  # Shifted from 7

        print("✅ test_phase_indices_after_test_implementation_addition: PASSED")
        return True


def run_all_tests():
    """Run all verification tests"""
    tests = [
        test_create_new_includes_test_implementation_phase,
        test_create_new_test_implementation_phase_order,
        test_update_phase_status_test_implementation,
        test_get_phase_status_test_implementation,
        test_phase_indices_after_test_implementation_addition
    ]

    passed = 0
    failed = 0

    print("=" * 70)
    print("Issue #324 Verification Tests")
    print("=" * 70)
    print()

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test.__name__}: FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__}: FAILED")
            print(f"   Error: {str(e)}")

    print()
    print("=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
