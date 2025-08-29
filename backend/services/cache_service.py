from cache import load_cache, save_cache

def get_cache_value(key):
    cache = load_cache()
    return cache.get(key)

def set_cache_value(key, value):
    cache = load_cache()
    cache[key] = value
    save_cache(cache)
    return True
