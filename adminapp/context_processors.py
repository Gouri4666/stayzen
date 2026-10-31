from .models import SiteSettings

def site_settings_processor(request):
    # This automatically makes {{ settings }} available in base.html on EVERY page!
    return {
        'settings': SiteSettings.load()
    }