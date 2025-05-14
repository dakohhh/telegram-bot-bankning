"""
Database initialization module
This file ensures proper ordering of model imports to avoid circular imports
"""
from .models import BaseModel, UUIDModel, TimestampModel
# Import all models here in the correct order
# This ensures proper initialization and prevents circular import issues

# After importing the base models, it's safe to import other models
# that depend on them

# First, import models with no foreign key dependencies on other models
# Then import models with dependencies in order of their dependency chain 