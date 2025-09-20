import requests
from django.conf import settings

def get_posthog_events(limit=50):
    url = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/events/"
    headers = {
        "Authorization": f"Bearer {settings.POSTHOG_API_KEY}"
    }
    params = {"limit": limit}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get("results", [])
    return []

def get_insight_data(insight_id):
    url = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/insights/{insight_id}/"
    headers = {
        "Authorization": f"Bearer {settings.POSTHOG_API_KEY}"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

