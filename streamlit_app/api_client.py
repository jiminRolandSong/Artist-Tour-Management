import requests


def _url(api_base_url, path):
    return f"{api_base_url.rstrip('/')}{path}"


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _handle_response(response):
    try:
        data = response.json()
    except ValueError:
        data = {"detail": response.text}

    if not response.ok:
        message = data.get("detail") if isinstance(data, dict) else None
        raise requests.HTTPError(message or f"Request failed with status {response.status_code}", response=response)

    return data


def login(api_base_url, username, password):
    response = requests.post(
        _url(api_base_url, "/api/token/"),
        json={"username": username, "password": password},
        timeout=15,
    )
    return _handle_response(response)


def register(api_base_url, username, email, password):
    response = requests.post(
        _url(api_base_url, "/api/register/"),
        json={"username": username, "email": email, "password": password},
        timeout=15,
    )
    return _handle_response(response)


def get_artists(api_base_url, token):
    response = requests.get(
        _url(api_base_url, "/api/artists/"),
        headers=_auth_headers(token),
        timeout=15,
    )
    return _handle_response(response)


def create_artist(api_base_url, token, name, genre):
    response = requests.post(
        _url(api_base_url, "/api/artists/"),
        json={"name": name, "genre": genre},
        headers=_auth_headers(token),
        timeout=15,
    )
    return _handle_response(response)


def get_venues(api_base_url, token):
    response = requests.get(
        _url(api_base_url, "/api/venues/"),
        headers=_auth_headers(token),
        timeout=15,
    )
    return _handle_response(response)


def get_tour_groups(api_base_url, token):
    response = requests.get(
        _url(api_base_url, "/api/tour-groups/"),
        headers=_auth_headers(token),
        timeout=15,
    )
    return _handle_response(response)


def create_tour_group(api_base_url, token, payload):
    response = requests.post(
        _url(api_base_url, "/api/tour-groups/"),
        json=payload,
        headers=_auth_headers(token),
        timeout=15,
    )
    return _handle_response(response)


def get_tour_dates(api_base_url, token):
    response = requests.get(
        _url(api_base_url, "/api/tours/"),
        headers=_auth_headers(token),
        timeout=15,
    )
    return _handle_response(response)


def run_optimization(api_base_url, token, payload):
    response = requests.post(
        _url(api_base_url, "/api/optimize/"),
        json=payload,
        headers=_auth_headers(token),
        timeout=60,
    )
    return _handle_response(response)


def confirm_optimization(api_base_url, token, payload):
    response = requests.post(
        _url(api_base_url, "/api/optimize/confirm/"),
        json=payload,
        headers=_auth_headers(token),
        timeout=30,
    )
    return _handle_response(response)
