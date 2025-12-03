"""
Configuration package.

ARCHITECTURAL NOTE: Why config/ is NOT inside shared/
======================================================

This package sits at the TOP LEVEL of src/ (alongside shared/, api/, worker/)
rather than inside shared/ for important architectural reasons:

1. DEPENDENCY DIRECTION
   ----------------------
   config/
     ↓ (provides settings to)
   shared/ (uses config)
     ↓ (used by)
   api/ & worker/

   The shared layer DEPENDS ON config, not the other way around.
   If config were inside shared/, we'd have awkward circular dependencies.

2. DIFFERENT SCOPE
   ---------------
   - shared/  = Domain logic (models, services, repositories, business rules)
   - config/  = Infrastructure (environment variables, app settings, deployment config)

   Configuration is INFRASTRUCTURE-LEVEL, not domain-level code.

3. APPLICATION-WIDE SCOPE
   -----------------------
   Config affects the ENTIRE application (shared + api + worker), not just
   "things shared between api and worker". It's at a higher abstraction level.

4. CLEAN IMPORTS
   -------------
   # ✅ Clean - config at same level as shared
   from ...config.settings import settings

   # ❌ Awkward - if config were in shared
   from ..shared.config.settings import settings

5. STANDARD PATTERN
   ----------------
   Follows Python conventions (Django's settings.py, Flask's config.py)
   where configuration is separate from application modules.

USAGE
=====
Import settings anywhere in the application:

    from src.config.settings import settings

    # Access configuration
    db_url = settings.DATABASE_URL
    secret = settings.SECRET_KEY
"""
