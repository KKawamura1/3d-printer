"""Cache expensive CAD model construction only during test execution.

Production build_part() functions remain uncached. Each test receives an
independent copy of the cached BRep so test-local transformations cannot
modify the shared geometry.
"""
from functools import lru_cache


@lru_cache(maxsize=32)
def _build_once(factory, args, keyword_args):
    return factory(*args, **dict(keyword_args))


def cached_build_part(factory, /, *args, **kwargs):
    """Build each (factory, arguments) combination once per Python process.

    Intended only for tests that treat the returned parameter object as
    read-only. The cached solid itself is never returned directly.
    """
    solid, parameters = _build_once(factory, args, tuple(sorted(kwargs.items())))
    return solid.copy(mesh=False), parameters
