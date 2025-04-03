"""
CRM Workflow Runner Script

This script provides a unified entry point for running CRM workflows:
- Email collection and enrichment
- Contact consolidation

It can run workflows individually or as a complete pipeline.
"""

import argparse
import logging
import sys
from typing import List

from dewey.core.base_script import BaseScript
from dewey.core.crm.contacts.contact_consolidation import ContactConsolidation
from dewey.core.crm.enrichment.email_enrichment import EmailEnrichment


class CRMWorkflowRunner(BaseScript):
    """
    Runner for CRM workflows.
    
    This script provides a unified entry point for executing CRM workflows.
    It can run individual workflows or a complete pipeline based on command-line arguments.
    """
    
    def __init__(self):
        """Initialize the CRM workflow runner."""
        super().__init__(
            name="CRMWorkflowRunner",
            description="Runner for CRM workflows",
            config_section="crm_workflow_runner",
            requires_db=True
        )
        self.logger.info("Initialized CRM Workflow Runner")
    
    def setup_argparse(self) -> argparse.ArgumentParser:
        """
        Set up command line arguments for the workflow runner.
        
        Returns:
            Configured argument parser
        """
        parser = super().setup_argparse()
        
        # Add workflow selection arguments
        workflow_group = parser.add_argument_group("Workflow Selection")
        workflow_group.add_argument(
            "--email-enrichment",
            action="store_true",
            help="Run email enrichment workflow"
        )
        workflow_group.add_argument(
            "--contact-consolidation",
            action="store_true",
            help="Run contact consolidation workflow"
        )
        workflow_group.add_argument(
            "--all",
            action="store_true",
            help="Run all workflows"
        )
        
        # Add Gmail API options
        gmail_group = parser.add_argument_group("Gmail API Options")
        gmail_group.add_argument(
            "--no-gmail-api",
            action="store_true",
            help="Disable Gmail API for email enrichment (use snippets only)"
        )
        
        return parser
    
    def execute(self) -> None:
        """
        Execute the selected CRM workflows based on command-line arguments.
        """
        try:
            # Parse arguments
            args = self.parse_args()
            
            # Determine which workflows to run
            run_email_enrichment = args.email_enrichment or args.all
            run_contact_consolidation = args.contact_consolidation or args.all
            
            # If no workflows specified, run all
            if not (run_email_enrichment or run_contact_consolidation):
                run_email_enrichment = True
                run_contact_consolidation = True
            
            # Log what we're going to do
            workflows = []
            if run_email_enrichment:
                workflows.append("Email Enrichment")
            if run_contact_consolidation:
                workflows.append("Contact Consolidation")
                
            workflow_str = ", ".join(workflows)
            self.logger.info(f"Running workflows: {workflow_str}")
            
            # Execute workflows in sequence
            if run_email_enrichment:
                self._run_email_enrichment()
                
            if run_contact_consolidation:
                self._run_contact_consolidation()
                
            self.logger.info("All workflows completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error executing CRM workflows: {e}", exc_info=True)
            raise
    
    def _run_email_enrichment(self) -> None:
        """
        Run the email enrichment workflow.
        """
        try:
            args = self.parse_args()
            
            self.logger.info("Starting Email Enrichment workflow")
            enrichment = EmailEnrichment()
            
            # Set Gmail API usage based on command line args
            if args.no_gmail_api:
                self.logger.info("Gmail API disabled by command line option")
                enrichment.use_gmail_api = False
                
            enrichment.execute()
            self.logger.info("Email Enrichment workflow completed")
        except Exception as e:
            self.logger.error(f"Error in Email Enrichment workflow: {e}")
            raise
    
    def _run_contact_consolidation(self) -> None:
        """
        Run the contact consolidation workflow.
        """
        try:
            self.logger.info("Starting Contact Consolidation workflow")
            consolidation = ContactConsolidation()
            consolidation.execute()
            self.logger.info("Contact Consolidation workflow completed")
        except Exception as e:
            self.logger.error(f"Error in Contact Consolidation workflow: {e}")
            raise


if __name__ == "__main__":
    runner = CRMWorkflowRunner()
    runner.execute() 