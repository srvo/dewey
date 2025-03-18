#!/usr/bin/env python3

from dewey.core.base_script import BaseScript
import ibis
from typing import Dict

class ConsolidateSchemas(BaseScript):
    """Script to consolidate schemas in MotherDuck."""

    def __init__(self):
        super().__init__(
            name="consolidate_schemas",
            description="Consolidate and clean up schemas in MotherDuck"
        )
        
    def _are_types_compatible(self, type1: str, type2: str) -> bool:
        """Check if two SQL types are compatible.
        
        Args:
            type1: First SQL type
            type2: Second SQL type
            
        Returns:
            True if types are compatible, False otherwise
        """
        # Normalize types to uppercase
        type1 = type1.upper()
        type2 = type2.upper()
        
        # Define compatible type groups
        numeric_types = {'INTEGER', 'BIGINT', 'SMALLINT', 'TINYINT', 'INT'}
        decimal_types = {'DECIMAL', 'NUMERIC', 'DOUBLE', 'FLOAT', 'REAL'}
        text_types = {'VARCHAR', 'TEXT', 'CHAR', 'STRING'}
        date_types = {'DATE', 'DATETIME', 'TIMESTAMP'}
        
        # Check if types are exactly the same
        if type1 == type2:
            return True
            
        # Check if types are in the same group
        for type_group in [numeric_types, decimal_types, text_types, date_types]:
            if type1 in type_group and type2 in type_group:
                return True
                
        return False
        
    def _are_schemas_compatible(self, schema1: Dict[str, str], schema2: Dict[str, str]) -> bool:
        """Check if two schemas are compatible.
        
        Args:
            schema1: First schema mapping column names to types
            schema2: Second schema mapping column names to types
            
        Returns:
            True if schemas are compatible, False otherwise
        """
        # Convert column names to lowercase for case-insensitive comparison
        schema1_lower = {k.lower(): v for k, v in schema1.items()}
        schema2_lower = {k.lower(): v for k, v in schema2.items()}
        
        # Check if they have the same columns
        if set(schema1_lower.keys()) != set(schema2_lower.keys()):
            return False
            
        # Check if column types are compatible
        for col in schema1_lower:
            if not self._are_types_compatible(schema1_lower[col], schema2_lower[col]):
                return False
                
        return True

    def run(self):
        """Run the schema consolidation process."""
        self.logger.info("Starting schema consolidation")

        # Get list of all tables
        tables = self.db_engine.list_tables()
        self.logger.info(f"Found {len(tables)} tables")

        # Group tables by their schema pattern
        schema_groups = {}
        for table in tables:
            # Extract schema pattern (e.g. 'emails', 'documents', etc.)
            schema_type = table.split('_')[0] if '_' in table else 'misc'
            if schema_type not in schema_groups:
                schema_groups[schema_type] = []
            schema_groups[schema_type].append(table)

        # Track empty tables for deletion
        empty_tables = []

        # Consolidate each group
        for schema_type, group_tables in schema_groups.items():
            self.logger.info(f"Processing schema group: {schema_type}")
            
            if len(group_tables) <= 1:
                continue

            # Get schema of first table as reference
            ref_schema = self.db_engine.get_schema(group_tables[0])
            
            # Create consolidated table name
            consolidated_table = f"{schema_type}_consolidated"
            
            # Create consolidated table with reference schema
            create_stmt = f"CREATE TABLE IF NOT EXISTS {consolidated_table} AS SELECT * FROM {group_tables[0]} WHERE 1=0"
            self.db_engine.execute(create_stmt)
            
            # Insert data from all tables with compatible schema
            for table in group_tables:
                try:
                    # Check if table is empty
                    count_result = self.db_engine.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                    if count_result and count_result[0] == 0:
                        empty_tables.append(table)
                        self.logger.info(f"Found empty table: {table}")
                        continue

                    table_schema = self.db_engine.get_schema(table)
                    if self._are_schemas_compatible(ref_schema, table_schema):
                        # Get column names in the correct order
                        columns = list(ref_schema.keys())
                        columns_str = ', '.join(columns)
                        
                        # Create insert statement with explicit column order
                        insert_stmt = f"INSERT INTO {consolidated_table} ({columns_str}) SELECT {columns_str} FROM {table}"
                        self.db_engine.execute(insert_stmt)
                        self.logger.info(f"Merged data from {table}")
                    else:
                        self.logger.warning(f"Schema mismatch for table {table}, skipping")
                except Exception as e:
                    self.logger.error(f"Error processing table {table}: {str(e)}")

        # Delete empty tables
        self.logger.info(f"Found {len(empty_tables)} empty tables to delete")
        for table in empty_tables:
            try:
                self.db_engine.execute(f"DROP TABLE IF EXISTS {table}")
                self.logger.info(f"Deleted empty table: {table}")
            except Exception as e:
                self.logger.error(f"Error deleting table {table}: {str(e)}")

        self.logger.info("Schema consolidation complete")

if __name__ == "__main__":
    ConsolidateSchemas().main() 