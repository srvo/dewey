"""Tests for financial pipeline."""

import pytest
from unittest.mock import patch, MagicMock
import subprocess
from dewey.core.research.analysis.financial_pipeline import (
    check_account_declarations,
    system_checks,
    check_python_dependencies,
    process_transactions,
    run_repository_maintenance,
    run_classification,
    validate_ledger,
    generate_reports,
    classification_verification,
    main,
)


class TestFinancialPipeline:
    """Test suite for financial pipeline."""

    @pytest.fixture
    def mock_subprocess_run(self):
        """Mock subprocess.run."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="Test output", stderr=""
            )
            yield mock_run

    @pytest.fixture
    def mock_paths(self, tmp_path):
        """Create mock file paths."""
        paths = {
            "main_ledger": tmp_path / "complete_ledger.journal",
            "mercury_input": tmp_path / "import/mercury/in",
            "reports_dir": tmp_path / "reports",
            "rules_file": tmp_path / "import/mercury/classification_rules.json",
        }

        # Create directories
        for path in paths.values():
            path.parent.mkdir(parents=True, exist_ok=True)

        # Create sample files
        paths["main_ledger"].write_text("account Assets:Checking\n")
        paths["rules_file"].write_text('{"rules": []}')

        return paths

    def test_check_account_declarations_valid(self, mock_paths, mock_subprocess_run):
        """Test account declarations check with valid ledger."""
        mock_subprocess_run.return_value.stdout = (
            "Expenses:Insurance\nExpenses:Payroll:Salaries"
        )
        check_account_declarations(mock_paths["main_ledger"])
        mock_subprocess_run.assert_called()

    def test_check_account_declarations_missing(self, mock_paths, mock_subprocess_run):
        """Test account declarations check with missing accounts."""
        mock_subprocess_run.return_value.stdout = "Assets:Checking"
        with pytest.raises(SystemExit):
            check_account_declarations(mock_paths["main_ledger"])

    def test_system_checks_all_present(self):
        """Test system checks with all dependencies present."""
        with patch("shutil.which", return_value="/usr/bin/test"):
            system_checks()

    def test_system_checks_missing(self):
        """Test system checks with missing dependencies."""
        with patch("shutil.which", return_value=None):
            with pytest.raises(SystemExit):
                system_checks()

    def test_check_python_dependencies_all_present(self):
        """Test Python dependency check with all packages present."""
        with patch.dict(
            "sys.modules",
            {"requests": MagicMock(), "colorlog": MagicMock(), "dotenv": MagicMock()},
        ):
            check_python_dependencies()

    def test_check_python_dependencies_missing(self):
        """Test Python dependency check with missing packages."""
        with patch.dict("sys.modules", {}):
            with pytest.raises(SystemExit):
                check_python_dependencies()

    def test_process_transactions_success(self, mock_paths, mock_subprocess_run):
        """Test successful transaction processing."""
        csv_file = mock_paths["mercury_input"] / "mercury_test.csv"
        csv_file.write_text("test,data\n1,2")

        process_transactions(mock_paths["mercury_input"])
        mock_subprocess_run.assert_called_once()

    def test_process_transactions_no_files(self, mock_paths, mock_subprocess_run):
        """Test transaction processing with no files."""
        with pytest.raises(SystemExit):
            process_transactions(mock_paths["mercury_input"])

    def test_run_repository_maintenance(self, mock_subprocess_run):
        """Test repository maintenance checks."""
        run_repository_maintenance()
        assert mock_subprocess_run.call_count == 2

    def test_run_classification(self, mock_paths, mock_subprocess_run):
        """Test classification workflow."""
        run_classification(mock_paths["main_ledger"])
        assert mock_subprocess_run.call_count == 2

    def test_validate_ledger(self, mock_paths, mock_subprocess_run):
        """Test ledger validation."""
        validate_ledger(mock_paths["main_ledger"])
        mock_subprocess_run.assert_called_once()

    def test_generate_reports(self, mock_paths, mock_subprocess_run):
        """Test report generation."""
        generate_reports(mock_paths["main_ledger"], mock_paths["reports_dir"])
        assert mock_subprocess_run.call_count == 4  # One call per report type

    def test_classification_verification(self, mock_paths):
        """Test classification verification."""
        with patch(
            "dewey.core.research.analysis.financial_pipeline.ClassificationVerifier"
        ) as mock_verifier:
            classification_verification(mock_paths["main_ledger"])
            mock_verifier.assert_called_once()

    @pytest.mark.integration
    def test_full_pipeline_integration(self, mock_paths, mock_subprocess_run):
        """Integration test for full pipeline."""
        # Create necessary files
        (mock_paths["mercury_input"] / "mercury_test.csv").write_text("test,data\n1,2")

        # Run main function
        with patch("pathlib.Path.cwd", return_value=mock_paths["main_ledger"].parent):
            main()

            # Verify all steps were executed
            assert (
                mock_subprocess_run.call_count >= 7
            )  # At least 7 subprocess calls expected

            # Check if reports directory was created
            assert mock_paths["reports_dir"].exists()

    def test_pipeline_error_handling(self, mock_paths, mock_subprocess_run):
        """Test error handling in pipeline."""
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            1, "test", "error"
        )

        with patch("pathlib.Path.cwd", return_value=mock_paths["main_ledger"].parent):
            with pytest.raises(SystemExit):
                main()

    def test_pipeline_missing_files(self, mock_paths, mock_subprocess_run):
        """Test pipeline behavior with missing files."""
        # Remove required files
        for path in mock_paths.values():
            if path.exists():
                path.unlink()

        with patch("pathlib.Path.cwd", return_value=mock_paths["main_ledger"].parent):
            with pytest.raises(SystemExit):
                main()
