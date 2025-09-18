"""
Condition Service for evaluating tenant eligibility based on various criteria.
Handles conditional logic like payment status, late fees, etc.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.tenant import Tenant
from app.models.message import Message, MessageStatus


logger = logging.getLogger(__name__)


class ConditionService:
    """
    Service for evaluating conditions to determine eligible tenants for messaging.
    Supports complex conditional logic based on tenant attributes and history.
    """
    
    def __init__(self):
        self.condition_operators = {
            "eq": self._equals,
            "neq": self._not_equals,
            "gt": self._greater_than,
            "gte": self._greater_than_equal,
            "lt": self._less_than,
            "lte": self._less_than_equal,
            "in": self._in_list,
            "not_in": self._not_in_list,
            "contains": self._contains,
            "not_contains": self._not_contains,
            "is_null": self._is_null,
            "is_not_null": self._is_not_null,
            "days_ago": self._days_ago,
            "days_ahead": self._days_ahead
        }
    
    async def get_eligible_tenants(
        self,
        conditions: Dict[str, Any],
        db: Session
    ) -> List[Tenant]:
        """
        Get list of tenants that meet the specified conditions.
        
        Args:
            conditions: Dictionary of conditions to evaluate
            db: Database session
            
        Returns:
            List of eligible tenants
        """
        try:
            if not conditions:
                # No conditions means all active tenants
                return db.query(Tenant).filter(Tenant.active == True).all()
            
            # Build query based on conditions
            query = db.query(Tenant).filter(Tenant.active == True)
            
            # Apply conditions
            query = self._apply_conditions(query, conditions, db)
            
            eligible_tenants = query.all()
            
            logger.info(f"Found {len(eligible_tenants)} eligible tenants based on conditions")
            
            return eligible_tenants
            
        except Exception as e:
            logger.error(f"Failed to get eligible tenants: {str(e)}")
            return []
    
    def _apply_conditions(
        self,
        query,
        conditions: Dict[str, Any],
        db: Session
    ):
        """
        Apply conditions to SQLAlchemy query.
        
        Args:
            query: Base SQLAlchemy query
            conditions: Conditions to apply
            db: Database session
            
        Returns:
            Modified query with conditions applied
        """
        logical_operator = conditions.get("operator", "and").lower()
        rules = conditions.get("rules", [])
        
        if not rules:
            return query
        
        condition_filters = []
        
        for rule in rules:
            condition_filter = self._build_condition_filter(rule, db)
            if condition_filter is not None:
                condition_filters.append(condition_filter)
        
        if condition_filters:
            if logical_operator == "and":
                query = query.filter(and_(*condition_filters))
            elif logical_operator == "or":
                query = query.filter(or_(*condition_filters))
        
        return query
    
    def _build_condition_filter(self, rule: Dict[str, Any], db: Session):
        """
        Build individual condition filter.
        
        Args:
            rule: Single condition rule
            db: Database session
            
        Returns:
            SQLAlchemy filter condition or None
        """
        try:
            field = rule.get("field")
            operator = rule.get("operator")
            value = rule.get("value")
            
            if not all([field, operator]):
                return None
            
            # Handle nested conditions
            if field == "group":
                nested_conditions = rule.get("conditions", {})
                if nested_conditions:
                    # Create subquery for nested conditions
                    subquery = db.query(Tenant).filter(Tenant.active == True)
                    subquery = self._apply_conditions(subquery, nested_conditions, db)
                    return Tenant.id.in_(subquery.with_entities(Tenant.id))
                return None
            
            # Get field attribute
            field_attr = self._get_field_attribute(field)
            if field_attr is None:
                logger.warning(f"Unknown field: {field}")
                return None
            
            # Apply operator
            condition_func = self.condition_operators.get(operator)
            if condition_func:
                return condition_func(field_attr, value, db)
            else:
                logger.warning(f"Unknown operator: {operator}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to build condition filter: {str(e)}")
            return None
    
    def _get_field_attribute(self, field: str):
        """
        Get SQLAlchemy field attribute from field name.
        
        Args:
            field: Field name
            
        Returns:
            SQLAlchemy field attribute or None
        """
        field_mapping = {
            "name": Tenant.name,
            "email": Tenant.email,
            "phone": Tenant.phone,
            "unit_number": Tenant.unit_number,
            "rent_amount": Tenant.rent_amount,
            "is_current_month_rent_paid": Tenant.is_current_month_rent_paid,
            "last_payment_date": Tenant.last_payment_date,
            "late_fee_applicable": Tenant.late_fee_applicable,
            "emergency_contact": Tenant.emergency_contact,
            "lease_start_date": Tenant.lease_start_date,
            "lease_end_date": Tenant.lease_end_date,
            "notes": Tenant.notes,
            "active": Tenant.active,
            "created_at": Tenant.created_at,
            "updated_at": Tenant.updated_at
        }
        
        return field_mapping.get(field)
    
    # Condition operators
    def _equals(self, field_attr, value, db):
        return field_attr == value
    
    def _not_equals(self, field_attr, value, db):
        return field_attr != value
    
    def _greater_than(self, field_attr, value, db):
        return field_attr > value
    
    def _greater_than_equal(self, field_attr, value, db):
        return field_attr >= value
    
    def _less_than(self, field_attr, value, db):
        return field_attr < value
    
    def _less_than_equal(self, field_attr, value, db):
        return field_attr <= value
    
    def _in_list(self, field_attr, value, db):
        if isinstance(value, list):
            return field_attr.in_(value)
        return field_attr == value
    
    def _not_in_list(self, field_attr, value, db):
        if isinstance(value, list):
            return ~field_attr.in_(value)
        return field_attr != value
    
    def _contains(self, field_attr, value, db):
        return field_attr.contains(str(value))
    
    def _not_contains(self, field_attr, value, db):
        return ~field_attr.contains(str(value))
    
    def _is_null(self, field_attr, value, db):
        return field_attr.is_(None)
    
    def _is_not_null(self, field_attr, value, db):
        return field_attr.isnot(None)
    
    def _days_ago(self, field_attr, value, db):
        """Check if field date is X days ago."""
        try:
            days = int(value)
            target_date = datetime.utcnow() - timedelta(days=days)
            return func.date(field_attr) == target_date.date()
        except (ValueError, TypeError):
            return None
    
    def _days_ahead(self, field_attr, value, db):
        """Check if field date is X days ahead."""
        try:
            days = int(value)
            target_date = datetime.utcnow() + timedelta(days=days)
            return func.date(field_attr) == target_date.date()
        except (ValueError, TypeError):
            return None
    
    def evaluate_tenant_conditions(
        self,
        tenant: Tenant,
        conditions: Dict[str, Any],
        db: Session
    ) -> bool:
        """
        Evaluate if a single tenant meets the conditions.
        
        Args:
            tenant: Tenant to evaluate
            conditions: Conditions to check
            db: Database session
            
        Returns:
            True if tenant meets conditions
        """
        try:
            if not conditions:
                return True
            
            # For single tenant evaluation, we use a different approach
            return self._evaluate_tenant_rules(tenant, conditions, db)
            
        except Exception as e:
            logger.error(f"Failed to evaluate tenant conditions: {str(e)}")
            return False
    
    def _evaluate_tenant_rules(
        self,
        tenant: Tenant,
        conditions: Dict[str, Any],
        db: Session
    ) -> bool:
        """
        Evaluate conditions for a single tenant.
        
        Args:
            tenant: Tenant to evaluate
            conditions: Conditions to check
            db: Database session
            
        Returns:
            True if conditions are met
        """
        logical_operator = conditions.get("operator", "and").lower()
        rules = conditions.get("rules", [])
        
        if not rules:
            return True
        
        results = []
        
        for rule in rules:
            result = self._evaluate_single_rule(tenant, rule, db)
            results.append(result)
        
        if logical_operator == "and":
            return all(results)
        elif logical_operator == "or":
            return any(results)
        else:
            return True
    
    def _evaluate_single_rule(
        self,
        tenant: Tenant,
        rule: Dict[str, Any],
        db: Session
    ) -> bool:
        """
        Evaluate single condition rule for a tenant.
        
        Args:
            tenant: Tenant to evaluate
            rule: Single rule to evaluate
            db: Database session
            
        Returns:
            True if rule is satisfied
        """
        try:
            field = rule.get("field")
            operator = rule.get("operator")
            value = rule.get("value")
            
            if not all([field, operator]):
                return True
            
            # Handle nested conditions
            if field == "group":
                nested_conditions = rule.get("conditions", {})
                return self._evaluate_tenant_rules(tenant, nested_conditions, db)
            
            # Get tenant field value
            tenant_value = getattr(tenant, field, None)
            
            # Apply operator
            return self._apply_operator(tenant_value, operator, value)
            
        except Exception as e:
            logger.error(f"Failed to evaluate single rule: {str(e)}")
            return True  # Default to true to avoid blocking
    
    def _apply_operator(self, tenant_value: Any, operator: str, expected_value: Any) -> bool:
        """
        Apply operator to compare tenant value with expected value.
        
        Args:
            tenant_value: Value from tenant object
            operator: Comparison operator
            expected_value: Expected value to compare against
            
        Returns:
            True if condition is met
        """
        try:
            if operator == "eq":
                return tenant_value == expected_value
            elif operator == "neq":
                return tenant_value != expected_value
            elif operator == "gt":
                return tenant_value > expected_value
            elif operator == "gte":
                return tenant_value >= expected_value
            elif operator == "lt":
                return tenant_value < expected_value
            elif operator == "lte":
                return tenant_value <= expected_value
            elif operator == "in":
                return tenant_value in expected_value if isinstance(expected_value, list) else tenant_value == expected_value
            elif operator == "not_in":
                return tenant_value not in expected_value if isinstance(expected_value, list) else tenant_value != expected_value
            elif operator == "contains":
                return str(expected_value) in str(tenant_value or "")
            elif operator == "not_contains":
                return str(expected_value) not in str(tenant_value or "")
            elif operator == "is_null":
                return tenant_value is None
            elif operator == "is_not_null":
                return tenant_value is not None
            elif operator == "days_ago":
                if isinstance(tenant_value, datetime) and isinstance(expected_value, int):
                    target_date = datetime.utcnow() - timedelta(days=expected_value)
                    return tenant_value.date() == target_date.date()
                return False
            elif operator == "days_ahead":
                if isinstance(tenant_value, datetime) and isinstance(expected_value, int):
                    target_date = datetime.utcnow() + timedelta(days=expected_value)
                    return tenant_value.date() == target_date.date()
                return False
            else:
                logger.warning(f"Unknown operator: {operator}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to apply operator {operator}: {str(e)}")
            return True
    
    def get_predefined_conditions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get common predefined condition sets.
        
        Returns:
            Dictionary of predefined conditions
        """
        return {
            "unpaid_rent": {
                "operator": "and",
                "rules": [
                    {
                        "field": "is_current_month_rent_paid",
                        "operator": "eq",
                        "value": False
                    }
                ]
            },
            "paid_rent": {
                "operator": "and",
                "rules": [
                    {
                        "field": "is_current_month_rent_paid",
                        "operator": "eq",
                        "value": True
                    }
                ]
            },
            "late_fees": {
                "operator": "and",
                "rules": [
                    {
                        "field": "late_fee_applicable",
                        "operator": "eq",
                        "value": True
                    }
                ]
            },
            "overdue_rent": {
                "operator": "and",
                "rules": [
                    {
                        "field": "is_current_month_rent_paid",
                        "operator": "eq",
                        "value": False
                    },
                    {
                        "field": "late_fee_applicable",
                        "operator": "eq",
                        "value": True
                    }
                ]
            },
            "no_recent_payment": {
                "operator": "and",
                "rules": [
                    {
                        "field": "last_payment_date",
                        "operator": "lt",
                        "value": (datetime.utcnow() - timedelta(days=30)).isoformat()
                    }
                ]
            },
            "all_tenants": {
                "operator": "and",
                "rules": []
            }
        }
    
    async def test_conditions(
        self,
        conditions: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """
        Test conditions and return statistics about matching tenants.
        
        Args:
            conditions: Conditions to test
            db: Database session
            
        Returns:
            Statistics about matching tenants
        """
        try:
            eligible_tenants = await self.get_eligible_tenants(conditions, db)
            total_tenants = db.query(Tenant).filter(Tenant.active == True).count()
            
            return {
                "total_tenants": total_tenants,
                "eligible_tenants": len(eligible_tenants),
                "match_percentage": (len(eligible_tenants) / total_tenants * 100) if total_tenants > 0 else 0,
                "tenant_names": [t.name for t in eligible_tenants[:10]],  # First 10 names
                "conditions_summary": self._summarize_conditions(conditions)
            }
            
        except Exception as e:
            logger.error(f"Failed to test conditions: {str(e)}")
            return {
                "error": str(e)
            }
    
    def _summarize_conditions(self, conditions: Dict[str, Any]) -> str:
        """
        Create human-readable summary of conditions.
        
        Args:
            conditions: Conditions to summarize
            
        Returns:
            Human-readable condition summary
        """
        if not conditions or not conditions.get("rules"):
            return "All active tenants"
        
        operator = conditions.get("operator", "and").upper()
        rules = conditions.get("rules", [])
        
        rule_summaries = []
        for rule in rules:
            field = rule.get("field", "")
            op = rule.get("operator", "")
            value = rule.get("value", "")
            
            # Convert to human readable
            field_name = field.replace("_", " ").title()
            
            if op == "eq":
                rule_summaries.append(f"{field_name} equals {value}")
            elif op == "neq":
                rule_summaries.append(f"{field_name} not equals {value}")
            elif op == "is_null":
                rule_summaries.append(f"{field_name} is empty")
            elif op == "is_not_null":
                rule_summaries.append(f"{field_name} is not empty")
            else:
                rule_summaries.append(f"{field_name} {op} {value}")
        
        return f" {operator} ".join(rule_summaries)


# Global condition service instance
condition_service = ConditionService()