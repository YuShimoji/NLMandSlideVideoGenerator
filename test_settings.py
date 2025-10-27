try:
    from config.settings import settings
    print("Settings import: OK")
except Exception as e:
    import traceback
    print(f"Settings import error: {e}")
    traceback.print_exc()
